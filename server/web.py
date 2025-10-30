import asyncio
import re
import json
import mimetypes
from os import path as os_path

from _config import Config
from response import Response
from render import Render
from videos import Videos
from images import Images
from share import Share
from log import log


class Web(Response):
    """ Middleware (web request handler)
    """
    def __init__(self, writer, request):
        super().__init__(writer, request)
        self.hash = None

    async def do_get(self) -> None:
        """ Router. Possible GET params: ?<page|video|image|bell>=<val>[...]&hash=<hash>[...]
        """
        if 'webmanifest' in self.request['uri']:  # check first
            return await self._send_webmanifest()

        if not self.request['query'] and self.request['uri'] == '/':  # home page
            return await self._send_page()

        if not self.request['query'] and self.request['uri'] != '/':
            return await self._send_static()

        if 'bell' in self.request['query']:
            return await self._send_bell()

        if 'hash' not in self.request['query']:
            raise RuntimeError('Web: empty hash')

        self.hash = self.request['query']['hash'][0]
        if self.hash not in Config.cameras and (not hasattr(Config, 'groups') or self.hash not in Config.groups):
            raise RuntimeError('Web: invalid hash')
        if not self.auth.info() or (
            self.auth.info()['hash'] != Config.master_cam_hash and self.auth.info()['hash'] != self.hash
        ):
            raise RuntimeError('Web: invalid auth', 403)

        # Authorized zone

        if 'page' in self.request['query']:
            return await self._send_page()

        if 'video' in self.request['query']:
            return await self._send_segment()

        if 'image' in self.request['query']:
            return await self._send_image()

        raise RuntimeError('Web: invalid route')

    async def do_post(self) -> None:
        """ Auth form handler
        """
        auth_info = self.auth.login(json.loads(self.request['body']))
        if not auth_info:
            raise RuntimeError('Web: invalid post data', 403)

        self.headers = [f'Set-Cookie: {self._create_auth_cookie()}']
        log(f"Web: logged in: {auth_info['nick']} > {auth_info['hash']}")

    def _get_network_type(self) -> str:
        host = self.request['headers']['host']
        client_ip = self.request['headers']['x-real-ip']
        gateway_ip = Share.get_default_gateway_ip()

        if client_ip == gateway_ip:  # cloud connection via router, e.g. KeenDNS
            return 'inet'

        local_network_id = '192.168.'
        if gateway_ip:
            local_network_id = re.sub(r'([.:])\d+$', r'\1', gateway_ip)  # i.g. "192.168.0."

        if client_ip.startswith(local_network_id) or host.startswith('127.0.') or host.startswith('localhost'):
            return 'local'
        return 'inet'

    def _create_auth_cookie(self) -> str:
        return (
            f'auth={self.auth.encrypt(self.auth.info())}; '
            'Path=/; Max-Age=3456000; Secure; HttpOnly; SameSite=Lax')

    async def _send_static(self) -> None:
        static_file = self.request['uri']
        if not re.search(r'^/([a-z]+/)*[a-z\d._\-]+$', self.request['uri']):
            raise RuntimeError('Web: invalid static URI', 404)

        await self._set_static(static_file)

    async def _send_webmanifest(self) -> None:
        static_file = '/app.webmanifest'
        await self._set_static(static_file)

        render = Render('', None, self.request['headers']['x-language'])

        self.body = self.body.replace(
            b'{title}', render.title.encode('UTF-8')).replace(
            b'{network}', self._get_network_type().encode('UTF-8')).replace(
            b'{uri}', self.request['uri'].replace(static_file, '').encode('UTF-8'))

    async def _set_static(self, static_file: str) -> None:
        try:
            mime_type, _enc = mimetypes.MimeTypes().guess_type(static_file)
            self.headers = [
                f'Content-Type: {mime_type}',
                'Cache-Control: max-age=604800',
            ]
            self.body = await Response.read_file(
                f'{os_path.dirname(os_path.realpath(__file__))}/../client{static_file}')
        except Exception:
            raise RuntimeError('Web: invalid static file', 404)

    async def _send_page(self) -> None:
        page = self.request['query']['page'][0] if self.request['query'] else 'home'
        if not self.auth.info():
            page = 'auth'

        self.headers = ['Content-Type: text/html; charset=utf-8']
        if self.auth.info():
            self.headers.append(f'Set-Cookie: {self._create_auth_cookie()}')

        render = Render(self.hash, self.auth.info(), self.request['headers']['x-language'])
        self.body = (await render.get_html(page, self.request['uri'])).encode('UTF-8')

    async def _send_segment(self) -> None:
        videos = Videos(self.hash)
        file_path, file_size = await videos.get(self.request['query'])
        query_date_time = self.request['query']['dt'][0] if 'dt' in self.request['query'] else ''
        file_date_time = videos.get_datetime_by_path(file_path)
        if file_path and file_size and query_date_time != file_date_time:
            self.headers = [
                'Content-Type: video/mp4',
                f'Content-Length: {str(file_size)}',
                'Cache-Control: no-store',
                f'X-Datetime: {file_date_time}',
                f'X-Range: {videos.get_range_by_path(file_path)}',
            ]
            self.body = await Response.read_file(file_path)

    async def _send_image(self) -> None:
        images = Images(self.hash)
        file_path, file_size, position, rng = images.get(self.request['query'])
        if not file_size:
            return
        mime_type, _enc = mimetypes.MimeTypes().guess_type(file_path)
        self.headers = [
            f'Content-Type: {mime_type}',
            f'Content-Length: {str(file_size)}',
            'Cache-Control: no-store',
            f'X-Range: {str(rng)}',
            f'X-Position: {position}',
        ]
        self.body = await Response.read_file(file_path)

    async def _send_bell(self) -> None:
        polling_timeout = 30  # secs

        if not self.auth.info():
            raise RuntimeError('Web: invalid bell auth', 403)

        try:
            last_date_time = self.request['query']['dt'][0]
        except Exception as e:
            last_date_time = ''
            log(f'Web: invalid bell datetime ({repr(e)})', True)

        prev_motions = Share.cam_motions.copy()
        cnt = 1
        while True:
            await asyncio.sleep(1)
            res = {}
            for cam_hash, date_time in Share.cam_motions.items():
                if self.auth.info()['hash'] != Config.master_cam_hash and self.auth.info()['hash'] != cam_hash:
                    continue
                if last_date_time >= date_time:
                    continue
                if cam_hash in prev_motions and prev_motions[cam_hash] >= date_time:
                    continue
                res[cam_hash] = {'dt': date_time, 'name': Config.cameras[cam_hash]['name']}

            if not res and cnt < polling_timeout:
                cnt += 1
                continue

            self.headers = [
                'Content-Type: application/json',
            ]
            self.body = json.dumps(res).encode('UTF-8')
            return
