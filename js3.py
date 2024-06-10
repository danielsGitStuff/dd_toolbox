from __future__ import annotations

import json
from datetime import date
from enum import Enum
from json import JSONEncoder
from pathlib import Path
from typing import List, Dict, Set, TypeVar, Optional, Type, Any


class JS3:
    """The basic class. These objects will be traversed and any Lists, Dicts, Sets or references to other instances will be included in the serialised JSON."""
    pass


SKIP: Set[str] = {'__objclass__', '_sort_order_'}

# Define the type variable T
T = TypeVar('T', str, int, bool, float, List, Dict, Set, Enum, date, JS3)
T_SIMPLE: Set[Type] = {str, bool, int, float}


class DictWrap:
    def __init__(self, something: Any):
        self.d: Optional[Dict[Any, Any]] = something if isinstance(something, Dict) else None
        self.something: Any = something if self.d is None else None

    def __hash__(self):
        return id(self)

    def dict_js(self) -> Dict[str, str | List]:
        if self.something is None:
            ks: List[Any] = []
            vs: List[Any] = []
            d: [str, str | Any] = {"__ci": "DW", "ks": ks, "vs": vs}
            for k, v in self.d.items():
                ks.append(k)
                vs.append(v)
            return d
        return self.something

    def __repr__(self):
        return f"{'D' if self.something is None else 'S'} <- {self.__hash__()}"


class EnumWrap:
    def __init__(self, d: Dict[Any, Any], ci: str, index: int):
        self.d: Dict[Any, Any] = d
        self.ci: str = ci
        self.index: int = index

    def enum_js(self) -> Dict[str, Any]:
        ks: List[Any] = []
        vs: List[Any] = []
        d: [str, str | Any] = {"__ci": "E", "__cci": self.ci, "ks": ks, "vs": vs, "__id": self.index}
        for k, v in self.d.items():
            ks.append(k)
            vs.append(v)
        return d


class SetWrap:
    def __init__(self, something: Any):
        self.s: Optional[List[Any]] = something if isinstance(something, List) else None
        self.something: Any = something if self.s is None else None

    def __hash__(self):
        return id(self)

    def set_js(self) -> Dict[str, str | List]:
        if self.something is None:
            ss: List[Any] = []
            d: Dict[str, str | Any] = {"__ci": "S", "s": ss}
            for s in self.s:
                ss.append(s)
            return d
        return self.something


class Traversal:
    def __init__(self):
        self.visited_instances: Dict[int, O] = {}
        self.index: int = 0
        self.stack: List[str | int] = []

    def create_id(self) -> int:
        i: int = self.index
        self.index += 1
        return i

    def create_o(self, ins: T) -> O:
        iid: int = id(ins)
        if iid in self.visited_instances:
            return self.visited_instances[iid]
        o: O = O(ins)
        o.index = self.create_id()
        return o


class O:
    def __init__(self, ins: T):
        self.ins: T = ins
        self.iid: int = id(ins)
        self.index: Optional[int] = None
        self.t: Type = type(ins)
        mod: str = self.t.__module__
        cla: str = self.t.__name__
        self.ci: str = f"{mod}/{cla}"
        self.is_simple: bool = self.t in T_SIMPLE
        self.d: Dict[str, O] = {}
        self.dd: Dict[O, O] = {}
        self.s: Set[O] = set()
        self.ls: List[O] = []
        self.used: bool = False
        self.is_js: bool = isinstance(ins, JS3)
        self.is_list: bool = isinstance(ins, List)
        self.is_set: bool = isinstance(ins, Set)
        self.is_dict: bool = isinstance(ins, Dict)
        self.is_none: bool = ins is None
        self.is_enum: bool = isinstance(ins, Enum)
        self.representation: Dict[str, Type] = {}

    def traverse(self, traversal: Traversal):
        if self.iid in traversal.visited_instances:
            return
        traversal.visited_instances[self.iid] = self
        traversal.stack.append(self.iid)
        if self.is_js:
            js: JS3 = self.ins
            self.is_js = True
            for k, v in js.__dict__.items():
                o: O = traversal.create_o(v)
                self.d[k] = o
                traversal.stack.append(k)
                self.representation[k] = JS3
                o.traverse(traversal=traversal)
                traversal.stack.pop()
        elif self.is_simple or self.is_none:
            pass
        elif self.is_list:
            self.is_list = True
            ls: List[Any] = self.ins
            for v in ls:
                o: O = traversal.create_o(v)
                self.ls.append(o)
                traversal.stack.append('LS')
                o.traverse(traversal=traversal)
                traversal.stack.pop()
        elif self.is_set:
            self.is_set = True
            ss: Set[Any] = self.ins
            for s in ss:
                o: O = traversal.create_o(s)
                self.s.add(o)
                traversal.stack.append("SET")
                o.traverse(traversal=traversal)
                traversal.stack.pop()
        elif self.is_dict:
            for k, v in self.ins.items():
                ok: O = traversal.create_o(k)
                ov: O = traversal.create_o(v)
                self.dd[ok] = ov
                traversal.stack.append("D.K")
                ok.traverse(traversal=traversal)
                traversal.stack.pop()
                traversal.stack.append("D.V")
                ov.traverse(traversal=traversal)
                traversal.stack.pop()
        elif self.is_enum:
            en: Enum = self.ins
            for k, v in en.__dict__.items():
                if k in SKIP:
                    continue
                ok = traversal.create_o(k)
                ov = traversal.create_o(v)
                self.dd[ok] = ov
                traversal.stack.append("E.K")
                ok.traverse(traversal=traversal)
                traversal.stack.pop()
                traversal.stack.append("E.V")
                ov.traverse(traversal=traversal)
                traversal.stack.pop()
        else:
            raise RuntimeError(f"cannot handle '{type(self.ins)}")
        traversal.stack.pop()

    def ref(self) -> DictWrap:
        return DictWrap({"__r": self.index})

    def full(self) -> Any:
        if self.is_simple:
            return self.ins
        if self.is_none:
            return None
        if self.used:
            return self.ref()
        self.used = True
        if self.is_js:
            d: Dict[str, Any] = {"__id": self.index, "__ci": self.ci}
            for field, o in self.d.items():
                o: O = o
                d[field] = o.full()
            return d
        if self.is_list:
            ls: List[Any] = []
            for o in self.ls:
                ls.append(o.full())
            return ls
        if self.is_set:
            ss: List[Any] = []
            for o in self.s:
                ss.append(o.full())
            return SetWrap(ss)
        if self.is_dict:
            d: Dict[Any, Any] = {}
            for kk, vv in self.dd.items():
                k: Any = kk.full()
                v: Any = vv.full()
                d[k] = v
            return DictWrap(d)
        elif self.is_enum:
            d: Dict = {}
            for k, v in self.dd.items():
                d[k.full()] = v.full()
            return EnumWrap(d, ci=self.ci, index=self.index)
        else:
            raise NotImplementedError

    def __repr__(self):
        s = f"{self.ci} <- {self.iid}"
        if self.is_simple:
            s += f" = {self.ins}"
        return s

    def __hash__(self):
        return hash(self.ins)


class LeEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, DictWrap):
            return obj.dict_js()
        if isinstance(obj, EnumWrap):
            return obj.enum_js()
        if isinstance(obj, SetWrap):
            return obj.set_js()
        if isinstance(obj, Set):
            return {"__ci": "S", "ls": list(obj)}
        return super().default(obj)


class JS3Enc:

    def __init__(self, ins: T):
        self.ins: T = ins
        self.root: Optional[O] = None
        self.traversal: Optional[Traversal] = None

    def __encode(self) -> Any:
        self.traversal = Traversal()
        self.root = self.traversal.create_o(self.ins)
        self.root.traverse(traversal=self.traversal)
        x = self.root.full()
        return x

    def encode(self, indent: int = 2) -> str:
        x = self.__encode()
        js: str = json.dumps(x, indent=indent, cls=LeEncoder)
        return js

    def save(self, file: Path, indent: int = 2):
        x = self.__encode()
        with open(file, "w") as f:
            json.dump(x, f, indent=indent, cls=LeEncoder)
