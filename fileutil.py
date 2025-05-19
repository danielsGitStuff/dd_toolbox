from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Optional, List


class FileUtil:
    @staticmethod
    def extract_name(f: Path) -> str:
        name: str = f.name
        if '.' not in name:
            return name
        idx: int = name.rfind('.')
        return name[:idx]

    @staticmethod
    def is_directory() -> Callable[[Path], bool]:
        def f(path: Path) -> bool:
            return path.is_dir()

        return lambda p: f(p)

    @staticmethod
    def condition_file_extension(extension: str) -> Callable[[Path], bool]:
        extension = extension.lower()

        def f(path: Path) -> bool:
            name: str = path.name.lower()
            if "." not in name:
                return False
            idx: int = name.rfind(".")
            actual_extension: str = name[idx + 1:]
            return extension == actual_extension

        return lambda p: f(p)

    def __init__(self, directory: Path | str, recursive: bool = False):
        self.recursive: bool = recursive
        self.directory: Path = directory if isinstance(directory, Path) else Path(directory)
        self.conditions: List[Callable[[Path], bool]] = []
        self.collected_files: Optional[List[Path]] = None

    def with_condition(self, condition: Callable[[Path], bool]) -> FileUtil:
        self.conditions.append(condition)
        return self

    def __recurse(self, directory: Path):
        paths: List[Path] = [Path(directory, name) for name in os.listdir(directory)]
        files: List[Path] = [p for p in paths if p.is_file()]
        subdirectories: List[Path] = [p for p in paths if p.is_dir()]
        if self.recursive:
            for subdir in subdirectories:
                self.__recurse(directory=subdir)
        for f in files:
            ok: bool = len(self.conditions) == sum([int(c(f)) for c in self.conditions])
            if ok:
                self.collected_files.append(f)

    def find(self) -> List[Path]:
        if self.collected_files is not None:
            return self.collected_files
        self.collected_files = []
        self.__recurse(directory=self.directory)
        return self.collected_files
