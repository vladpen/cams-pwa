import json
import hashlib
import subprocess
from urllib.parse import quote_plus, unquote_plus
from typing import Optional
from _config import Config


class Auth:
    def __init__(self, encrypted):
        self._info = self.decrypt(encrypted)

    def info(self) -> Optional[str]:
        return self._info

    def login(self, json_data: bytes) -> Optional[str]:
        data = json.loads(json_data.decode('UTF-8'))
        if 'psw' not in data or 'cam' not in data:
            return
        if data['cam'] != Config.master_cam_hash and data['cam'] not in Config.cameras:
            return

        if data['cam'] == Config.master_cam_hash and self._get_hash(data['psw']) == Config.master_password_hash:
            self._info = Config.master_cam_hash
            return self._info

        if data['cam'] in Config.cameras and self._get_hash(data['psw']) == Config.cam_password_hash:
            self._info = data['cam']
            return self._info

        # todo: add cam to list

    @staticmethod
    def encrypt(decrypted: str) -> Optional[str]:
        if not decrypted:
            return
        cmd = (
            f'echo "{decrypted.strip()}" | '
            f'openssl enc -e -base64 -aes-256-cbc -k "{Config.encryption_key}" -pbkdf2')
        p = subprocess.run(cmd, shell=True, capture_output=True)
        return quote_plus(p.stdout.decode())

    @staticmethod
    def decrypt(encrypted: str) -> Optional[str]:
        if not encrypted:
            return
        cmd = (
            f'echo "{unquote_plus(encrypted)}" | '
            f'openssl enc -d -base64 -aes-256-cbc -k "{Config.encryption_key}" -pbkdf2')
        p = subprocess.run(cmd, shell=True, capture_output=True)
        try:
            decrypted = p.stdout.decode().strip()
            if decrypted != Config.master_cam_hash and decrypted not in Config.cameras:
                return
            return decrypted
        except Exception:
            return

    @staticmethod
    def _get_hash(psw: str) -> str:
        return hashlib.sha256(psw.encode('UTF-8')).hexdigest()
