import asyncio
import re
import json
import mimetypes
from os import path as os_path
from datetime import datetime

import const
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

    async def do_get(self) -> None:
        """ Router. Possible GET params: ?<page|video|image|chart|bell>=<val>[...]
        """
        if 'webmanifest' in self.request['uri']:  # check first (query may not be empty)
            return await self._send_webmanifest()

        if not self.request['query'] and self.request['uri'] != '/':
            return await self._send_static()

        if 'page' in self.request['query'] or (
                not self.request['query'] and self.request['uri'] == '/'):  # home page
            return await self._send_page()

        if 'video' in self.request['query']:
            return await self._send_segment()

        if 'image' in self.request['query']:
            return await self._send_image()

        if 'chart' in self.request['query']:
            return await self._send_chart()

        if 'bell' in self.request['query']:
            self.handle_sse = self._handle_sse  # callback
            return None

        raise RuntimeError('Web: invalid route')

    async def do_post(self) -> None:
        return

    def _get_key(self) -> str:
        return self.request['query']['key'][0] if self.request['query'] and 'key' in self.request['query'] else ''

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

    async def _send_static(self) -> None:
        static_file = re.sub(r'\?.*$', '', self.request['uri'])

        if not re.search(r'^/([a-z]+/)*[a-z\d._\-]+$', static_file):
            raise RuntimeError('Web: invalid static URI', 404)

        await self._set_static(static_file)

    async def _send_webmanifest(self) -> None:
        static_file = '/app.webmanifest'
        await self._set_static(static_file)

        render = Render(self.request['headers']['x-language'])

        self.body = self.body.replace(
            b'{title}', render.app_title.encode('UTF-8')).replace(
            b'{network}', self._get_network_type().encode('UTF-8')).replace(
            b'{uri}', self.request['uri'].replace(static_file, '').encode('UTF-8'))

    async def _set_static(self, static_file: str) -> None:
        try:
            mime_type, _enc = mimetypes.MimeTypes().guess_type(static_file)
            self.headers = [
                f'Content-Type: {mime_type}',
                'Cache-Control: max-age=2592000'  # 30 days
            ]
            self.body = await Response.read_file(
                f'{os_path.dirname(os_path.realpath(__file__))}/../client{static_file}')
        except Exception:
            raise RuntimeError('Web: invalid static file', 404)

    async def _send_page(self) -> None:
        self.headers = ['Content-Type: text/html; charset=utf-8']

        page = self.request['query']['page'][0] if self.request['query'] else 'home'

        render = Render(self.request['headers']['x-language'])
        self.body = (await render.get_html(page, self.request['uri'], self._get_network_type())).encode('UTF-8')

    async def _send_segment(self) -> None:
        key = self._get_key()
        if not key or key not in Config.cameras:
            raise RuntimeError('Web: invalid segment key')
        videos = Videos(key)
        file_path, file_size = await videos.get(self.request['query'])
        query_date_time = self.request['query']['dt'][0] if 'dt' in self.request['query'] else ''
        file_date_time = videos.get_datetime_by_path(file_path)
        if not file_path or not file_size or (query_date_time and query_date_time == file_date_time):
            return
        self.headers = [
            'Content-Type: video/mp4',
            f'Content-Length: {str(file_size)}',
            'Cache-Control: no-cache',
            f'X-Datetime: {file_date_time}',
            f'X-Range: {videos.get_range_by_path(file_path)}'
        ]
        if not query_date_time:  # first request (onSourceOpen)
            self.headers += [
                f'X-Codecs: {Config.cameras[key]['codecs']}',
                f'X-Events: {int(Config.cameras[key]['events'])}']
        self.body = await Response.read_file(file_path)

    async def _send_image(self) -> None:
        key = self._get_key()
        if not key or key not in Config.cameras:
            raise RuntimeError('Web: invalid image key')
        images = Images(key)

        file_path, file_size, position, rng = images.get(self.request['query'])
        if not file_size:
            return

        mime_type, _enc = mimetypes.MimeTypes().guess_type(file_path)
        self.headers = [
            f'Content-Type: {mime_type}',
            f'Content-Length: {str(file_size)}',
            'Cache-Control: no-cache',
            f'X-Range: {str(rng)}',
            f'X-Position: {position}',
        ]
        self.body = await Response.read_file(file_path)

    async def _send_chart(self) -> None:
        key = self.request['query']['chart'][0]
        if not key or key not in Config.cameras:
            raise RuntimeError('Web: invalid chart key')

        chart_data = Images(key).get_chart_data()

        self.headers = ['Content-Type: application/json']
        self.body = json.dumps(chart_data).encode('UTF-8')

    async def _handle_sse(self) -> str:
        uid = self.request['query']['uid'][0]
        keys = self.request['query']['keys'][0].split(',')
        keep_connection = int(self.request['query']['bell'][0])

        if uid in Share.sse_clients:  # close previous connection & request for _loop_sse closing
            Share.sse_clients[uid].close_sse_connection = True
            Share.sse_clients[uid].close()
            log(f'SSE renew connection: {uid} {self._get_id(Share.sse_clients[uid])} -> {self._get_id(self)}')

        cams = await self._init_sse(keys)

        if not keep_connection or not cams:
            self.close()
            return f'{uid} {self._get_id(self)} init done' if not keep_connection else f'{uid} no cams for monitoring'

        Share.sse_clients[uid] = self
        log(f'SSE new loop: {uid} {self._get_id(self)}')

        return await self._loop_sse(uid, cams)

    async def _init_sse(self, keys: list) -> dict:
        cams = {}
        for key in keys:
            if key not in Config.cameras:
                continue
            if Config.cameras[key]['events'] or Config.cameras[key]['sensitivity'] > 1:
                cams[key] = {
                    'time': self._get_bell_time(key),
                    'events': int(Config.cameras[key]['events'])}

        data = {'action': 'init', 'cams': cams}
        body = (
            'event: message\r\n'
            'data: ' + json.dumps(data) + '\r\n\r\n').encode('UTF-8')

        await self.write(body)

        return cams

    async def _loop_sse(self, uid: str, cams: dict) -> str:
        cnt = 0
        last_times = {}

        while not self.close_sse_connection:
            try:
                cnt = cnt + 1 if cnt < 10 else 1

                if cnt % 2 == 0:  # check new motions every 2 secs (even cnt)
                    bell_cams = {}
                    for key in cams:
                        if key not in Share.cam_motions:
                            continue
                        if key not in last_times:
                            last_times[key] = Share.cam_motions[key]

                        if Share.cam_motions[key] > last_times[key]:
                            last_times[key] = Share.cam_motions[key]
                            bell_cams[key] = self._get_bell_time(key)

                    if bell_cams:
                        data = {'action': 'bell', 'cams': bell_cams}
                        body = (
                            'event: message\r\n'
                            'data: ' + json.dumps(data) + '\r\n\r\n').encode('UTF-8')

                        await self.write(b'\r\n\r\n' + body)
                        log(f'SSE bell: {uid} {list(bell_cams.keys())}')

                if cnt == 10:  # ping client every 10 sesc & raise exception if connection lost
                    await self.write(b'.')

                await asyncio.sleep(1)

            except Exception as e:
                self.close()
                del Share.sse_clients[uid]
                return f'{uid} {self._get_id(self)} error: {e}'

        del Share.sse_clients[uid]
        return f'{uid} {self._get_id(self)} close_sse_connection={self.close_sse_connection}'

    @staticmethod
    def _get_id(obj: object) -> str:
        return str(id(obj))[-4:]

    @staticmethod
    def _get_bell_time(key) -> str:
        if key not in Share.cam_motions:
            return ''
        last_bell_datetime = datetime.strptime(Share.cam_motions[key], const.DT_WEB_FORMAT)
        if (datetime.now() - last_bell_datetime).total_seconds() > 43200:  # not older than 12 hours
            return ''
        return last_bell_datetime.strftime(const.DT_WEB_FORMAT)
