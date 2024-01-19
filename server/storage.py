import time
from datetime import datetime, timedelta

import const
from cmd import execute_async, execute, get_execute
from _config import Config
from videos import Videos
from share import Share
from log import Log


class Storage:
    def __init__(self, camera_hash):
        self._hash = camera_hash
        self._cam_path = f"{Config.storage_path}/{Config.cameras[self._hash]['folder']}"
        self._start_time = None
        self._last_rotation_date = ''
        self._videos = Videos(self._hash)

    def run(self) -> None:
        """ Start fragments saving """
        try:
            self._start_saving('run')
        except Exception as e:
            Log.write(f"Storage: ERROR: can't start saving {self._hash} ({repr(e)})")

    def _start_saving(self, caller: str) -> None:
        """ We'll use system (linux) commands for this job
        """
        self._mkdir(datetime.now().strftime(const.DT_PATH_FORMAT))

        cfg = Config.cameras[self._hash]
        if 'storage_command' in cfg and cfg['storage_command']:
            cmd = cfg['storage_command']
        else:
            cmd = Config.storage_command
        cmd = cmd.replace('{url}', cfg['url']).replace('{cam_path}', f'{self._cam_path}')

        self.main_process = execute_async(cmd)
        self._start_time = datetime.now()

        Log.write(f'* Storage: {caller}: start main process {self.main_process.pid} for {self._hash}')

    def _mkdir(self, folder: str) -> None:
        """ Create storage folder if not exists
        """
        execute(f'mkdir -p {self._cam_path}/{folder}')

    def watchdog(self) -> None:
        """ Infinite loop for checking camera(s) availability
        """
        Log.write(f'* Storage: start watchdog for {self._hash}')
        while True:
            time.sleep(Config.min_segment_duration)
            try:
                self._watchdog()
            except Exception as e:
                Log.write(f"Storage: watchdog ERROR: can't check the storage {self._hash} ({repr(e)})")

    def _watchdog(self) -> None:
        """ Extremely important piece.
            Checks if saving is frozen and creates next working directory.
            Cameras can turn off on power loss, or external commands can freeze.
        """
        if not self._start_time:
            return

        self._mkdir((datetime.now() + timedelta(minutes=1)).strftime(const.DT_PATH_FORMAT))
        self._cleanup()

        prev_dir = f'{self._cam_path}/{(datetime.now() - timedelta(minutes=1)).strftime(const.DT_PATH_FORMAT)}'
        working_dir = f'{self._cam_path}/{datetime.now().strftime(const.DT_PATH_FORMAT)}'
        ls = get_execute(f'ls -l {prev_dir}/* {working_dir}/* | awk ' + "'{print $5,$9}'").splitlines()
        if ls:
            ls = ls[-10:]
        if ls:
            self._live_motion_detector(ls[:-1])
        if ls or not self._start_time or (datetime.now() - self._start_time).total_seconds() < 60.0:
            return  # normal case

        Log.write(f'Storage: FREEZE detected for "{self._hash}"')

        # Freeze detected, restart
        try:
            self._start_time = None
            self.main_process.kill()
            # execute(f"kill -9 `pgrep -f '{self.main_cmd[:80]}'`")  # also kill all possible zombies
            daily_dir = f'{self._cam_path}/{datetime.now().strftime(const.DT_ROOT_FORMAT)}'
            self._delete_unfinished(daily_dir)
        except Exception as e:
            Log.write(f'Storage: watchdog: kill {self.main_process.pid} ERROR "{self._hash}" ({repr(e)})')

        self._start_saving('watchdog')

        # Remove previous folders if empty
        prev_min = datetime.now() - timedelta(minutes=1)
        if not self._remove_folder_if_empty(prev_min.strftime(const.DT_PATH_FORMAT)):
            return
        if not self._remove_folder_if_empty(prev_min.strftime(f'{const.DT_ROOT_FORMAT}/%H')):
            return
        self._remove_folder_if_empty(prev_min.strftime(const.DT_ROOT_FORMAT))

    def _live_motion_detector(self, file_list) -> None:
        cfg = Config.cameras[self._hash]
        if cfg['sensitivity'] <= 1 or len(file_list) < 2:
            return
        total_size = 0
        cnt = 0
        for file in file_list[:-1]:
            f = file.split(' ')
            if int(f[0]) <= const.MIN_FILE_SIZE:
                continue
            total_size += int(f[0])
            cnt += 1
        if not cnt:
            return

        last_file = file_list[-1].split(' ')
        average_size = total_size / cnt

        if float(last_file[0]) > average_size * cfg['sensitivity']:
            date_time = self._videos.get_datetime_by_path(last_file[1])
            if self._hash in Share.cam_motions and Share.cam_motions[self._hash] >= date_time:
                return
            Share.cam_motions[self._hash] = date_time
            Log.write(f'Storage: motion detected: {date_time[:8]} {date_time[8:]} {self._hash}')

    def _remove_folder_if_empty(self, folder) -> bool:
        path = f'{self._cam_path}/{folder}'

        ls = get_execute(f'ls -A {path}')
        if ls:
            return False  # not empty

        execute(f'rmdir {path}')
        return True

    def _cleanup(self) -> None:
        """ Cleanup (once a day)
        """
        now_date = datetime.now().strftime(const.DT_ROOT_FORMAT)
        if self._last_rotation_date and self._last_rotation_date == now_date:
            return
        self._last_rotation_date = now_date

        ls = get_execute(f'ls -d {self._cam_path}/*').splitlines()
        if not ls:
            return

        oldest_folder = (datetime.now() - timedelta(days=Config.storage_period_days)).strftime(const.DT_ROOT_FORMAT)

        for row in ls[:-1]:
            wd = row.split('/')[-1]
            if not wd:
                break
            if wd < oldest_folder:
                execute_async(f'rm -rf {self._cam_path}/{wd}')
                Log.write(f'Storage: remove {self._hash} {wd}')
                continue
            self._delete_unfinished(wd)

        Log.write(f'Storage: cleanup done {self._hash}')

    def _delete_unfinished(self, wd) -> None:
        # Remove unfinished (low sized) files & empty folders
        execute(f'find {self._cam_path}/{wd} -type f -size -{const.MIN_FILE_SIZE}c -delete')
        execute_async(f'find {self._cam_path}/{wd} -type d -empty -delete')
