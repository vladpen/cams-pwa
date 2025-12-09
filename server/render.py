import re
import gettext
from os import path as os_path

from _config import Config
from response import Response
from share import Share


class Render:
    def __init__(self, language: str):
        self._language = language

        self._i18n = gettext.translation(
            'base',
            f'{os_path.dirname(os_path.realpath(__file__))}/../locale',
            fallback=True,
            languages=[self._language])

        self.app_title = self._i18n.gettext('Cams')

    async def get_html(self, page: str, uri: str, network: str) -> str:
        """ Factory method to read and render a given template (page) in the global layout (/client/layout.html).
            The template should be named "{page}.html" and the rendering method should be named "_render_{page}".
            Returns the finished HTML layout.
        """
        method_name = f'_render_{page}'

        if not re.match(r'^[a-z_]+$', page):
            raise RuntimeError('Render: invalid page', 404)

        layout = await _read_file('layout.html')
        template = await _read_file(f'{page}.html')
        template = await self._replace_functions(template)

        html = layout.replace('{content}', template).replace('{uri}', uri)
        context = {
            'title': self.app_title, 'lang': self._language, 'start_dt': Share.start_datetime, 'network': network}

        # TODO: cache compiled HTML

        if method_name in dir(self):
            render = getattr(self, method_name)
            context.update(render())

        for key, val in context.items():
            html = html.replace('{' + key + '}', val)

        return html

    @staticmethod
    def _render_cam() -> dict[str, str]:
        return {
            'days': str(Config.storage_period_days)
        }

    def _render_cam_edit(self) -> dict[str, str]:
        return {
            'title': self._i18n.gettext('Camera')
        }

    def _render_group_edit(self) -> dict[str, str]:
        return {
            'title': self._i18n.gettext('Group')
        }

    async def _replace_functions(self, html: str) -> str:
        match = re.findall(r'{([a-z_]+)\((.+?)\)}', html)
        if not match:
            return html  # Nothing to render

        for pair in match:
            function = pair[0]
            args = pair[1]
            if function == 'include':
                html = await self._replace_include(html, args)
            elif function == '_':
                html = html.replace('{_(' + args + ')}', self._i18n.gettext(args))

        return html

    @staticmethod
    async def _replace_include(html: str, file_name: str) -> str:
        if not re.search(r'^[a-z_\-]+\.[a-z]+$', file_name):
            raise RuntimeError('Render: invalid included template')
        return html.replace('{include(' + file_name + ')}', (await _read_file(file_name)))


async def _read_file(file_name: str):
    return (
        await Response.read_file(f'{os_path.dirname(os_path.realpath(__file__))}/../client/{file_name}')
    ).decode()
