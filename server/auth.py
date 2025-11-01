import hashlib
import subprocess
from urllib.parse import quote_plus, unquote_plus
from typing import Dict, Optional
from _config import Config
from log import log


class Auth:
    def __init__(self, encrypted):
        self._info = self.decrypt(encrypted)

    def info(self) -> Optional[Dict[str, str]]:
        return self._info

    def login(self, data: Dict[str, str]) -> Optional[Dict[str, str]]:
        if 'psw' not in data or 'cam' not in data:
            return None
        cam_hash = data['cam'].strip()
        psw = data['psw'].strip()
        if not hash or not psw:
            return None
        if cam_hash != Config.master_cam_hash and cam_hash not in Config.cameras:
            return None

        if cam_hash == Config.master_cam_hash and self._get_password_hash(psw) == Config.master_password_hash:
            self._info = {'hash': Config.master_cam_hash}
            return self._info

        if cam_hash in Config.cameras and self._get_password_hash(psw) == Config.cam_password_hash:
            self._info = {'hash': cam_hash}
            return self._info
        return None

        # todo: add cam to list

    @staticmethod
    def encrypt(auth_info: Optional[Dict[str, str]]) -> Optional[str]:
        if not auth_info:
            return None
        decrypted = f"{auth_info['hash']}"
        cmd = (
            f'echo "{decrypted}" | '
            f'openssl enc -e -base64 -aes-256-cbc -k "{Config.encryption_key}" -pbkdf2')
        p = subprocess.run(cmd, shell=True, capture_output=True)
        res = p.stdout.decode()
        if not res:
            log('Auth encryption: the OPENSSL may not be installed', True)
        return quote_plus(res)

    @staticmethod
    def decrypt(encrypted: str) -> Optional[Dict[str, str]]:
        if not encrypted:
            return None
        cmd = (
            f'echo "{unquote_plus(encrypted)}" | '
            f'openssl enc -d -base64 -aes-256-cbc -k "{Config.encryption_key}" -pbkdf2')
        p = subprocess.run(cmd, shell=True, capture_output=True)
        try:
            decrypted = p.stdout.decode().strip().split('\n', 1)
            auth_info = {'hash': decrypted[0]}
            if auth_info['hash'] != Config.master_cam_hash and auth_info['hash'] not in Config.cameras:
                return None
            return auth_info
        except (Exception,):
            return None

    @staticmethod
    def _get_password_hash(psw: str) -> str:
        return hashlib.sha256(psw.encode('UTF-8')).hexdigest()
