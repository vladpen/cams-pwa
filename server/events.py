import re
import time
from datetime import datetime, timedelta
from typing import List

import const
from _config import Config
from execute import execute_async, execute, get_execute
from share import Share
from log import Log


class Events:
    CHECK_INTERVAL_SEC = 2

    def __init__(self, camera_hash):
        self._hash = camera_hash
        self._cam_config = Config.cameras[self._hash]
        self._events_path = f"{Config.events_path}/{self._cam_config['folder']}"
        self._last_event = ''
        self._last_rotation_date = ''
        self._root_folders = []

    def check(self) -> None:
        """ Check camera events (motion detector) and rotate folders
        """
        Log.write(f'* Events: start handling {self._hash}')
        while True:
            time.sleep(self.CHECK_INTERVAL_SEC)
            try:
                self._rotate()
                self._check()
            except Exception as e:
                Log.write(f"Events ERROR: can't handle {self._hash} ({repr(e)})")

    def _check(self) -> None:
        folders = self._get_root_folders()
        if not folders:
            return
        live_path = f'{self._events_path}/{folders[-1]}'

        last_event_iso = get_execute(f'ls --full-time {live_path} | tail -1 | awk ' + "'{print $6,$7}'")
        # example: 2024-05-18 10:49:33.898542994
        no_milliseconds = re.sub(r'\.[^.]+$', '', last_event_iso)  # remove milliseconds
        last_event_digits = re.sub(r'\D', '', no_milliseconds)  # remove all non-digit characters
        if not last_event_digits:
            return
        if self._last_event and last_event_digits <= self._last_event:
            return

        Share.cam_motions[self._hash] = last_event_digits
        if not self._last_event:
            self._last_event = last_event_digits
            return

        self._last_event = last_event_digits
        Log.write(f'Events: motion detected: {no_milliseconds} {self._hash}')

    def _rotate(self) -> None:
        now_date = datetime.now().strftime(const.DT_ROOT_FORMAT)
        if self._last_rotation_date and self._last_rotation_date == now_date:
            return
        self._last_rotation_date = now_date

        self._cleanup()

        # Rotation
        yesterday_folder = (datetime.now() - timedelta(days=1)).strftime(const.DT_ROOT_FORMAT)

        folders = self._get_root_folders()
        if not folders:
            return
        live_path = f'{self._events_path}/{folders[-1]}'

        # check live folder is empty
        if not get_execute(f"[ '$(ls -A {live_path})' ] && echo 1 || echo ''"):
            return

        # check yesterday folder exists
        if get_execute(f'test -d {self._events_path}/{yesterday_folder} && echo 1'):
            return

        execute(
            f'mkdir -p {self._events_path}/{yesterday_folder} '
            f'&& mv {live_path}/* {self._events_path}/{yesterday_folder}')

        Log.write(f'Events: rotation at {now_date} {self._hash}')

    def _cleanup(self) -> None:
        oldest_folder = (datetime.now() - timedelta(days=Config.events_period_days)).strftime(const.DT_ROOT_FORMAT)

        ls = get_execute(f'ls -d {self._events_path}/*').splitlines()
        if not ls:
            return

        for row in ls:
            wd = row.split('/')[-1]
            if wd >= oldest_folder or not wd:
                break
            execute_async(f'rm -rf {self._events_path}/{wd}')
            Log.write(f'Events cleanup: remove {self._hash} {wd}')

    def _get_root_folders(self) -> List[str]:
        if self._root_folders:
            return self._root_folders
        ls = get_execute(f'ls {self._events_path}').splitlines()
        if not ls:
            return self._root_folders
        self._root_folders = ls
        return self._root_folders
