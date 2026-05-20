import datetime
from .js3 import ListWrap, SetWrap, DictWrap, RefWrap, DateWrap
from .lok import Lok

from typing import Any, List, Set, Dict


class SelfReferenceFinder:
    def __init__(self, obj: Any):
        self.root: Any = obj
        self.stack: List[str] = []
        self.visited: Dict[int, Any] = {}
        self.lok: Lok = Lok(src=self)
        self.max_depth: int = 0
        self.depth: int = 0

    def down(self, s: str):
        self.stack.append(s)
        self.depth += 1
        self.max_depth = max(self.depth, self.max_depth)

    def up(self):
        self.stack.pop()
        self.depth -= 1

    def traverse(self):
        self._traverse(self.root)

    def _visit(self, obj: Any):
        idd: int = id(obj)
        if idd in self.visited:
            for x in self.stack:
                self.lok.err(f"   {x}")
            raise RuntimeError(f"id already visited: {idd}.")
        self.visited[idd] = obj

    def _traverse(self, obj: Any):
        if (obj is None or isinstance(obj, RefWrap) or isinstance(obj, DateWrap) or isinstance(obj, int) or isinstance(obj, str) or isinstance(obj, float)
                or isinstance(obj, bool) or isinstance(obj, datetime.date)):
            return
        elif isinstance(obj, List) or isinstance(obj, Set):
            self._visit(obj)
            self._iterate(obj)
        elif isinstance(obj, ListWrap):
            self.down("LW")
            self._visit(obj)
            self._iterate(obj.ls)
            self.up()
        elif isinstance(obj, SetWrap):
            self.down("S")
            self._visit(obj)
            self._iterate(obj.s)
            self.up()
        elif isinstance(obj, DictWrap):
            self._visit(obj)
            for k, v in obj.d.items():
                self.down(f"DWK {k}")
                self._traverse(k)
                self.up()
                self.down(f"DWV {v}")
                self._traverse(v)
                self.up()
        elif isinstance(obj, Dict):
            self._visit(obj)
            for k, v in obj.items():
                self.down(f"DK {k}")
                self._traverse(k)
                self.up()
                self.down(f"DV {v}")
                self._traverse(v)
                self.up()
        else:
            raise RuntimeError('Unknown')

    def _iterate(self, obj: List | Set):
        self.stack.append('ls')
        for o in obj:
            self._traverse(o)
        self.stack.pop()
