import re
import subprocess
from datetime import datetime, timedelta
from http.cookies import SimpleCookie
from typing import Tuple, List, Dict, Any, Optional
from _config import Config
from log import Log


class Files:
    MAX_RANGE = 2000
    DT_FORMAT = '%Y%m%d/%H/%M'
    DT_FULL_FORMAT = '%Y%m%d%H%M%S'
    DEPTH = 3
    MIN_FILE_SIZE = 1000

    def __init__(self, cam_hash: str, cookie: SimpleCookie):
        self._hash = cam_hash
        self._cam_path = f'{Config.storage_path}/{Config.cameras[cam_hash]["path"]}'
        self._cookie = cookie

    def get_days(self):
        return round((datetime.now() - self.get_start_date_time()).total_seconds() / 86400)

    def get_live(self) -> Tuple[str, int]:
        current_folder = datetime.now().strftime(self.DT_FORMAT)  # Regular case
        file, size = self._get_file(current_folder, -2, -1)
        if size > self.MIN_FILE_SIZE:
            self._cookie['rng'] = ''
            return file, int(size)

        fallback = (datetime.now() - timedelta(minutes=1)).strftime(self.DT_FORMAT).split('/')
        path, size = self._find_nearest_file('/'.join(fallback[0:-1]), fallback[-1], -2)
        self._cookie['rng'] = ''
        return path, size

    def _find_nearest_file(self, parent: str, folder: str, step: int) -> Tuple[str, int]:
        """ If folder is set, shift left (to parent folder); else shift right (to child folder) """
        parts = parent.split('/') if parent else []

        if (folder and len(parts) == self.DEPTH - 1) or (not folder and len(parts) == self.DEPTH):
            path = f'{parent}/{folder}' if folder else parent
            sign = -1
            if step == -2:
                start, stop = -2, -1  # live, skip last file
            elif step < 0:
                start, stop = -1, None  # last
            else:
                start, stop = 0, 1  # first
                sign = 1
            file, size = self._get_file(path, start, stop)
            if size > self.MIN_FILE_SIZE:
                return file, int(size)

            fallback = (datetime.strptime(path, self.DT_FORMAT) + timedelta(minutes=1) * sign).strftime(self.DT_FORMAT)
            file, size = self._get_file(fallback, start, stop)

            if size > self.MIN_FILE_SIZE:
                return file, int(size)

        folders = self._get_folders(parent)
        if not folders and len(parts) > 0:
            return self._find_nearest_file('/'.join(parts[0:-1]), parts[-1], step)  # shift left

        if folder:
            if step < 0:  # find the largest element of folders less than folder
                rest = [i for i in folders if i < folder]
            else:  # find the smallest element of folders greater than folder
                rest = [i for i in folders if i > folder]
            if rest:
                parts.append(max(rest) if step < 0 else min(rest))
                return self._find_nearest_file('/'.join(parts), '', step)  # shift right

            if len(parts) > 0:
                return self._find_nearest_file('/'.join(parts[0:-1]), parts[-1], step)  # shift left
            elif step < 0:
                return self._find_nearest_file('', '', 1)  # move to the beginning
            else:
                return self.get_live()  # move to the end

        if not folder and folders and len(parts) < self.DEPTH:
            parts.append(folders[-1]) if step < 0 else parts.append(folders[0])
            return self._find_nearest_file('/'.join(parts), '', step)  # shift right

        Log.print(f'find_nearest_file: folder not found: {parent}/{folder}, step={step}')

        return '', 0

    def get_by_range(self, query: Dict[str, List[str]]) -> Tuple[str, int]:
        rng = int(query['range'][0])
        rng = min(max(rng, 0), self.MAX_RANGE)

        start_date = self.get_start_date_time()
        time_range = datetime.now() - start_date
        delta_minutes = int(time_range.total_seconds() * rng / self.MAX_RANGE / 60)
        wd = (start_date + timedelta(minutes=delta_minutes)).strftime(self.DT_FORMAT)

        self._cookie['rng'] = str(rng)  # todo: calc rng ?

        parts = wd.split('/')
        return self._find_nearest_file('/'.join(parts[0:-1]), parts[-1], -1)

    def get_next_by_date_time(self, date_time: str, query: Dict[str, List[str]]) -> Tuple[str, int]:
        raw_step = int(query['next'][0])

        steps = [1, 60, 600, 3600]
        step = steps[abs(raw_step) - 1] if 1 <= abs(raw_step) <= len(steps) else 1
        step = step * -1 if raw_step < 0 else step

        if 'md' in query:
            return self._get_next_motion_by_date_time(date_time, int(query['md'][0]), step)

        file_path = self._get_path_by_datetime(date_time)
        # if not file_path:
        #    return '', 0
        parts = file_path.split('/')
        wd = '/'.join(parts[0:-1])

        files = self._get_files(wd)

        if files and abs(step) == 1:
            arr = files if step > 0 else reversed(files)
            for file in arr:
                file_name = file.split()[1]
                if (step > 0 and file_name <= parts[-1]) or (step < 0 and file_name >= parts[-1]):
                    continue

                f = file.split()
                path = f'{self._cam_path}/{wd}/{f[1]}'
                if int(f[0]) > self.MIN_FILE_SIZE:
                    self._cookie['rng'] = str(self._get_range_by_path(path))
                    return path, int(f[0])

        sign = 1 if step > 0 else -1
        step = max(60, abs(step)) * sign
        folder = (
            datetime.strptime(wd, self.DT_FORMAT) + timedelta(seconds=abs(step)) * sign
        ).strftime(self.DT_FORMAT)

        if step > 0 and folder >= datetime.now().strftime(self.DT_FORMAT):
            return self.get_live()

        parts = folder.split('/')
        return self._find_nearest_file('/'.join(parts[0:-1]), parts[-1], sign)

    def get_datetime_by_path(self, path: str) -> str:
        parts = path[len(self._cam_path) + 1:].split('/')
        return ''.join(parts[0:-1]) + parts[-1].replace('.mp4', '')

    def get_start_date_time(self) -> datetime:
        return datetime.strptime(self._get_folders()[0], '%Y%m%d')

    def _get_next_motion_by_date_time(self, date_time: str, sensitivity: int, step: int) -> Tuple[str, int]:
        if step >= 60 or step <= -60:
            sign = 1 if step > 0 else -1
            folder = (
                datetime.strptime(date_time, self.DT_FULL_FORMAT) + timedelta(seconds=abs(step)) * sign
            ).strftime(self.DT_FORMAT)
            file_name = '00.mp4'
        else:
            path = self._get_path_by_datetime(date_time)
            file_name = path.split('/')[-1]
            folder = '/'.join(path.split('/')[0:-1])

        return self._motion_detector(folder, file_name, 0, sensitivity)

    def _motion_detector(self, folder: str, file_name: str, current_size: int, sensitivity: int) -> Tuple[str, int]:
        files = self._get_files(folder)
        if not files:
            file = self._find_nearest_file(folder, '', 1)
            if file:
                path = '/'.join(file[0][len(self._cam_path) + 1:].split('/')[0:-1])
                if path > folder:
                    return self._motion_detector(path, '', current_size, sensitivity)

                return self.get_live()

        sens = 1 + sensitivity / 100
        for file in files:
            f = file.split(' ')
            if not current_size and file_name and file_name <= f[1]:
                current_size = int(f[0])
            elif current_size and float(f[0]) > current_size * sens and int(f[0]) > self.MIN_FILE_SIZE:
                path = f'{self._cam_path}/{folder}/{f[1]}'
                self._cookie['rng'] = str(self._get_range_by_path(path))
                return path, int(f[0])
            elif current_size:
                current_size = int(f[0])

        if folder >= datetime.now().strftime(self.DT_FORMAT):
            return self.get_live()

        folder = (datetime.strptime(folder, self.DT_FORMAT) + timedelta(minutes=1)).strftime(self.DT_FORMAT)

        return self._motion_detector(folder, '', current_size, sensitivity)

    def _get_folders(self, folder: str = '') -> List[str]:
        cmd = f'ls {self._cam_path}/{folder}'
        return self._exec(cmd).splitlines()  # todo: cache root folder

    def _get_files(self, folder: str = '', start: int = 0, stop: Optional[int] = None) -> List[str]:
        wd = f"{self._cam_path}/{folder}"
        cmd = f'ls -l {wd} | awk ' + "'{print $5,$9}'"
        res = self._exec(cmd)
        if not res and folder < datetime.now().strftime(self.DT_FORMAT):
            self._exec(f'rmdir {self._cam_path}/{folder}')  # delete empty folder
        return res.splitlines()[start:stop]

    def _get_file(self, folder: str, start: int = 0, stop: Optional[int] = None) -> Tuple[str, int]:
        files = self._get_files(folder, start, stop)
        if not files:
            return '', 0
        file = files[0].split()  # [size, file]
        path = f'{self._cam_path}/{folder}/{file[1]}'
        self._cookie['rng'] = str(self._get_range_by_path(path))
        return path, int(file[0])

    def _get_range_by_path(self, path: str) -> int:
        start_date_time = self.get_start_date_time()
        delta_seconds = (
            datetime.strptime(self.get_datetime_by_path(path), self.DT_FULL_FORMAT) - start_date_time
        ).total_seconds()
        total_seconds = (datetime.now() - start_date_time).total_seconds()
        return round(self.MAX_RANGE * delta_seconds / total_seconds)

    @staticmethod
    def _get_path_by_datetime(dt: str) -> str:
        if not re.match('^\d{14}$', dt):
            return ''
        return f'{dt[0:8]}/{dt[8:10]}/{dt[10:12]}/{dt[12:14]}.mp4'

    @staticmethod
    def _exec(cmd: str, default: Any = '') -> Any:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True, shell=True)
        stdout, _stderr = p.communicate()
        return stdout.strip() or default
