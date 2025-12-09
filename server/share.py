import subprocess
from datetime import datetime


class Share:
    cam_motions = {}
    sse_clients = {}
    start_datetime = datetime.now().strftime('%d%H%M')
    _default_gateway_ip = ''

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
