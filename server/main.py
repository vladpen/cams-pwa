from concurrent.futures import ThreadPoolExecutor

from _config import Config
from request import listen_http
from storage import Storage
from events import Events


def main() -> None:
    tasks = []

    if Config.web_enabled:
        # Start one listener for all web clients
        tasks.append(listen_http)

    for camera_hash in Config.cameras.keys():
        if Config.storage_enabled:
            # Start streams saving
            s = Storage(camera_hash)
            s.run()
            tasks.append(s.watchdog)

        if Config.events_enabled and Config().cameras[camera_hash]['events']:
            # Events checking & rotation
            e = Events(camera_hash)
            tasks.append(e.check)

    with ThreadPoolExecutor(len(tasks)) as executor:
        for task in tasks:
            executor.submit(task)


if __name__ == '__main__':
    main()
