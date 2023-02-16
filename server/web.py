import ssl
import re
import json
import mimetypes
from os import path as os_path
from http.server import BaseHTTPRequestHandler, HTTPServer
from http.cookies import SimpleCookie
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs
from _config import Config
from auth import Auth
from files import Files
from log import Log


class Server:
    @staticmethod
    def run() -> None:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(Config.ssl_certificate, Config.ssl_private_key)

        web_server = ThreadingServer((Config.webServerHost, Config.webServerPort), Handler)
        web_server.socket = context.wrap_socket(web_server.socket, server_side=True)

        Log.print(f'Serving HTTP on https://{Config.webServerHost}:{Config.webServerPort}/ ...')

        try:
            web_server.serve_forever()
        except KeyboardInterrupt:
            pass

        web_server.server_close()
        Log.print('Server stopped.')


class ThreadingServer(ThreadingMixIn, HTTPServer):
    pass


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        """ Possible GET params: ?<page|live|next|range>=<val>[&dt=<dt>]&hash=<hash>[&md=<val>]
        """
        self._init()

        self._query = parse_qs(urlparse(self.path).query)
        if not self._query:
            if not re.search(r'^/([a-z]+/)*[a-z\d.]*$', self.path):
                return self._send_error()

            template = self.path if self.path != '/' else '/index.html'

            if not self.auth.info() and template.endswith('.html'):
                return self._send_template('/auth.html')

            return self._send_template(template)

        if 'hash' not in self._query:
            return self._send_error()

        self.hash = self._query['hash'][0]
        if not self.auth.info() or (self.auth.info() != Config.master_cam_hash and self.auth.info() != self.hash):
            return self._send_error(403)
        if self.hash not in Config.cameras and (not hasattr(Config, 'groups') or self.hash not in Config.groups):
            return self._send_error()

        if 'page' in self._query:
            tpl = self._query["page"][0]
            if tpl not in ['cam', 'group']:
                return self._send_error()
            return self._send_template(f'/{tpl}.html')

        self.files = Files(self.hash, self._query)
        self.cam_path = Config.cameras[self.hash]['path']

        if 'live' in self._query:
            return self._send_video(*self.files.get_live())
        elif 'range' in self._query:
            return self._send_video(*self.files.get_by_range())
        elif 'next' in self._query:
            # if 'dt' not in query:
            #    return self._send_video(*self.files.get_live(query))
            return self._send_video(*self.files.get_next())

        self._send_error()

    def do_POST(self) -> None:
        self._init()

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        auth_info = self.auth.login(post_data)
        if not auth_info:
            Log.print('Web: ERROR: invalid auth')
            return self._send_error(403)

        self.send_response(200)
        self.send_header('Set-Cookie', f'auth={self.auth.encrypt(auth_info)}; Secure; Path=/; Max-Age=3456000')
        self.end_headers()
        Log.print('Web: logged in')

    def version_string(self) -> str:
        """Overrides parent method."""
        return 'Cams PWA'

    def _init(self) -> None:
        self.cookie = SimpleCookie()
        raw_cookies = self.headers.get('Cookie')
        if raw_cookies:
            self.cookie.load(raw_cookies)

        self.auth = Auth(self.cookie['auth'].value if 'auth' in self.cookie else None)

    def _send_template(self, template: str) -> None:
        path = '/layout.html' if template.endswith('.html') else template
        try:
            with open(f'{os_path.dirname(os_path.realpath(__file__))}/../client{path}', 'rb') as file:
                mime_type, _enc = mimetypes.MimeTypes().guess_type(template)
                self.send_response(200)
                self.send_header('Content-Type', mime_type)
                self.send_header(
                    'Set-Cookie', f'auth={self.auth.encrypt(self.auth.info())}; Secure; Path=/; Max-Age=3456000')
                self.end_headers()
                self.wfile.write(self._replace_template(template, file.read()))
        except Exception as e:
            Log.print(f'Web: ERROR: template not found: "{template}" ({repr(e)})')
            self._send_error()

    def _replace_template(self, template: str, content: bytes) -> bytes:
        if not template.endswith('.html'):
            return content

        content = content.replace('{content}'.encode('UTF-8'), self._get_content(template))
        title = Config.title

        if template == '/index.html':
            cams_list = {}
            groups_list = {}
            for k, v in Config.cameras.items():
                if self.auth.info() == Config.master_cam_hash or self.auth.info() == k:
                    cams_list[k] = {'name': v['name']}
            if hasattr(Config, 'groups'):
                for k, v in Config.groups.items():
                    if self.auth.info() == Config.master_cam_hash:
                        groups_list[k] = {'name': v['name']}

            content = content.replace(
                '{cams}'.encode('UTF-8'), json.dumps(cams_list).encode('UTF-8')
            ).replace(
                '{groups}'.encode('UTF-8'), json.dumps(groups_list).encode('UTF-8')
            )
        elif template == '/cam.html':
            self.files = Files(self.hash, self.cookie)
            title = Config.cameras[self.hash]['name']
            content = content.replace(
                '{days}'.encode('UTF-8'), json.dumps(self.files.get_days()).encode('UTF-8'))
        elif template == '/group.html':
            if hasattr(Config, 'groups'):
                title = Config.groups[self.hash]['name']
            content = content.replace(
                '{cams}'.encode('UTF-8'), json.dumps(Config.groups[self.hash]['cams']).encode('UTF-8')
            )
        return content.replace('{title}'.encode('UTF-8'), title.encode('UTF-8'))

    @staticmethod
    def _get_content(template: str) -> bytes:
        try:
            with open(f'{os_path.dirname(os_path.realpath(__file__))}/../client{template}', 'rb') as file:
                return file.read()
        except Exception as e:
            Log.print(f'Web: ERROR: content not found: "{template}" ({repr(e)})')

    def _send_video(self, file_path: str, file_size: int) -> None:
        query_date_time = self._query['dt'][0] if 'dt' in self._query else ''
        file_date_time = self.files.get_datetime_by_path(file_path)

        self.send_response(200)
        if file_path and file_size and query_date_time != file_date_time:
            self.send_header('Content-Type', 'video/mp4')
            self.send_header('Content-Length', str(file_size))
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.send_header('X-Datetime', file_date_time)
            self.send_header('X-Range', self.files.get_range_by_path(file_path))
            self.end_headers()
            with open(file_path, 'rb') as video_file:
                self.wfile.write(video_file.read())
        else:
            self.end_headers()

    def _send_error(self, code: int = 404) -> None:
        self.send_response(code)
        self.end_headers()
