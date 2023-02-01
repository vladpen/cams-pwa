import asyncio
from datetime import datetime, timedelta
from _config import Config
from log import Log


class Storage:
    CLEANUP_HOUR_MINUTE = '0000'

    def __init__(self, camera_hash):
        self._hash = camera_hash
        self._cam_path = f'{Config.storage_path}/{Config.cameras[self._hash]["path"]}'

    async def run(self) -> None:
        """ Start fragments saving
        """
        try:
            await self._start_saving()
        except Exception as e:
            Log.write(f'Storage: ERROR: can\'t start saving "{self._hash}" ({repr(e)})')

    async def _start_saving(self, caller: str = '') -> None:
        """ We'll use system (linux) commands for this job
        """
        await self._mkdir(datetime.now().strftime('%Y%m%d/%H/%M'))

        cfg = Config.cameras[self._hash]
        cmd = Config.storage_command.replace('{url}', cfg['url']).replace('{cam_path}', f'{self._cam_path}')

        # Run given command in background
        # Important: don't use create_subprocess_SHELL for this command!
        #
        self.main_process = await asyncio.create_subprocess_exec(*cmd.split())

        Log.write(f'Storage:{caller} start main process {self.main_process.pid} for "{self._hash}"')

    async def _mkdir(self, folder: str) -> None:
        """ Create storage folder if not exists
        """
        cmd = f'mkdir -p {self._cam_path}/{folder}'
        p = await asyncio.create_subprocess_shell(cmd)
        await p.wait()

    async def watchdog(self) -> None:
        """ Infinite loop for checking camera(s) availability
        """
        while True:
            await asyncio.sleep(Config.watchdog_interval)
            try:
                await self._watchdog()
            except Exception as e:
                Log.print(f'Storage: watchdog ERROR: can\'t restart storage "{self._hash}" ({repr(e)})')

    async def _watchdog(self) -> None:
        """ Extremely important piece.
            Checks if saving is frozen and creates next working directory.
            Cameras can turn off on power loss, or external commands can freeze.
        """
        wd = f'{Config.cameras[self._hash]["path"]}/{datetime.now().strftime("%Y%m%d/%H/%M")}'
        path = f'{Config.storage_path}/{wd}'
        cmd = f'ls {path} | wc -l'
        p = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        stdout, _stderr = await p.communicate()
        cnt = int(stdout.decode().strip())

        Log.print(f'Storage: watchdog: check {wd}: {cnt} file(s) found')

        await self._mkdir((datetime.now() + timedelta(minutes=1)).strftime('%Y%m%d/%H/%M'))
        await self._cleanup()

        if cnt or datetime.now().strftime('%S') < str(Config.watchdog_interval):
            return  # normal case or possible not ended yet

        # Freezing detected, restart
        try:
            self.main_process.kill()
        except Exception as e:
            Log.print(f'Storage: watchdog: kill {self.main_process.pid} ERROR "{self._hash}" ({repr(e)})')

        await self._start_saving('watchdog: ')

        # Remove previous folders if empty
        prev_min = datetime.now() - timedelta(minutes=1)
        await self._remove_folder_if_empty(prev_min.strftime('%Y%m%d/%H/%M'))
        await self._remove_folder_if_empty(prev_min.strftime('%Y%m%d/%H'))
        await self._remove_folder_if_empty(prev_min.strftime('%Y%m%d'))

    async def _remove_folder_if_empty(self, folder) -> None:
        path = f'{Config.storage_path}/{Config.cameras[self._hash]["path"]}/{folder}'
        cmd = f'rmdir {path}'
        p = await asyncio.create_subprocess_shell(cmd)
        res = await p.wait()  # returns 0 if success, else 1
        if res == 0:
            Log.print(f'Storage: watchdog: folder removed: "{self._hash}" {folder}')

    async def _cleanup(self) -> None:
        """ Cleanup (5 times per day)
        """
        if datetime.now().strftime('%M') != '00' or datetime.now().strftime('%H') > '05':
            return

        cmd = f'ls -d {self._cam_path}/*'
        p = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        stdout, _stderr = await p.communicate()
        if not stdout:
            return

        oldest_dir_name = (datetime.now() - timedelta(days=Config.storage_period_days + 1)).strftime('%Y%m%d')

        for row in stdout.decode().strip().split('\n'):
            wd = row.split('/')[-1]
            if wd >= oldest_dir_name or not wd:
                break
            cmd = f'rm -rf {self._cam_path}/{wd}'
            p = await asyncio.create_subprocess_shell(cmd)
            await p.wait()

            Log.write(f'Storage: cleanup: remove {self._hash} {wd}')
