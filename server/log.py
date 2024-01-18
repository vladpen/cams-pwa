import time
from subprocess import Popen

from _config import Config


class Log:
    @staticmethod
    def write(info) -> None:
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        if Config.debug:
            print(f'* {now} {info.strip()}')
            return

        # No strict necessary to use system command here, but it's the easiest way
        info = info.replace('"', '\\"')
        text = f'{now} {info}'
        cmd = f'echo "{text}" >> {Config.log_file}'
        Popen(cmd, shell=True)
