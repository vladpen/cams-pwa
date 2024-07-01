import re
import json
from os import path as os_path
from typing import Dict
from datetime import datetime

import const
from _config import Config
from response import Response
from videos import Videos
from images import Images
from share import Share


class Render:
    def __init__(self, title: str, source_hash: str, auth_info: str):
        self.title = title
        self.hash = source_hash
        self.auth_info = auth_info
        self.cams = {}
        self.bell_hidden = 'hidden'

    async def get_html(self, page: str) -> str:
        """ Factory method to read and render a given template (page) in the global layout (/client/layout.html).
            The template should be named "{page}.html" and the rendering method should be named "_render_{page}".
            Returns the finished HTML layout.
        """
        method_name = f'_render_{page}'

        if not re.match(r'^[a-z]+$', page) or method_name not in dir(self):
            raise RuntimeError('Render: invalid page')

        self._prepare_context()  # set self.cams & self.bell_hidden

        layout = (
            await Response.read_file(f'{os_path.dirname(os_path.realpath(__file__))}/../client/layout.html')
        ).decode()
        template = (
            await Response.read_file(f'{os_path.dirname(os_path.realpath(__file__))}/../client/{page}.html')
        ).decode()
        html = layout.replace('{content}', template)

        render = getattr(self, method_name)
        context = render()

        context.update({
            'bell_hidden': self.bell_hidden,
            'is_system_busy': Share.is_system_busy()
        })
        for key, val in context.items():
            html = html.replace('{' + key + '}', val)

        return html

    def _prepare_context(self):
        for cam_hash, cam in Config.cameras.items():
            if self.auth_info != Config.master_cam_hash and self.auth_info != cam_hash:
                continue
            self.cams[cam_hash] = {
                'name': cam['name'],
                'codecs': cam['codecs'],
                'sensitivity': cam['sensitivity'],
                'events': cam['events'],
                'bell': self._get_bell_time(cam_hash)}
            if cam['sensitivity'] or cam['events']:
                self.bell_hidden = ''

    @staticmethod
    def _get_bell_time(cam_hash) -> str:
        if cam_hash not in Share.cam_motions:
            return ''
        last_bell_datetime = datetime.strptime(Share.cam_motions[cam_hash], const.DT_WEB_FORMAT)
        if (datetime.now() - last_bell_datetime).total_seconds() > 43200:  # not older than 12 hours
            return ''
        return last_bell_datetime.strftime('%H:%M')

    def _render_home(self) -> Dict[str, str]:
        groups = {}
        if hasattr(Config, 'groups'):
            for k, v in Config.groups.items():
                if self.auth_info == Config.master_cam_hash:
                    groups[k] = {'name': v['name']}
        return {
            'title': self.title,
            'cams': json.dumps(self.cams),
            'groups': json.dumps(groups)
        }

    def _render_cam(self) -> Dict[str, str]:
        if self.hash not in self.cams:
            raise RuntimeError('Render: invalid cam hash')

        events_hidden = 'hidden' if not self.cams[self.hash]['events'] else ''
        return {
            'title': self.cams[self.hash]['name'],
            'days': json.dumps(Videos(self.hash).get_days()),
            'cam_info': json.dumps(self.cams[self.hash]),
            'events_hidden': events_hidden,
        }

    def _render_group(self) -> Dict[str, str]:
        if not hasattr(Config, 'groups') or self.hash not in Config.groups:
            raise RuntimeError('Render: invalid group hash')
        cams = {}
        for cam_hash in Config.groups[self.hash]['cams']:
            if cam_hash in self.cams:
                cams[cam_hash] = self.cams[cam_hash]

        return {
            'title': Config.groups[self.hash]['name'],
            'cams': json.dumps(cams)
        }

    def _render_events(self) -> Dict[str, str]:
        if self.hash not in self.cams:
            raise RuntimeError('Render: invalid events hash')
        return {
            'title': self.cams[self.hash]['name'],
            'cam_info': json.dumps(self.cams[self.hash]),
            'chart_data': json.dumps(Images(self.hash).get_chart_data())
        }

    def _render_auth(self) -> Dict[str, str]:
        return {'title': self.title}
