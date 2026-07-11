from __future__ import annotations

import multiprocessing
import os
import sys
import traceback
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TextIO, Any, Optional, List, Callable


class LokOutType(Enum):
    STD = "std"
    ERR = "err"
    FILE = "file"

    @staticmethod
    def by_text_io(out: TextIO) -> LokOutType:
        if sys.stderr == out:
            return LokOutType.ERR
        else:
            return LokOutType.STD

    def out(self, file_options: FileOptions | None) -> TextIO:
        if LokOutType.STD == self:
            return sys.stdout
        elif LokOutType.ERR == self:
            return sys.stderr
        elif LokOutType.FILE == self:
            assert file_options is not None
            if file_options.append:
                return open(file=file_options.file, mode='a', encoding='utf-8')
            return open(file=file_options.file, mode='w', encoding='utf-8')


class FileOptions:
    def __init__(self, file: Path | str, append: bool = False):
        self.file: Path = file if isinstance(file, Path) else Path(file)
        self.append: bool = append


class Lok:
    @staticmethod
    def from_instance(ins: Any) -> Lok:
        return Lok(name=ins.__class__.__qualname__)

    def __init__(self, name: Optional[str | Callable[[], str]] = None, src: Optional[Any] = None, lok_type: LokOutType = LokOutType.STD):
        self._name_callable: Optional[Callable[[], str]] = None
        self.src: Optional[Any] = src
        self.name: Optional[str] = src.__class__.__qualname__ if name is None else name if isinstance(name, str) else None
        if isinstance(name, Callable):
            self._name_callable = name
        assert self.name is not None or self._name_callable is not None
        self.enabled: bool = True
        self.lok_type: LokOutType = lok_type
        self.stored_lines: List[str] = []
        self.file_options: FileOptions | None = None
        self.children: list[Lok] = []
        self._out: TextIO | None = None
        self._has_active_children: bool = False

    def _name(self) -> str:
        if self.name is not None:
            return self.name
        elif self._name_callable is not None:
            return self._name_callable()
        else:
            raise ValueError("cannot get name")

    def __call__(self, obj: any, file: Optional[TextIO | LokOutType] = None, indent: Optional[int] = None):

        if file is not None:
            if isinstance(file, LokOutType):
                out = file
            else:
                out = LokOutType.by_text_io(file)
        self.__print_any(obj, indent=indent)

    def set_enabled(self, enabled: bool, children_too: bool = True) -> Lok:
        self.enabled = enabled
        if children_too:
            for child in self.children:
                child.set_enabled(enabled=enabled, children_too=children_too)
        self._has_active_children = len(self.children) > 0 and any([child.enabled for child in self.children])
        return self

    def __print_any(self, obj: any, override_enabled: bool = False, indent: Optional[int] = None):
        if not self.enabled and not self._has_active_children:
            return
        if self._out is None:
            self.get_out()
        assert self._out is not None
        process_info = multiprocessing.current_process().name
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        s: str = f"{obj}"
        s_lines: List[str] = s.split("\n")
        for s_line in s_lines:
            indent_str: str = '' if indent is None else '  ' * indent
            line: str = f"[{self._name()}] [{process_info}], {timestamp}: {indent_str}{s_line}"
            self.__print_line(line, out=self._out, override_enabled=override_enabled)

    def __print_line(self, line: str, out: TextIO, override_enabled: bool = False):
        if self.enabled or override_enabled:
            if self.lok_type == LokOutType.FILE:
                self._print_2_file(line)
            else:
                print(line, file=out)
        if self._has_active_children:
            for child in self.children:
                child.__print_line(line=line, out=child.get_out())

    def get_out(self) -> TextIO:
        if self._out is None:
            self._out = self.lok_type.out(file_options=self.file_options)
        assert self._out is not None
        return self._out

    def print(self, obj: any, out: Optional[TextIO] = None, indent: Optional[int] = None):
        out = self.out.out() if out is None else out
        self.__print_any(obj=obj, indent=indent)

    def err(self, obj: any, indent: Optional[int] = None):
        self.__print_any(obj=obj, override_enabled=True, indent=indent)

    def exception(self, e):
        lines: List[str] = [f"Exception '{e.__class__.__qualname__}'."]
        if e.__traceback__ is not None:
            tb = traceback.extract_tb(e.__traceback__)
            lines.extend(traceback.format_list(tb))
        for l in lines:
            self.err(l)

    def _print_2_file(self, line: str):
        if not self.file_options:
            return
        try:
            self.file_options.file.parent.mkdir(parents=True, exist_ok=True)
            with self.file_options.file.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as e:
            print(f"Lok._print_2_file failed: {e}", file=sys.stderr)

    def log_file(self, file: Path | str, append: bool = False) -> Lok:
        file_options: FileOptions = FileOptions(file=file, append=append)
        child: Lok = Lok(name=self.name, src=self.src, lok_type=LokOutType.FILE)
        child.file_options = file_options
        child.enabled = self.enabled
        self.children.append(child)
        self._has_active_children = child.enabled
        return self
