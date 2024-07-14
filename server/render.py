import re
import json
import gettext
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
    def __init__(self, title: str, source_hash: str, auth_info: str, language: str):
        self.title = title
        self.hash = source_hash
        self.auth_info = auth_info
        self.language = language
        self.cams = {}
        self.bell_hidden = 'hidden'

    async def get_html(self, page: str) -> str:
        """ Factory method to read and render a given template (page) in the global layout (/client/layout.html).
            The template should be named "{page}.html" and the rendering method should be named "_render_{page}".
            Returns the finished HTML layout.
        """
        method_name = f'_render_{page}'

        if not re.match(r'^[a-z]+$', page) or method_name not in dir(self):
            raise RuntimeError('Render: page not found', 404)

        self._prepare_context()  # set self.cams & self.bell_hidden

        layout = await _read_file('layout.html')
        template = await _read_file(f'{page}.html')
        template = await _replace_functions(template, self.language)

        html = layout.replace('{content}', template)

        # TODO: cache compiled HTML

        render = getattr(self, method_name)
        context = render()

        context.update({
            'lang': self.language,
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
                'bell': _get_bell_time(cam_hash)}
            if cam['sensitivity'] or cam['events']:
                self.bell_hidden = ''

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


async def _read_file(file_name: str):
    return (
        await Response.read_file(f'{os_path.dirname(os_path.realpath(__file__))}/../client/{file_name}')
    ).decode()


async def _replace_functions(html: str, language: str) -> str:
    match = re.findall(r'{([a-z_]+)\((.+?)\)}', html)
    if not match:
        return html  # Nothing to render

    i18n = gettext.translation(
        'base',
        f'{os_path.dirname(os_path.realpath(__file__))}/../locale',
        fallback=True,
        languages=[language])

    for pair in match:
        function = pair[0]
        args = pair[1]
        if function == 'include':
            html = await _replace_include(html, args)
        elif function == '_':
            html = html.replace('{_(' + args + ')}', i18n.gettext(args))

    return html


async def _replace_include(html: str, file_name: str) -> str:
    if not re.search(r'^[a-z\-]+\.[a-z]+$', file_name):
        raise RuntimeError('Render: invalid included template')
    return html.replace('{include(' + file_name + ')}', (await _read_file(file_name)))


def _get_bell_time(cam_hash) -> str:
    if cam_hash not in Share.cam_motions:
        return ''
    last_bell_datetime = datetime.strptime(Share.cam_motions[cam_hash], const.DT_WEB_FORMAT)
    if (datetime.now() - last_bell_datetime).total_seconds() > 43200:  # not older than 12 hours
        return ''
    return last_bell_datetime.strftime('%H:%M')
