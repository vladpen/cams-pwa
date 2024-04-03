import asyncio
import re
import json
import mimetypes
from os import path as os_path
from datetime import datetime

import const
from _config import Config
from response import Response
from videos import Videos
from images import Images
from share import Share
from log import Log


class Web(Response):
    """ Middleware (web request handler)
    """
    def __init__(self, writer, request):
        super().__init__(writer, request)
        self.hash = None

    async def do_get(self) -> None:
        """ Router. Possible GET params: ?<page|video|image|bell>=<val>[...]&hash=<hash>[...]
        """
        if not self.request['query'] and self.request['uri'] != '/':
            return await self._send_static()

        if not self.request['query'] and self.request['uri'] == '/':
            return await self._send_page()  # index page

        if 'bell' in self.request['query']:
            return await self._send_bell()

        if 'hash' not in self.request['query']:
            raise RuntimeError('Web: empty hash')

        self.hash = self.request['query']['hash'][0]
        if self.hash not in Config.cameras and (not hasattr(Config, 'groups') or self.hash not in Config.groups):
            raise RuntimeError('Web: invalid hash')
        if not self.auth.info() or (self.auth.info() != Config.master_cam_hash and self.auth.info() != self.hash):
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
        Log.write(f'Web: logged in: {auth_info}')

    def _get_title(self) -> str:
        host = self.request['headers']['host']
        client_ip = self.request['headers']['x-real-ip']
        gateway_ip = Share.get_default_gateway_ip()

        if client_ip == gateway_ip:  # cloud connection via router, e.g. KeenDNS
            return Config.web_title

        local_network_id = '192.168.'
        if gateway_ip:
            local_network_id = re.sub(r'([.:])\d+$', r'\1', gateway_ip)  # i.g. "192.168.0."

        if client_ip.startswith(local_network_id) or host.startswith('127.0.') or host.startswith('localhost'):
            return Config.title
        return Config.web_title

    async def _send_static(self) -> None:
        static_file = self.request['uri']
        if not re.search(r'^/([a-z]+/)*[a-z\d._]+$', static_file):
            raise RuntimeError('Web: invalid static URI', 404)

        try:
            mime_type, _enc = mimetypes.MimeTypes().guess_type(static_file)
            self.headers = [
                f'Content-Type: {mime_type}',
                'Cache-Control: max-age=604800',
            ]
            self.body = await Response.read_file(
                f'{os_path.dirname(os_path.realpath(__file__))}/../client{static_file}')
            if static_file == '/cams.webmanifest':
                self.body = self.body.replace(b'{title}', self._get_title().encode('UTF-8'))

        except Exception:
            raise RuntimeError('Web: static file not found', 404)

    async def _send_page(self) -> None:
        page = self.request['query']['page'][0] if self.request['query'] else 'index'
        if page not in ['index', 'cam', 'group', 'events']:
            raise RuntimeError('Web: invalid page')

        template = f'/{page}.html'
        if not self.auth.info():
            template = '/auth.html'

        self.body = (
            await Response.read_file(f'{os_path.dirname(os_path.realpath(__file__))}/../client/layout.html')
        ).decode()

        self.headers = ['Content-Type: text/html; charset=utf-8']  # , 'Cache-Control: max-age=604800'
        if self.auth.info():
            self.headers.append(f'Set-Cookie: {self._create_auth_cookie()}')

        self.body = (await self._replace_template(template, self.body)).encode('UTF-8')

    def _create_auth_cookie(self) -> str:
        return (
            f'auth={self.auth.encrypt(self.auth.info())}; '
            'Path=/; Max-Age=3456000; Secure; HttpOnly; SameSite=Lax')

    async def _replace_template(self, template: str, content: str) -> str:
        tpl = (await Response.read_file(f'{os_path.dirname(os_path.realpath(__file__))}/../client{template}')).decode()
        content = content.replace('{content}', tpl)

        title = self._get_title()
        cams_list = {}
        bell_hidden = 'hidden'
        for cam_hash, cam in Config.cameras.items():
            if self.auth.info() == Config.master_cam_hash or self.auth.info() == cam_hash:
                cams_list[cam_hash] = {
                    'name': cam['name'],
                    'codecs': cam['codecs'],
                    'sensitivity': cam['sensitivity'],
                    'events': cam['events'],
                    'bell': self._get_bell_time(cam_hash)}
                if cam['sensitivity'] or cam['events']:
                    bell_hidden = ''

        if template == '/index.html':
            groups_list = {}
            if hasattr(Config, 'groups'):
                for k, v in Config.groups.items():
                    if self.auth.info() == Config.master_cam_hash:
                        groups_list[k] = {'name': v['name']}

            content = content.replace(
                '{cams}', json.dumps(cams_list)
            ).replace(
                '{groups}', json.dumps(groups_list)
            )
        elif template == '/cam.html':
            if self.hash not in cams_list:
                return ''
            videos = Videos(self.hash)
            cam = Config.cameras[self.hash]
            title = cam['name']
            events_hidden = 'hidden' if not cams_list[self.hash]['events'] else ''
            content = content.replace(
                '{days}', json.dumps(videos.get_days())
            ).replace(
                '{cam_info}', json.dumps(cams_list[self.hash])
            ).replace(
                '{events_hidden}', events_hidden
            )
        elif template == '/group.html':
            cams = {}
            for cam_hash in Config.groups[self.hash]['cams']:
                if cam_hash in cams_list:
                    cams[cam_hash] = cams_list[cam_hash]
            if hasattr(Config, 'groups'):
                title = Config.groups[self.hash]['name']
            content = content.replace(
                '{cams}', json.dumps(cams)
            )
        elif template == '/events.html':
            if self.hash not in cams_list:
                return ''
            images = Images(self.hash)
            cam = Config.cameras[self.hash]
            title = cam['name']
            content = content.replace(
                '{cam_info}', json.dumps(cams_list[self.hash])
            ).replace(
                '{chart_data}', json.dumps(images.get_chart_data())
            )
        content = content.replace('{bell_hidden}', bell_hidden).replace('{is_system_busy}', Share.is_system_busy())
        return content.replace('{title}', title)

    @staticmethod
    def _get_bell_time(cam_hash) -> str:
        if cam_hash not in Share.cam_motions:
            return ''
        last_bell_datetime = datetime.strptime(Share.cam_motions[cam_hash], const.DT_WEB_FORMAT)
        if (datetime.now() - last_bell_datetime).total_seconds() > 43200:  # not older than 12 hours
            return ''
        return last_bell_datetime.strftime('%H:%M')

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
            Log.write(f'Web ERROR: invalid bell datetime ({repr(e)})')

        prev_motions = Share.cam_motions.copy()
        cnt = 1
        while True:
            await asyncio.sleep(1)
            res = {}
            for cam_hash, date_time in Share.cam_motions.items():
                if self.auth.info() != Config.master_cam_hash and self.auth.info() != cam_hash:
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
