import time
from subprocess import Popen
from _config import Config


class Log:
    @staticmethod
    def print(info) -> None:
        if Config.debug:
            print(info.strip())

    @staticmethod
    def write(info, host: str = None) -> None:
        print(f'*** {info.strip()} ***')
        if host == '127.0.0.1':
            return

        # No strict necessary to use system command here, but it's the easiest way
        info = info.replace('"', '\\"')
        text = f'{time.strftime("%Y-%m-%d %H:%M:%S")} {info}'
        cmd = f'echo "{text}" >> {Config.log_file}'
        Popen(cmd, shell=True)
