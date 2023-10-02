import asyncio
from datetime import datetime, timedelta
from typing import List
from _config import Config
from share import Share
from log import Log


class Events:
    CHECK_INTERVAL_SEC = 2
    DT_ROOT_FORMAT = '%Y-%m-%d'
    DT_WEB_FORMAT = '%Y%m%d%H%M%S'

    def __init__(self, camera_hash):
        self._hash = camera_hash
        self._cam_config = Config.cameras[self._hash]
        self._events_path = f'{Config.events_path}/{self._cam_config["folder"]}'
        self._last_event = ''
        self._last_rotation_date = ''
        self._root_folders = []

    async def run(self) -> None:
        """ Check camera events (motion detector) and rotate folders
        """
        Log.write(f'Events: start handling {self._hash}')
        while True:
            await asyncio.sleep(self.CHECK_INTERVAL_SEC)
            try:
                await self._rotate()
                await self._check()
            except Exception as e:
                Log.write(f"Events ERROR: can't handle {self._hash} ({repr(e)})")

    async def _check(self) -> None:
        folders = await self._get_root_folders()
        if not folders:
            return
        live_path = f'{self._events_path}/{folders[-1]}'

        cmd = f'ls --full-time {live_path} | tail -1 | awk ' + "'{print $6,$7,$8}'"
        last_event_iso = await self._exec(cmd)
        if not last_event_iso:
            return
        last_event_ts = int(datetime.fromisoformat(last_event_iso).timestamp())
        if self._last_event and last_event_ts <= self._last_event:
            return

        Share.cam_motions[self._hash] = last_event_ts
        if not self._last_event:
            self._last_event = last_event_ts
            return

        self._last_event = last_event_ts
        Log.print(f'Events: motion detected: {last_event_iso} {self._hash}')

    async def _rotate(self) -> None:
        now_date = datetime.now().strftime(self.DT_ROOT_FORMAT)
        if self._last_rotation_date and self._last_rotation_date == now_date:
            return
        self._last_rotation_date = now_date

        await self._cleanup()

        # Rotation
        yesterday_folder = (datetime.now() - timedelta(days=1)).strftime(self.DT_ROOT_FORMAT)

        folders = await self._get_root_folders()
        if not folders:
            return
        live_path = f'{self._events_path}/{folders[-1]}'

        # check live folder is empty
        cmd = f'[ "$(ls -A {live_path})" ] && echo 1 || echo ""'
        if not await self._exec(cmd):
            return

        # check yesterday folder is exist
        cmd = f'test -d {self._events_path}/{yesterday_folder} && echo 1'
        if await self._exec(cmd):
            return

        cmd = (
            f'mkdir -p {self._events_path}/{yesterday_folder} '
            f'&& mv {live_path}/* {self._events_path}/{yesterday_folder}')
        p = await asyncio.create_subprocess_shell(cmd)
        await p.wait()

        Log.write(f'Events: rotation at {now_date} {self._hash}')

    async def _cleanup(self) -> None:
        oldest_folder = (datetime.now() - timedelta(days=Config.events_period_days)).strftime(self.DT_ROOT_FORMAT)

        cmd = f'ls -d {self._events_path}/*'
        p = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        stdout, _stderr = await p.communicate()
        if not stdout:
            return

        for row in stdout.decode().strip().split('\n'):
            wd = row.split('/')[-1]
            if wd >= oldest_folder or not wd:
                break
            cmd = f'rm -rf {self._events_path}/{wd}'
            p = await asyncio.create_subprocess_shell(cmd)
            await p.wait()

            Log.write(f'Events cleanup: remove {self._hash} {wd}')

    async def _get_root_folders(self) -> List[str]:
        if self._root_folders:
            return self._root_folders
        cmd = f'ls {self._events_path}'
        self._root_folders = (await self._exec(cmd)).splitlines()
        return self._root_folders

    async def _exec(self, cmd) -> str:
        p = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        stdout, _stderr = await p.communicate()
        if not stdout:
            return ''
        return stdout.decode().strip()
