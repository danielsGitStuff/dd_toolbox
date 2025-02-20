from __future__ import annotations

import datetime
import json
from datetime import date
from enum import Enum
from json import JSONEncoder
from pathlib import Path
from typing import List, Dict, Set, TypeVar, Optional, Type, Any, Tuple, Callable


class JS3:
    ignored: Set[str] = set()


SKIP: Set[str] = {'__objclass__', '_sort_order_'}

# Define the type variable T
T = TypeVar('T', str, int, bool, float, List, Dict, Set, Enum, date, JS3)
T_SIMPLE: Set[Type] = {str, bool, int, float}


class Wrap:
    def __init__(self, o: O):
        self.o: O = o


class DateWrap(Wrap):
    def __init__(self, o: O, d: datetime.date):
        super().__init__(o)
        self.d: datetime.date = d

    def __hash__(self):
        return id(self)

    def date_js(self) -> Dict[str, Any]:
        value: str = self.d.strftime("%Y-%m-%d")
        d: Dict[str, Any] = {"__ci": "DD", "v": value}
        if self.o.ref_counter > 1:
            d['__id'] = self.o.index
        return d


class RefWrap:
    def __init__(self, ref_id: int):
        self.ref_id = ref_id

    def ref_js(self) -> Dict[str, int]:
        return {'__r': self.ref_id}


class ListWrap(Wrap):
    def __init__(self, o: O, something: Any):
        super().__init__(o)
        self.o: O = o
        self.ls: List[Any] = something

    def ls_js(self) -> Dict[str, str | List]:
        if self.o.ref_counter > 1:
            return {'__ci': 'LW', '__id': self.o.index, 'ls': self.ls}
        return self.ls


class DictWrap(Wrap):
    def __init__(self, o: O, something: Any):
        super().__init__(o)
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


class EnumWrap(Wrap):
    def __init__(self, o: O, d: Dict[Any, Any], ci: str, index: int):
        super().__init__(o)
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
        if self.o.ref_counter > 1:
            d['__id'] = self.o.index
        return d


class SetWrap(Wrap):
    def __init__(self, o: O, something: Any):
        super().__init__(o)
        self.s: Optional[List[Any]] = something if isinstance(something, List) else None
        self.something: Any = something if self.s is None else None

    def __hash__(self):
        return id(self)

    def set_js(self) -> Dict[str, str | List]:
        if self.something is None:
            ss: List[Any] = []
            d: Dict[str, str | Any] = {"__ci": "S", '__id': self.o.index, "s": ss}
            for s in self.s:
                ss.append(s)
            return d
        return self.something


class Traversal:
    def __init__(self):
        self.visited_instances: Dict[int, O] = {}
        self.ref_counter: Dict[int, int] = {}
        self.index: int = 0
        self.stack: List[str | int] = []

    def create_id(self) -> int:
        i: int = self.index
        self.index += 1
        return i

    def create_o(self, ins: T) -> O:
        iid: int = id(ins)
        if iid in self.visited_instances:
            return self.visited_instances[iid].ref_inc()
        o: O = O(ins)
        o.index = self.create_id()
        return o

    def visit_instance(self, o: O):
        self.visited_instances[o.iid] = o
        if o.iid not in self.ref_counter:
            self.ref_counter[o.iid] = 0
        self.ref_counter[o.iid] += 1


class O:
    def __init__(self, ins: T):
        self.ref_counter: int = 1
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
        self.is_date: bool = isinstance(ins, datetime.date)
        self.is_tuple: bool = isinstance(ins, Tuple)
        self.representation: Dict[str, Type] = {}
        self.flat_idx_2_instances: Dict[int, Any] = {}

    def ref_inc(self) -> O:
        self.ref_counter += 1
        return self

    def traverse(self, traversal: Traversal):
        if self.iid in traversal.visited_instances:
            return
        traversal.visit_instance(self)
        traversal.stack.append(self.iid)
        if self.is_js:
            js: JS3 = self.ins
            self.is_js = True
            for k, v in js.__dict__.items():
                if k in js.ignored:
                    continue
                o: O = traversal.create_o(v)
                self.d[k] = o
                traversal.stack.append(k)
                self.representation[k] = JS3
                o.traverse(traversal=traversal)
                traversal.stack.pop()
        elif self.is_simple or self.is_none:
            pass
        elif self.is_list:
            ls: List[Any] = self.ins
            for v in ls:
                o: O = traversal.create_o(v)
                self.ls.append(o)
                traversal.stack.append('LS')
                # if v is not None and v.__class__.__qualname__ == 'NXM':
                #     print(v)
                o.traverse(traversal=traversal)
                traversal.stack.pop()
        elif self.is_tuple:
            ts: Tuple = self.ins
            for t in ts:
                o: O = traversal.create_o(t)
                self.ls.append(o)
                traversal.stack.append('TS')
                o.traverse(traversal=traversal)
                traversal.stack.pop()
        elif self.is_set:
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
        elif self.is_date:
            d: datetime.date = self.ins
        else:
            raise RuntimeError(f"cannot handle '{type(self.ins)}")
        traversal.stack.pop()

    def ref(self) -> RefWrap:
        return RefWrap(self.index)

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
        if self.is_list or self.is_tuple:
            ls: List[Any] = []
            for o in self.ls:
                ls.append(o.full())
            return ListWrap(o=self, something=ls)
        if self.is_set:
            ss: List[Any] = []
            for o in self.s:
                ss.append(o.full())
            return SetWrap(o=self, something=ss)
        if self.is_dict:
            d: Dict[Any, Any] = {}
            for kk, vv in self.dd.items():
                k: Any = kk.full()
                v: Any = vv.full()
                d[k] = v
            return DictWrap(o=self, something=d)
        if self.is_enum:
            d: Dict = {}
            for k, v in self.dd.items():
                d[k.full()] = v.full()
            return EnumWrap(o=self, d=d, ci=self.ci, index=self.index)
        if self.is_date:
            return DateWrap(o=self, d=self.ins)
        else:
            raise NotImplementedError

    def flat(self, root: Optional[O] = None) -> Any:
        if self.is_simple:
            return self.ins
        if self.is_none:
            return None
        if self.used:
            return self.ref()
        self.used = True
        if self.is_js:
            d: Dict[str, Any] = {"__id": self.index, "__ci": self.ci}
            root.flat_idx_2_instances[self.index] = d
            for field, o in self.d.items():
                o: O = o
                d[field] = o.flat(root=root)

        elif self.is_list or self.is_tuple:
            ls: List[Any] = []
            root.flat_idx_2_instances[self.index] = ListWrap(o=self, something=ls)
            for o in self.ls:
                ls.append(o.flat(root=root))
        elif self.is_set:
            ss: List[Any] = []
            root.flat_idx_2_instances[self.index] = SetWrap(o=self, something=ss)
            for o in self.s:
                ss.append(o.flat(root=root))
        elif self.is_dict:
            d: Dict[Any, Any] = {}
            root.flat_idx_2_instances[self.index] = DictWrap(o=self, something=d)
            for kk, vv in self.dd.items():
                k: Any = kk.flat(root=root)
                v: Any = vv.flat(root=root)
                d[k] = v
        elif self.is_enum:
            d: Dict = {}
            root.flat_idx_2_instances[self.index] = EnumWrap(o=self, d=d, ci=self.ci, index=self.index)
            for k, v in self.dd.items():
                d[k.flat(root=root)] = v.flat(root=root)
        elif self.is_date:
            root.flat_idx_2_instances[self.index] = DateWrap(o=self, d=self.ins)
        if self == root:
            dw: DictWrap = DictWrap(o=self, something=self.flat_idx_2_instances)
            d: Dict[str, Any] = {"__ci": "_flat_", "os": dw.dict_js()}
            return d
        else:
            return self.ref()

    def __repr__(self):
        s = f"{self.ci} <- {self.iid}"
        if self.is_simple:
            s += f" = {self.ins}"
        return s

    def __hash__(self):
        return hash(self.ins)


class LeEncoder(JSONEncoder):
    @staticmethod
    def static_default(obj):
        if isinstance(obj, ListWrap):
            return obj.ls_js()
        if isinstance(obj, DictWrap):
            return obj.dict_js()
        if isinstance(obj, EnumWrap):
            return obj.enum_js()
        if isinstance(obj, SetWrap):
            return obj.set_js()
        if isinstance(obj, Set):
            return {"__ci": "S", "ls": list(obj)}
        if isinstance(obj, DateWrap):
            return obj.date_js()
        if isinstance(obj, RefWrap):
            return obj.ref_js()
        return super().default(obj)

    def default(self, obj):
        if isinstance(obj, ListWrap):
            return obj.ls_js()
        if isinstance(obj, DictWrap):
            return obj.dict_js()
        if isinstance(obj, EnumWrap):
            return obj.enum_js()
        if isinstance(obj, SetWrap):
            return obj.set_js()
        if isinstance(obj, Set):
            return {"__ci": "S", "ls": list(obj)}
        if isinstance(obj, DateWrap):
            return obj.date_js()
        if isinstance(obj, RefWrap):
            return obj.ref_js()
        return super().default(obj)


class JS3Enc:

    @staticmethod
    def standard_serialization_f(x: Any, indent: int, cls: Any) -> str:
        return json.dumps(x, indent=indent, cls=cls)

    def __init__(self, ins: T):
        self.ins: T = ins
        self.root: Optional[O] = None
        self.traversal: Optional[Traversal] = None
        self.serialization_f: Callable[[Any, int, Any], str] = JS3Enc.standard_serialization_f
        self._flat: bool = False

    def flat(self) -> JS3Enc:
        """will encode the json into a flat list. prevents recursion errors."""
        self._flat = True
        return self

    def __encode(self, debug: bool = False) -> Any:
        self.traversal = Traversal()
        self.root = self.traversal.create_o(self.ins)
        self.root.traverse(traversal=self.traversal)
        x: Any
        x = self.root.flat(root=self.root) if self._flat else self.root.full()
        return x

    def encode(self, indent: int = 2, debug: bool = False) -> str:
        x = self.__encode(debug=debug)
        js: str = self.serialization_f(x, indent, LeEncoder)
        return js

    def save(self, file: Path, indent: Optional[int] = None, debug: bool = False):
        js = self.encode(indent=indent, debug=debug)
        with open(file, "w") as f:
            f.write(js)

    def with_serialization_f(self, f: Callable[[Any, int, Any], str]) -> JS3Enc:
        self.serialization_f = f
        return self
