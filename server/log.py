"""
Log to system journal.
Usage examples (for "cams-pwa" unit):
    Show log from today:
        journalctl -u cams-pwa --since today
    Live log monitoring:
        journalctl -u cams-pwa -f
"""


def log(message, is_error=False) -> None:
    prefix = '' if not is_error else '~ ERROR: '
    print(f'{prefix}{message.strip()}', flush=True)
