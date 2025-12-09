import asyncio
import re
from datetime import datetime, timedelta

import const
from _config import Config
from execute import get_execute
from log import log


class Videos:
    DEPTH = 3
    MD_AVERAGE_LEN = 10

    def __init__(self, cam_key: str):
        self._key = cam_key
        self._cam_path = f"{Config.storage_path}/{Config.cameras[self._key]['folder']}"
        self._range = const.MAX_RANGE
        self._root_folder = []
        self._date_time = ''

    async def get(self, args: dict[str, list]) -> tuple[str, int]:
        date_time = args['dt'][0] if 'dt' in args else ''

        if args['video'][0] == 'next':
            step = int(args['step'][0]) if 'step' in args else 0
            sensitivity = int(args['md'][0]) if 'md' in args else -1
            return await self._get_next(step, date_time, sensitivity)

        elif args['video'][0] == 'range':
            rng = int(args['range'][0]) if 'range' in args else const.MAX_RANGE
            return await self._get_by_range(rng)

        return await self._get_live(date_time)

    def get_datetime_by_path(self, path: str) -> str:
        relative_path = path[len(self._cam_path) + 1:]
        no_ext = re.sub(r'\.[^.]+$', '', relative_path)
        return re.sub(r'\D', '', no_ext)

    def get_range_by_path(self, path: str) -> str:
        if self._range > const.MAX_RANGE:
            return str(self._range)
        start_date = self._get_start_date()
        total_seconds = (datetime.now() - start_date).total_seconds()
        delta_seconds = (
            datetime.strptime(self.get_datetime_by_path(path), const.DT_WEB_FORMAT) - start_date
        ).total_seconds()
        return str(round(const.MAX_RANGE * delta_seconds / total_seconds))

    async def _get_live(self, date_time: str = '', cnt: int = 0) -> tuple[str, int]:
        cnt += 1
        if cnt > 20:  # 20 * 0.5 = 10 sec max (avoid "gateway timeout" error)
            return '', 0

        self._range = const.MAX_RANGE + 1

        path, size = self._get_live_file()  # checks now and last minute folder
        if not size:
            fallback = (datetime.now() - timedelta(minutes=1)).strftime(const.DT_PATH_FORMAT).split('/')
            return await self._find_nearest_file('/'.join(fallback[0:-1]), fallback[-1], -1)

        segment_date_time = self.get_datetime_by_path(path)
        if not date_time or segment_date_time > date_time or not Config.storage_enabled:
            return path, size

        await asyncio.sleep(0.5)
        return await self._get_live(date_time, cnt)

    async def _get_by_range(self, rng: int) -> tuple[str, int]:
        rng = min(max(rng, 0), const.MAX_RANGE)

        start_date = self._get_start_date()
        time_range = datetime.now() - start_date
        delta_minutes = int(time_range.total_seconds() * rng / const.MAX_RANGE / 60)
        wd = (start_date + timedelta(minutes=delta_minutes)).strftime(const.DT_PATH_FORMAT)

        parts = wd.split('/')

        return await self._find_nearest_file('/'.join(parts[0:-1]), parts[-1], 1)

    async def _get_next(self, step: int, date_time: str, sensitivity: int) -> tuple[str, int]:
        if not date_time:
            return await self._get_live()

        self._date_time = date_time

        if sensitivity >= 0:
            return await self._get_next_motion(sensitivity, step)

        file_path = self._get_path_by_datetime(date_time)
        parts = file_path.split('/')
        wd = '/'.join(parts[0:-1])

        files = []
        if -10 < step < 0:
            prev_dir = (datetime.strptime(date_time, const.DT_WEB_FORMAT) - timedelta(minutes=1)
                        ).strftime(const.DT_PATH_FORMAT)
            files = self._get_files_by_folders([prev_dir, wd])
        elif 0 < step < 10:
            next_dir = (datetime.strptime(date_time, const.DT_WEB_FORMAT) + timedelta(minutes=1)
                        ).strftime(const.DT_PATH_FORMAT)
            files = self._get_files_by_folders([wd, next_dir])
        if files and abs(step) < len(files):
            arr = files if step > 0 else reversed(files)
            working_path = f'{self._cam_path}/{file_path}'
            i = 0
            for file in arr:
                f = file.split()
                path = f[1]
                if (step > 0 and path <= working_path) or (step < 0 and path >= working_path):
                    continue
                i += 1
                if i < abs(step):
                    continue
                if int(f[0]) > const.MIN_FILE_SIZE:
                    return path, int(f[0])

        sign = 1 if step > 0 else -1
        seconds = max(60, abs(step))
        folder = (
            datetime.strptime(wd, const.DT_PATH_FORMAT) + timedelta(seconds=seconds) * sign
        ).strftime(const.DT_PATH_FORMAT)

        if step > 0 and folder > datetime.now().strftime(const.DT_PATH_FORMAT):
            return await self._get_live(date_time)

        step = -2 if step < 0 else 1
        parts = folder.split('/')
        return await self._find_nearest_file('/'.join(parts[0:-1]), parts[-1], step)

    def _get_start_date(self) -> datetime:
        return datetime.strptime(self._get_folders()[0], const.DT_ROOT_FORMAT)

    async def _find_nearest_file(self, parent: str, folder: str, step: int) -> tuple[str, int]:
        """ If folder is set shift left (to parent folder); else shift right (to child folder) """
        parts = parent.split('/') if parent else []

        if (folder and len(parts) == self.DEPTH - 1) or (not folder and len(parts) == self.DEPTH):
            path = f'{parent}/{folder}'.rstrip('/')
            position = step - 1 if step > 0 else step
            file, size = self._get_file(path, position)
            if size:
                return file, size

        folders = self._get_folders(parent)
        if not folders and len(parts) > 0:
            return await self._find_nearest_file('/'.join(parts[0:-1]), parts[-1], step)  # shift left

        if folder:
            if step < 0:  # find the largest element of folders less than folder
                rest = [i for i in folders if i < folder]
            else:  # find the smallest element of folders greater than folder
                rest = [i for i in folders if i > folder]
            if rest:
                parts.append(max(rest) if step < 0 else min(rest))
                return await self._find_nearest_file('/'.join(parts), '', step)  # shift right

            if len(parts) > 0:
                return await self._find_nearest_file('/'.join(parts[0:-1]), parts[-1], step)  # shift left
            elif step < 0:
                return await self._find_nearest_file('', '', 1)  # move to the beginning
            else:
                return await self._get_live()  # move to the end

        if not folder and folders and len(parts) < self.DEPTH:
            parts.append(folders[-1]) if step < 0 else parts.append(folders[0])
            return await self._find_nearest_file('/'.join(parts), '', step)  # shift right

        log(f'find_nearest_file: not found: {parent}[/{folder}], step={step}')

        return '', 0

    async def _get_next_motion(self, sensitivity: int, step: int) -> tuple[str, int]:
        sign = 1 if step > 0 else -1
        if step >= 60 or step <= -60:
            folder = (
                datetime.strptime(self._date_time, const.DT_WEB_FORMAT) + timedelta(seconds=abs(step)) * sign
            ).strftime(const.DT_PATH_FORMAT)
        else:
            path = self._get_path_by_datetime(self._date_time)
            folder = '/'.join(path.split('/')[0:-1])

        last_files = {}
        prev_folder = (
            datetime.strptime(folder, const.DT_PATH_FORMAT) - timedelta(minutes=1) * sign
        ).strftime(const.DT_PATH_FORMAT)
        files = self._get_files(prev_folder)
        if files:
            for file in files:
                f = file.split(' ')
                last_files[f'{prev_folder}/{f[1]}'] = int(f[0])

        return await self._motion_detector(folder, last_files, 100 - max(0, min(90, sensitivity)), sign)

    async def _motion_detector(
            self, folder: str, last_files: dict[str, int], sensitivity: int, sign: int) -> tuple[str, int]:
        requested_path = self._get_path_by_datetime(self._date_time)
        files = self._get_files(folder)
        if not files:
            if sign > 0 and folder >= self._get_folders()[-1]:
                return await self._get_live()
            if sign < 0 and folder <= self._get_folders()[0]:
                return '', 0

            file = await self._find_nearest_file(folder, '', sign)
            if file:
                next_folder = '/'.join(file[0][len(self._cam_path) + 1:].split('/')[0:-1])
                if (sign > 0 and next_folder <= folder) or (sign < 0 and next_folder >= folder):
                    return '', 0
                return await self._motion_detector(next_folder, last_files, sensitivity, sign)

        sens = 1 + sensitivity / 100
        if sign < 0:
            files.reverse()
        for file in files:
            f = file.split(' ')
            if float(f[0]) < const.MIN_FILE_SIZE:  # exclude broken files
                continue
            average_size = sum(last_files.values()) / len(last_files) if last_files else 0

            last_files[f'{folder}/{f[1]}'] = int(f[0])
            if len(last_files) > self.MD_AVERAGE_LEN:
                first_key = next(iter(last_files))
                del last_files[first_key]

            path = f'{folder}/{f[1]}'

            if (sign > 0 and requested_path >= path) or (sign < 0 and requested_path <= path):
                continue  # don't detect the files before last motion & last motion itself

            if average_size and float(f[0]) > average_size * sens:
                return f'{self._cam_path}/{folder}/{f[1]}', int(f[0])

        if folder >= datetime.now().strftime(const.DT_PATH_FORMAT):
            return await self._get_live()

        next_folder = (
            datetime.strptime(folder, const.DT_PATH_FORMAT) + timedelta(minutes=1) * sign
        ).strftime(const.DT_PATH_FORMAT)

        return await self._motion_detector(next_folder, last_files, sensitivity, sign)

    def _get_folders(self, folder: str = '') -> list[str]:
        if not folder and self._root_folder:
            return self._root_folder
        ls = get_execute(f'ls {self._cam_path}/{folder}').splitlines()
        if not folder:
            self._root_folder = ls
        return ls

    def _get_files(self, folder: str) -> list[str]:
        wd = f"{self._cam_path}/{folder}"
        return get_execute(f'ls -l {wd} | awk ' + "'{print $5,$9}'").splitlines()

    def _get_files_by_folders(self, folders: list[str]) -> list[str]:
        paths = ''
        for folder in folders:
            paths = f'{paths}{self._cam_path}/{folder}/* '
        return get_execute(f'ls -l {paths} | awk ' + "'{print $5,$9}'").splitlines()

    def _get_file(self, folder: str, position: int = 0) -> tuple[str, int]:
        files = self._get_files(folder)
        if not files or len(files) <= position or len(files) < abs(position):
            return '', 0
        file = files[position].split()  # [size, file]
        path = f'{self._cam_path}/{folder}/{file[1]}'
        size = int(file[0])
        if size > const.MIN_FILE_SIZE:
            return path, size
        if position < 0 and len(files) > abs(position):
            return self._get_file(folder, position - 1)
        return '', 0

    def _get_live_file(self):
        folder = datetime.now().strftime(const.DT_PATH_FORMAT)  # Regular case
        files = self._get_files(folder)
        position = -2
        if len(files) > 1:
            file = files[position].split()  # [size, file]
            size = int(file[0])
            if size < const.MIN_FILE_SIZE:
                return '', 0

            path = f'{self._cam_path}/{folder}/{file[1]}'
            return path, size

        elif files:
            position = -1

        folder = (datetime.now() - timedelta(minutes=1)).strftime(const.DT_PATH_FORMAT)  # Possible case
        return self._get_file(folder, position)

    @staticmethod
    def _get_path_by_datetime(dt: str) -> str:
        if not re.match(r'^\d{14}$', dt):
            return ''
        return f'{dt[0:4]}-{dt[4:6]}-{dt[6:8]}/{dt[8:10]}/{dt[10:12]}/{dt[12:14]}.mp4'
