import asyncio
import re
from ssl import SSLContext, PROTOCOL_TLS_SERVER
from urllib.parse import urlparse, parse_qs
from typing import Dict

from _config import Config
from web import Web
from log import Log


def listen_http() -> None:
    Log.write(f'* Serving on https://{Config.web_server_host}:{Config.web_server_port}')
    asyncio.run(_main())


async def _main():
    ctx = SSLContext(PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(Config.ssl_certificate, Config.ssl_private_key)
    server = await asyncio.start_server(_handle, Config.web_server_host, Config.web_server_port, ssl=ctx)
    async with server:
        await server.serve_forever()


async def _handle(reader: asyncio.streams.StreamReader, writer: asyncio.streams.StreamWriter) -> None:
    raw_request = await _get_request(reader)
    start_line = raw_request.split('\n', 1)[0].strip()
    peer_name = writer.get_extra_info('peername')
    host = ''

    try:
        request = await _parse_request(raw_request)
        host = request['headers']['host'].split(':', 1)[0]
        peer_name = peer_name[0]

        web = Web(writer, request)
        if request['method'] == 'POST':
            await web.do_post()
        else:
            await web.do_get()

        await web.send(web.headers, web.body, start_line)

    except Exception as e:
        error, code = e.args[0], e.args[1] if len(e.args) > 1 and isinstance(e.args[1], int) else 400
        msg = f'{peer_name} > {host} "{start_line}"'
        try:
            await Web.send_error(writer, code, msg, error)
        except Exception as ex:
            Log.write(f'Request {msg} cancelled ({repr(ex)})')


async def _get_request(reader: asyncio.streams.StreamReader) -> str:
    request = ''
    try:
        request = (await reader.read(1000000000)).decode().strip()
    except Exception as e:
        Log.write(f'Request ERROR: {repr(e)}')
    return request


async def _parse_request(raw_request: str) -> Dict:
    if not raw_request:
        raise Exception('Request: empty request')

    request_parts = re.split(r'(?:\r?\n){2,}', raw_request, 2)
    header_lines = request_parts[0].splitlines()
    start_line = header_lines[0].split()
    if len(start_line) < 3:
        raise Exception('Request: invalid start line')

    request = {'method': start_line[0], 'uri': start_line[1], 'version': start_line[2]}
    request['query'] = parse_qs(urlparse(request['uri']).query)  # GET params (dict)

    if not request['version'].startswith('HTTP/'):
        raise Exception('Request: invalid version')

    if request['method'] not in ('GET', 'POST'):
        raise Exception('Request: method not allowed')

    request['headers'] = {}
    for field in header_lines[1:]:
        if not field:
            continue
        key, value = field.split(':', 1)
        request['headers'][key.lower()] = value.strip()

    for field in ['host', 'accept', 'user-agent']:
        if field not in request['headers']:
            raise Exception(f'Request: empty required field "{field}"')

    request['body'] = request_parts[1] if len(request_parts) > 1 else ''
    return request