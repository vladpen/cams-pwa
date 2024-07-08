import asyncio
from http.cookies import SimpleCookie
from typing import Dict, List

from auth import Auth
from log import Log


class Response:
    def __init__(self, writer: asyncio.streams.StreamWriter, request: Dict):
        self.writer = writer
        self.request = request
        self.cookie = SimpleCookie()
        if 'cookie' in request['headers']:
            self.cookie.load(request['headers']['cookie'])
        self.auth = Auth(self.cookie['auth'].value if 'auth' in self.cookie else None)
        self.headers = []
        self.body = b''

    @staticmethod
    async def send_error(writer:  asyncio.streams.StreamWriter, code: int, msg: str, error: str) -> None:
        codes = {400: 'Bad Request', 403: 'Forbidden', 404: 'Not Found'}
        if code not in codes:
            code = 400

        headers = [f'HTTP/1.1 {code} {codes[code]}', '', '',]
        writer.write(('\r\n'.join(headers)).encode('UTF-8'))
        await writer.drain()
        writer.close()
        Log.write(f'Request {msg} {code} ERROR ({error})')

    async def send(self, headers: List, content: bytes, request_start_line: str) -> None:
        headers = ['HTTP/1.1 200 OK'] + headers + ['', '']
        headers = ('\r\n'.join(headers)).encode('UTF-8')
        self.writer.write(headers + content)
        await self.writer.drain()
        self.writer.close()

        peer = self.request['headers']['x-real-ip']
        host = self.request['headers']['x-host']
        Log.write(f'Request {peer} > {host} "{request_start_line}" 200')

    @staticmethod
    async def read_file(filename: str) -> bytes:
        p = await asyncio.create_subprocess_shell(
            f'cat {filename}',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        stdout, _stderr = await p.communicate()
        return stdout
