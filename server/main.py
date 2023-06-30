import asyncio
from threading import Thread
from _config import Config
from storage import Storage
from events import Events
import web


async def main() -> None:
    tasks = []

    if Config.web_enabled:
        # Start one listener for all web clients
        thread = Thread(target=web.Server.run)
        thread.start()

    for camera_hash in Config.cameras.keys():
        if Config.storage_enabled:
            # Start streams saving
            await asyncio.sleep(0.1)
            s = Storage(camera_hash)
            tasks.append(asyncio.create_task(s.run()))
            await asyncio.sleep(0.1)
            tasks.append(asyncio.create_task(s.watchdog()))

        if Config.events_enabled and Config().cameras[camera_hash]['events']:
            # Events checking & rotation
            await asyncio.sleep(0.01)
            e = Events(camera_hash)
            tasks.append(asyncio.create_task(e.run()))

    for t in tasks:
        await t

if __name__ == '__main__':
    asyncio.run(main())
