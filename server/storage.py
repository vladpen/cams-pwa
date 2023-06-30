import asyncio
from datetime import datetime, timedelta
from _config import Config
from videos import Videos
from share import Share
from log import Log


class Storage:
    DT_ROOT_FORMAT = '%Y-%m-%d'
    DT_FORMAT = '%Y-%m-%d/%H/%M'

    def __init__(self, camera_hash):
        self._hash = camera_hash
        self._cam_path = f'{Config.storage_path}/{Config.cameras[self._hash]["folder"]}'
        self._start_time = None
        self._last_rotation_date = ''
        self._videos = Videos(self._hash)

    async def run(self) -> None:
        """ Start fragments saving
        """
        try:
            await self._start_saving()
        except Exception as e:
            Log.write(f"Storage: ERROR: can't start saving {self._hash} ({repr(e)})")

    async def _start_saving(self, caller: str = '') -> None:
        """ We'll use system (linux) commands for this job
        """
        await self._mkdir(datetime.now().strftime(self.DT_FORMAT))

        cfg = Config.cameras[self._hash]
        if 'storage_command' in cfg and cfg['storage_command']:
            cmd = cfg['storage_command']
        else:
            cmd = Config.storage_command
        cmd = cmd.replace('{url}', cfg['url']).replace('{cam_path}', f'{self._cam_path}')

        # Run given command in background
        # Important: don't use create_subprocess_SHELL for this command!
        #
        await asyncio.sleep(0.1)
        self.main_process = await asyncio.create_subprocess_exec(*cmd.split())
        self._start_time = datetime.now()
        await asyncio.sleep(0.1)

        Log.write(f'Storage:{caller} start main process {self.main_process.pid} for {self._hash}')

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
            await asyncio.sleep(Config.min_segment_duration)
            try:
                await self._watchdog()
            except Exception as e:
                Log.write(f"Storage: watchdog ERROR: can't check the storage {self._hash} ({repr(e)})")

    async def _watchdog(self) -> None:
        """ Extremely important piece.
            Checks if saving is frozen and creates next working directory.
            Cameras can turn off on power loss, or external commands can freeze.
        """
        if not self._start_time:
            return

        prev_dir = f'{self._cam_path}/{(datetime.now() - timedelta(minutes=1)).strftime(self._videos.DT_FORMAT)}'
        working_dir = f'{self._cam_path}/{datetime.now().strftime(self._videos.DT_FORMAT)}'
        cmd = f'ls -l {prev_dir}/* {working_dir}/* | awk ' + "'{print $5,$9}'"
        p = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        stdout, _stderr = await p.communicate()
        res = stdout.decode().strip().splitlines()[-10:]

        await self._mkdir((datetime.now() + timedelta(minutes=1)).strftime(self.DT_FORMAT))
        await self._cleanup()

        self._live_motion_detector(res[:-1])

        if res or not self._start_time or (datetime.now() - self._start_time).total_seconds() < 60.0:
            return  # normal case

        Log.print(f'Storage: FREEZE detected for "{self._hash}"')

        # Freeze detected, restart
        try:
            self._start_time = None
            self.main_process.kill()
        except Exception as e:
            Log.print(f'Storage: watchdog: kill {self.main_process.pid} ERROR "{self._hash}" ({repr(e)})')

        await self._start_saving('watchdog: ')

        # Remove previous folders if empty
        prev_min = datetime.now() - timedelta(minutes=1)
        await self._remove_folder_if_empty(prev_min.strftime(self.DT_FORMAT))
        await self._remove_folder_if_empty(prev_min.strftime(f'{self.DT_ROOT_FORMAT}/%H'))
        await self._remove_folder_if_empty(prev_min.strftime(self.DT_ROOT_FORMAT))

    def _live_motion_detector(self, file_list) -> None:
        cfg = Config.cameras[self._hash]
        if cfg['sensitivity'] <= 1 or len(file_list) < 2:
            return
        total_size = 0
        cnt = 0
        for file in file_list[:-1]:
            f = file.split(' ')
            if int(f[0]) <= self._videos.MIN_FILE_SIZE:
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
            Log.print(f'Storage: motion detected: {date_time} {self._hash}')

    async def _remove_folder_if_empty(self, folder) -> None:
        path = f'{Config.storage_path}/{Config.cameras[self._hash]["folder"]}/{folder}'
        cmd = f'rmdir {path}'
        p = await asyncio.create_subprocess_shell(cmd)
        res = await p.wait()  # returns 0 if success, else 1
        if res == 0:
            Log.write(f'Storage: watchdog: folder {folder} removed from {self._hash}')

    async def _cleanup(self) -> None:
        """ Cleanup (once a day)
        """
        now_date = datetime.now().strftime(self.DT_ROOT_FORMAT)
        if self._last_rotation_date and self._last_rotation_date == now_date:
            return
        self._last_rotation_date = now_date

        cmd = f'ls -d {self._cam_path}/*'
        p = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        stdout, _stderr = await p.communicate()
        if not stdout:
            return

        oldest_folder = (datetime.now() - timedelta(days=Config.storage_period_days)).strftime(self.DT_ROOT_FORMAT)

        for row in stdout.decode().strip().split('\n'):
            wd = row.split('/')[-1]
            if wd >= oldest_folder or not wd:
                break
            cmd = f'rm -rf {self._cam_path}/{wd}'
            p = await asyncio.create_subprocess_shell(cmd)
            await p.wait()

            Log.write(f'Storage: cleanup: remove {self._hash} {wd}')
