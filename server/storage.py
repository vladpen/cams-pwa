import time
import re
from datetime import datetime, timedelta

import const
from execute import execute_async, execute, get_execute, get_returncode
from _config import Config
from videos import Videos
from share import Share
from log import log

FREEZE_INTERVAL = 30.0
KILL_TIMEOUT = 5


class Storage:
    def __init__(self, camera_key):
        self._key = camera_key
        self._cam_path = f"{Config.storage_path}/{Config.cameras[self._key]['folder']}"
        self._start_time = None
        self._main_process = None
        self._last_rotation_date = ''
        self._videos = Videos(self._key)

    def run(self) -> None:
        """ Start fragments saving """
        try:
            self._start_saving('run')
        except Exception as e:
            log(f"Storage: can't start saving {self._key} ({repr(e)})", True)

    def _start_saving(self, caller: str) -> None:
        """ We'll use system (linux) commands for this job
        """
        self._mkdir(datetime.now().strftime(const.DT_PATH_FORMAT))

        cfg = Config.cameras[self._key]
        if 'storage_command' in cfg and cfg['storage_command']:
            cmd = cfg['storage_command']
        else:
            cmd = Config.storage_command

        cam_ip = re.findall(r'\d+(?:\.\d+){3}', cfg['url'])
        if not cam_ip:
            log(f"Storage: can't parse cam IP from URL for {self._key}", True)
            return

        self._start_time = datetime.now()

        ping = get_returncode(f'ping -c 1 -W 1 {cam_ip[0]}')
        if ping != 0:
            log(f'Storage: OFFLINE: {self._key} ({cam_ip[0]})')
            return

        cmd = cmd.replace('{url}', f'"{cfg['url']}"').replace('{cam_path}', f'{self._cam_path}')

        self._main_process = execute_async(cmd)

        log(f'* Storage: {caller}: start saving process {self._main_process.pid} {self._key}')

    def _mkdir(self, folder: str) -> None:
        """ Create storage folder if not exists
        """
        execute(f'mkdir -p {self._cam_path}/{folder}')

    def watchdog(self) -> None:
        """ Infinite loop for checking camera(s) availability
        """
        log(f'* Storage: watchdog: start {self._key}')
        while True:
            time.sleep(Config.min_segment_duration)
            try:
                self._watchdog()
            except Exception as e:
                log(f'Storage: watchdog: {self._key} ({repr(e)})', True)

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
        if ls or not self._start_time or (datetime.now() - self._start_time).total_seconds() < FREEZE_INTERVAL:
            return  # normal case

        log(f'Storage: FREEZE: {self._key}')

        # Freeze detected, restart
        self._start_time = None

        if self._main_process:
            try:
                self._main_process.kill()
                daily_dir = datetime.now().strftime(const.DT_ROOT_FORMAT)
                self._delete_unfinished(daily_dir)
                # Wait for the process die to avoid "zombie"
                # Perhaps the timeout should be greater than DefaultTimeoutStopSec in /etc/systemd/system.conf
                time.sleep(KILL_TIMEOUT)
            except Exception as e:
                log(f"Storage: watchdog: can't kill {self._main_process.pid} {self._key} ({repr(e)})", True)

        self._start_saving('watchdog')

        # Remove previous folders if empty
        prev_min = datetime.now() - timedelta(minutes=1)
        if not self._remove_folder_if_empty(prev_min.strftime(const.DT_PATH_FORMAT)):
            return
        if not self._remove_folder_if_empty(prev_min.strftime(f'{const.DT_ROOT_FORMAT}/%H')):
            return
        self._remove_folder_if_empty(prev_min.strftime(const.DT_ROOT_FORMAT))

    def _live_motion_detector(self, file_list) -> None:
        cfg = Config.cameras[self._key]
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
            if self._key in Share.cam_motions and Share.cam_motions[self._key] >= date_time:
                return
            Share.cam_motions[self._key] = date_time
            mtime = f'{date_time[8:10]}:{date_time[10:12]}:{date_time[12:14]}'
            log(f'Storage: motion detected: {mtime} {self._key}')

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

        cnt = len(ls)
        for row in ls[:-1]:
            wd = row.split('/')[-1]
            if not wd:
                break
            if wd < oldest_folder and cnt > Config.storage_period_days:
                execute_async(f'rm -rf {self._cam_path}/{wd}')
                cnt -= 1
                log(f'Storage cleanup: remove {self._key} {wd}')
            else:
                self._delete_unfinished(wd)

        log(f'Storage: cleanup done {self._key}')

    def _delete_unfinished(self, wd) -> None:
        # Remove unfinished (low sized) files & empty folders
        execute(f'find {self._cam_path}/{wd} -type f -size -{const.MIN_FILE_SIZE}c -delete')
        execute_async(f'find {self._cam_path}/{wd} -type d -empty -delete')
