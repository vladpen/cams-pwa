from typing import Tuple, List, Any, Dict

import const
from _config import Config
from execute import get_execute


class Images:
    def __init__(self, camera_hash):
        self._hash = camera_hash
        self._cam_config = Config.cameras[self._hash]
        self._events_path = f"{Config.events_path}/{self._cam_config['folder']}"
        self._root_folders = []

    def get_chart_data(self) -> List[int]:
        cnt = []
        for folder in self._get_root_folders():
            wd = f"{self._events_path}/{folder}"
            wd_count = get_execute(f'ls {wd} | wc -l')
            cnt.append(int(wd_count) if wd_count else 0)
        return cnt

    def get(self, args: Dict[str, List[Any]]) -> Tuple[str, int, str, int]:
        if args['image'][0] == 'next':
            step = int(args['step'][0]) if 'step' in args else 0
            position = args['pos'][0].split('.') if 'pos' in args else [-1, -1]
            return self._get_next(step, position)

        elif args['image'][0] == 'range':
            rng = int(args['range'][0]) if 'range' in args else const.MAX_RANGE
            position = args['pos'][0].split('.') if 'pos' in args else [-1, -1]
            return self._get_by_range(rng, position)

        return self._get_last()  # never happen

    def _get_next(self, step: int, position: List[int]) -> Tuple[str, int, str, int]:
        if step == 0:
            return self._get_last()

        folder_idx = int(position[0])
        file_idx = int(position[1])

        folders = self._get_root_folders()
        if folder_idx < 0:
            folder_idx = len(folders) - 1

        files = self._get_files(folders[folder_idx])
        if file_idx < 0:
            file_idx = len(files) - 1

        # try to get file from current folder
        if (step < 0 and abs(step) <= file_idx) or (0 < step <= len(files) - file_idx - 1):
            file_idx += step
            return self._response(folders, files, folder_idx, file_idx)

        if step < 0 and folder_idx <= 0:
            return self._get_first()
        elif step > 0 and folder_idx >= len(folders) - 1:
            return self._get_last()

        if step < 0 < folder_idx:
            folder_idx -= 1
            file_idx = -1
            step = -1
        elif folder_idx < len(folders) - 1:
            folder_idx += 1
            file_idx = 0
            step = 1

        return self._get_next(step, [folder_idx, file_idx])

    def _response(self, folders, files, folder_idx, file_idx) -> Tuple[str, int, str, int]:
        if not files:
            return '', 0, '', 0
        range_folder = const.MAX_RANGE / len(folders)
        folder_range = range_folder * folder_idx

        range_file = range_folder / len(files)
        file_range = range_file * file_idx

        rng = round(folder_range + file_range)
        if folder_idx >= len(folders) - 1 and file_idx >= len(files) - 1:
            rng = const.MAX_RANGE + 1
        elif folder_idx <= 0 and file_idx <= 0:
            rng = -1

        f = files[file_idx].split()
        return f'{self._events_path}/{folders[folder_idx]}/{f[1]}', int(f[0]), f'{folder_idx}.{file_idx}', rng

    def _get_by_range(self, rng: int, position: List[int]) -> Tuple[str, int, str, int]:
        rng = min(max(rng, 0), const.MAX_RANGE - 1)

        folders = self._get_root_folders()
        range_folder = int(const.MAX_RANGE / len(folders))
        folder_idx = int(rng / range_folder)

        files = self._get_files(folders[folder_idx])
        file_idx = int((rng / range_folder - folder_idx) * len(files))

        if position[0] == folder_idx and position[1] == file_idx:  # save some traffic
            return '', 0, '', 0

        return self._response(folders, files, folder_idx, file_idx)

    def _get_last(self) -> Tuple[str, int, str, int]:
        return self._get_file(-1, const.MAX_RANGE + 1)

    def _get_first(self) -> Tuple[str, int, str, int]:
        return self._get_file(0, -1)

    def _get_file(self, pos: int, rng: int) -> Tuple[str, int, str, int]:
        folders = self._get_root_folders()
        if not folders:
            return '', 0, '', rng
        folder = folders[pos]
        files = self._get_files(folder)
        if not files and len(folders) > 1:  # fallback case
            folder = folders[-2]
            files = self._get_files(folder)

        f = files[pos].split()
        path = f'{self._events_path}/{folder}/{f[1]}'
        size = int(f[0])
        return path, size, '', rng

    def _get_root_folders(self) -> List[str]:
        if self._root_folders:
            return self._root_folders
        self._root_folders = get_execute(f'ls {self._events_path}').splitlines()
        return self._root_folders

    def _get_files(self, folder: str) -> List[str]:
        wd = f"{self._events_path}/{folder}"
        return get_execute(f'ls -l {wd} | awk ' + "'{print $5,$9}'").splitlines()
