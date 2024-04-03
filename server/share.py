import subprocess
from datetime import datetime
from _config import Config


class Share:
    cam_motions = {}

    _default_gateway_ip = ''
    _is_system_busy = 'false'
    _system_busy_ts = 0.0

    @staticmethod
    def get_default_gateway_ip() -> str:
        if Share._default_gateway_ip:
            return Share._default_gateway_ip
        try:
            Share._default_gateway_ip = subprocess.run(
                'ip route | grep default', shell=True, capture_output=True
            ).stdout.decode().split(' ')[2]
        finally:
            return Share._default_gateway_ip

    @staticmethod
    def is_system_busy() -> str:
        if not hasattr(Config, 'is_system_busy_command') or not Config.is_system_busy_command:
            return Share._is_system_busy

        now_ts = datetime.now().timestamp()
        if now_ts - Share._system_busy_ts < 5.0:
            return Share._is_system_busy
        Share._system_busy_ts = now_ts

        try:
            if subprocess.run(Config.is_system_busy_command, shell=True, capture_output=True).stdout:
                Share._is_system_busy = 'true'
            else:
                Share._is_system_busy = 'false'
        finally:
            return Share._is_system_busy
