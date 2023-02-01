import asyncio
from threading import Thread
from _config import Config
from storage import Storage
import web


async def main() -> None:
    tasks = []

    if Config.web_enabled:
        # Start one listener for all web clients
        thread = Thread(target=web.Server.run)
        thread.start()

    if Config.storage_enabled:
        # Start streams saving
        for camera_hash in Config.cameras.keys():
            s = Storage(camera_hash)
            tasks.append(asyncio.create_task(s.run()))
            tasks.append(asyncio.create_task(s.watchdog()))

    for t in tasks:
        await t

if __name__ == '__main__':
    asyncio.run(main())
