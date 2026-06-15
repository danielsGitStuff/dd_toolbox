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

    @staticmethod
    def by_text_io(out: TextIO) -> LokOutType:
        if sys.stderr == out:
            return LokOutType.ERR
        else:
            return LokOutType.STD

    def out(self) -> TextIO:
        if LokOutType.STD == self:
            return sys.stdout
        else:
            return sys.stderr


class Lok:
    @staticmethod
    def from_instance(ins: Any) -> Lok:
        return Lok(name=ins.__class__.__qualname__)

    def __init__(self, name: Optional[str | Callable[[], str]] = None, src: Optional[Any] = None, out: TextIO = sys.stdout):
        self._name_callable: Optional[Callable[[], str]] = None
        self.name: Optional[str] = src.__class__.__qualname__ if name is None else name if isinstance(name, str) else None
        if isinstance(name, Callable):
            self._name_callable = name
        assert self.name is not None or self._name_callable is not None
        self.out: LokOutType = LokOutType.by_text_io(out)
        self.enabled: bool = True
        self.stored_lines: List[str] = []
        self.file: Optional[Path] = None

    def _name(self) -> str:
        if self.name is not None:
            return self.name
        elif self._name_callable is not None:
            return self._name_callable()
        else:
            raise ValueError("cannot get name")

    def __call__(self, obj: any, file: Optional[TextIO | LokOutType] = None, indent: Optional[int] = None):
        out: LokOutType = self.out
        if file is not None:
            if isinstance(file, LokOutType):
                out = file
            else:
                out = LokOutType.by_text_io(file)
        self.__print_any(obj, out=out.out(), indent=indent)

    def set_enabled(self, enabled: bool) -> Lok:
        self.enabled = enabled
        return self

    def __print_any(self, obj: any, out: TextIO, override_enabled: bool = False, indent: Optional[int] = None):
        if not self.enabled:
            return
        process_info = multiprocessing.current_process().name
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        s: str = f"{obj}"
        s_lines: List[str] = s.split("\n")
        for s_line in s_lines:
            indent_str: str = '' if indent is None else '  ' * indent
            line: str = f"[{self._name()}] [{process_info}], {timestamp}: {indent_str}{s_line}"
            self.__print_line(line, out=out, override_enabled=override_enabled)

    def __print_line(self, line: str, out: TextIO, override_enabled: bool = False):
        if self.enabled or override_enabled:
            print(line, file=out)
            self._print_2_file(line)
        else:
            self.stored_lines.append(line)

    def print(self, obj: any, out: Optional[TextIO] = None, indent: Optional[int] = None):
        out = self.out.out() if out is None else out
        self.__print_any(obj=obj, out=out, indent=indent)

    def err(self, obj: any, indent: Optional[int] = None):
        self.__print_any(obj=obj, out=sys.stderr, override_enabled=True, indent=indent)

    def print_self(self) -> Lok:
        if len(self.stored_lines) == 0:
            return self
        print(f"Lok '{self._name()}'")
        for l in self.stored_lines:
            print(l)
        return self

    def exception(self, e):
        lines: List[str] = [f"Exception '{e.__class__.__qualname__}'."]
        if e.__traceback__ is not None:
            tb = traceback.extract_tb(e.__traceback__)
            lines.extend(traceback.format_list(tb))
        for l in lines:
            self.err(l)

    def _print_2_file(self, line: str):
        if not self.file:
            return
        try:
            self.file.parent.mkdir(parents=True, exist_ok=True)
            with self.file.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as e:
            print(f"Lok._print_2_file failed: {e}", file=sys.stderr)

    def log_file(self, file: Path | str) -> Lok:
        self.file = file if isinstance(file, Path) else Path(file)
        return self

    def log_file_reset(self) -> Lok:
        assert self.file is not None
        if self.file.exists():
            os.remove(self.file)
        return self
