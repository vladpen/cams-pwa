import asyncio
from urllib.parse import unquote

from log import log


class Response:
    def __init__(self, writer: asyncio.streams.StreamWriter, request: dict, start_line: str):
        self._writer = writer
        self.request = request
        self.start_line = start_line
        self.headers = []
        self.body = b''
        self.handle_sse = None
        self.close_sse_connection = False

    @staticmethod
    async def send_error(writer:  asyncio.streams.StreamWriter, code: int, msg: str, error: str) -> None:
        codes = {400: 'Bad Request', 403: 'Forbidden', 404: 'Not Found'}
        if code not in codes:
            code = 400

        headers = [f'HTTP/1.1 {code} {codes[code]}', '', '',]
        writer.write(('\r\n'.join(headers)).encode('UTF-8'))
        await writer.drain()
        writer.close()
        log(f'Request {msg} {code}: {error}', True)

    async def send(self) -> None:
        headers = ['HTTP/1.1 200 OK']

        peer = self.request['headers']['x-real-ip']
        host = self.request['headers']['x-host']
        ua = self.request['headers']['x-user-agent']
        msg = f'Request {peer} ({ua}) > {host} "{unquote(self.start_line)}" 200'

        if not self.handle_sse:
            headers = ('\r\n'.join(headers + self.headers)).encode('UTF-8')
            await self.write(headers + b'\r\n\r\n' + self.body)
            log(msg)
        else:
            headers += [
                'Content-Type: text/event-stream',
                'Cache-Control: no-cache',
                'X-Accel-Buffering: no']  # prevent Nginx from buffering the SSE stream

            headers = ('\r\n'.join(headers)).encode('UTF-8')
            await self.write(headers + b'\r\n\r\n')
            log(msg)

            res = await self.handle_sse()

            log(f'SSE closed: {res}')

        self._writer.close()

    async def write(self, content: bytes) -> None:
        self._writer.write(content)
        await self._writer.drain()

    def close(self) -> None:
        self._writer.close()

    @staticmethod
    async def read_file(filename: str) -> bytes:
        p = await asyncio.create_subprocess_shell(
            f'cat {filename}',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        stdout, _stderr = await p.communicate()
        return stdout
