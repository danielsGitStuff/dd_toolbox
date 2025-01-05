from __future__ import annotations

import sys
from datetime import datetime

import multiprocessing
import traceback

from enum import Enum
from typing import TextIO, Any, Optional, List


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

    def __init__(self, name: Optional[str] = None, src: Optional[Any] = None, out: TextIO = sys.stdout):
        self.name: str = src.__class__.__qualname__ if name is None else name
        assert self.name is not None
        self.out: LokOutType = LokOutType.by_text_io(out)
        self.enabled: bool = True
        self.stored_lines: List[str] = []

    def __call__(self, obj: any, file: Optional[TextIO | LokOutType] = None):
        out: LokOutType = self.out
        if file is not None:
            if isinstance(file, LokOutType):
                out = file
            else:
                out = LokOutType.by_text_io(file)
        self.__print_any(obj, out=out.out())

    def set_enabled(self, enabled: bool) -> Lok:
        self.enabled = enabled
        return self

    def __print_any(self, obj: any, out: TextIO, override_enabled: bool = False):
        process_info = multiprocessing.current_process().name
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        s: str = f"{obj}"
        s_lines: List[str] = s.split("\n")
        for s_line in s_lines:
            line: str = f"[{self.name}] [{process_info}], {timestamp}: {s_line}"
            self.__print_line(line, out=out, override_enabled=override_enabled)

    def __print_line(self, line: str, out: TextIO, override_enabled: bool = False):
        if self.enabled or override_enabled:
            print(line, file=out)
        else:
            self.stored_lines.append(line)

    def print(self, obj: any, out: Optional[TextIO] = None):
        out = self.out.out() if out is None else out
        self.__print_any(obj=obj, out=out)

    def err(self, obj: any):
        self.__print_any(obj=obj, out=sys.stderr, override_enabled=True)

    def print_self(self) -> Lok:
        if len(self.stored_lines) == 0:
            return self
        print(f"Lok '{self.name}'")
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
