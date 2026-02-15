from __future__ import annotations

import sys

import datetime
import importlib
import inspect
import json
from enum import Enum
from pathlib import Path
from shared.js3 import JS3
from shared.lok import Lok
from shared.otimer import OTimer
from typing import Optional, Any, Dict, List, Type, Set, Callable

SKIP: Set[str] = {'__id', '__ci', '__r'}
T_SIMPLE: Set[Type] = {str, bool, int, float}


class JS3Dec:
    def __init__(self):
        self.src: Optional[str] = None
        self.dicts: Optional[Dict[Any, Any] | List] = None
        self.id_2_obj: Dict[int, Any] = {}
        self.flat_id_2_instance: Dict[int, Any] = {}
        self.lok: Lok = Lok(src=self)
        self.f_decode: Callable[[str], Any] = json.loads

    def get_class_from_module(self, module_name: str, class_name: str):
        try:
            # Dynamically import the module
            module = importlib.import_module(module_name)
        except ImportError:
            print(f"Module '{module_name}' not found.")
            return None

        try:
            # Get the class from the module
            class_ = getattr(module, class_name)
        except AttributeError:
            print(f"Class '{class_name}' not found in module '{module_name}'.")
            return None

        return class_

    def __read_src(self):
        self.dicts = self.f_decode(self.src)

    def source(self, src: Path | str) -> JS3Dec:
        if isinstance(src, str):
            self.src = src
        else:
            with open(src, 'r', encoding='utf-8') as f:
                self.src = f.read()
        return self

    def with_decode_f(self, f: Callable[[str], Any]) -> JS3Dec:
        self.f_decode = f
        return self

    def decode(self) -> Any:
        self.__read_src()
        return self.decode_instance(self.dicts)

    def instance(self, cls: Type) -> Any:
        """
        Creates an instance of the given class.

        If the class has a constructor without arguments, it calls that.
        Otherwise, it attempts to find a constructor and call it with None values
        for all arguments.
        """
        if cls is None:
            self.lok.err("CLS is None!")
        try:
            return cls()
        except TypeError as e:
            if "no arguments" in str(e) or "missing" in str(e) and "required" in str(e):
                # Likely a constructor with arguments
                try:
                    # Inspect the constructor arguments
                    init_method = getattr(cls, "__init__")
                    if init_method is object.__init__:
                        # If the class doesn't have its own __init__, it inherits object.__init__, which takes no arguments.
                        # This should have been caught by the initial cls() call, but handle it just in case.
                        return cls()

                    signature = inspect.signature(init_method)

                    # Get the constructor arguments (excluding 'self')
                    parameters = [
                        p
                        for p in signature.parameters.values()
                        if p.name != "self"
                           and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
                    ]

                    # Create an instance with None values for all arguments
                    return cls(*[None] * len(parameters))
                except Exception as inner_e:
                    print(f"Could not instantiate '{cls}' with None values.", file=sys.stderr)
                    raise inner_e
            else:
                print(f"Could not instantiate '{cls}'.", file=sys.stderr)
                raise e
        except Exception as e:
            print(f"Could not instantiate '{cls}'.", file=sys.stderr)
            raise e

    def decode_instance(self, src_ins: Dict[Any, Any] | List[Any]) -> Any:
        ci: Optional[str] = None
        idd: Optional[int] = None
        cls: Optional[Type] = None
        ins: Optional[Any] = None
        src_t: Type = type(src_ins)
        if isinstance(src_ins, Dict):
            ci = src_ins.get("__ci", None)
            idd = src_ins.get("__id", None)
            ref_id: Optional[int] = src_ins.get('__r', None)
            if ref_id is not None:
                return self.id_2_obj[ref_id]
            if ci is not None and "/" in ci:
                splits: List[str] = ci.split("/")
                mod: str = splits[0]
                cl: str = splits[1]
                cls = self.get_class_from_module(module_name=mod, class_name=cl)
                ins = self.instance(cls)
                self.id_2_obj[idd] = ins
                for field, v in src_ins.items():
                    if field in SKIP:
                        continue
                    sub_ins: Any = self.decode_instance(v)
                    setattr(ins, field, sub_ins)
                return ins
            if 'LW' == ci:
                return self.decode_ls(src_ins)
            if "DW" == ci:
                return self.decode_dw(src_ins)
            if "S" == ci:
                return self.decode_set(src_ins)
            if "E" == ci:
                return self.decode_enum(src_ins)
            if "DD" == ci:
                date_str: str = src_ins["v"]
                d: datetime.date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                return d
            if "_flat_" == ci:
                return self.decode_flat(src_ins)

            # ref: Optional[int] = src_ins.get("__r", None)
            # if ref is not None:
            #     return self.id_2_obj[ref]
            raise RuntimeError(f"cannot deal with ci '{ci}'.")
        if isinstance(src_ins, List):
            ls: List = []
            for e in src_ins:
                v = self.decode_instance(e)
                ls.append(v)
            return ls
        if src_t in T_SIMPLE:
            return src_ins

    def decode_flat(self, src_d: Dict) -> Any:
        indices: List[int] = src_d['os']['ks']
        vs: List[Any] = src_d['os']['vs']
        # the first iteration will create all referencable objects (Lists, Sets, JS3, Enum etc.)
        # and put it in a dict keyed by its reference id
        t1: OTimer = OTimer("JS decode creating instances...").start()
        for idx, v in zip(indices, vs):
            self.flat_decode_instance(src_ins=v, idx=idx)
        t1.stop().print()
        # stage 2 reiterates all of it again and resolves all references and adds missing properties
        t2: OTimer = OTimer("JS decode: enriching...").start()
        for idx, v in zip(indices, vs):
            self.flat_enrich(src_ins=v, idx=idx)
        t2.stop().print()
        return self.flat_id_2_instance[0]

    def flat_enrich(self, src_ins: Dict[Any, Any] | List[Any], idx: int) -> Any:
        decoded: Any = self.flat_id_2_instance[idx]
        if isinstance(decoded, JS3):
            src_ins: Dict[Any, Any] = src_ins
            for field, src in src_ins.items():
                if field in SKIP:
                    continue
                decoded_prop = self.flat_enrich_stage_2(src)
                setattr(decoded, field, decoded_prop)
        elif isinstance(decoded, List):
            src_ins: List[Any] = src_ins
            for src in src_ins:
                decoded.append(self.flat_enrich_stage_2(src))
        elif isinstance(decoded, datetime.date):
            return decoded
        elif isinstance(decoded, Dict):
            src_ins: Dict[str, Any] = src_ins
            ks: List[Any] = src_ins["ks"]
            vs: List[Any] = src_ins["vs"]
            for k, v in zip(ks, vs):
                decoded_k = self.flat_enrich_stage_2(k)
                decoded_v = self.flat_enrich_stage_2(v)
                decoded[decoded_k] = decoded_v
            pass
        elif isinstance(decoded, Set):
            for src in src_ins['s']:
                decoded.add(self.flat_enrich_stage_2(src))
        else:
            raise RuntimeError(f"Do not know what to do!")
        pass

    def flat_enrich_stage_2(self, src: Any):
        if src is None:
            return None
        t: Type = type(src)
        if t in T_SIMPLE:
            return src
        if isinstance(src, Dict):
            ref_id: Optional[int] = src.get('__r', None)
            if ref_id is not None:
                return self.flat_id_2_instance[ref_id]
            raise RuntimeError("needs debugging")

    def flat_decode_instance(self, src_ins: Dict[Any, Any] | List[Any], idx: int) -> Any:
        ci: Optional[str] = None
        idd: Optional[int] = None
        cls: Optional[Type] = None
        ins: Optional[Any] = None
        src_t: Type = type(src_ins)
        if isinstance(src_ins, Dict):
            ci = src_ins.get("__ci", None)
            idd = src_ins.get("__id", None)
            ref_id: Optional[int] = src_ins.get('__r', None)
            if ref_id is not None:
                return self.id_2_obj[ref_id]
            if ci is not None and "/" in ci:
                splits: List[str] = ci.split("/")
                mod: str = splits[0]
                cl: str = splits[1]
                cls = self.get_class_from_module(module_name=mod, class_name=cl)
                ins = self.instance(cls)
                self.id_2_obj[idd] = ins
                self.flat_id_2_instance[idx] = ins
                return ins
            if 'LW' == ci:
                self.flat_id_2_instance[idx] = []
                return
            if "DW" == ci:
                self.flat_id_2_instance[idx] = {}
                return
            if "S" == ci:
                self.flat_id_2_instance[idx] = set()
                return
            if "E" == ci:
                self.flat_id_2_instance[idx] = self.decode_enum(src_ins)
            if "DD" == ci:
                date_str: str = src_ins["v"]
                d: datetime.date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                self.flat_id_2_instance[idx] = d
                return d
            raise RuntimeError(f"cannot deal with ci '{ci}'.")
        if isinstance(src_ins, List):
            ls: List = []
            self.flat_id_2_instance[idx] = ls
            return ls
        if src_t in T_SIMPLE:
            return src_ins

    def decode_dw(self, src_d: Dict):
        d: Dict = {}
        iid: Optional[int] = src_d.get('__id', None)
        if iid is not None:
            self.id_2_obj[iid] = d
        ks: List = src_d['ks']
        vs: List = src_d['vs']
        for k, v in zip(ks, vs):
            if "__r" == k:
                return self.id_2_obj[v]
            sub_k = self.decode_instance(k)
            sub_v = self.decode_instance(v)
            d[sub_k] = sub_v
        return d

    def decode_ls(self, src: Dict) -> List[Any]:
        src_ls: List[Any] = src['ls']
        ls: List[Any] = []
        iid: int = src['__id']
        if iid is not None:
            self.id_2_obj[iid] = ls
        for elem in src_ls:
            decoded_elem = self.decode_instance(elem)
            ls.append(decoded_elem)
        return ls

    def decode_set(self, src: Dict[str, Any]) -> Set[Any]:
        s: Set = set()
        iid: int = src['__id']
        if iid is not None:
            self.id_2_obj[iid] = s
        ls: List = src['s']
        for e in ls:
            v = self.decode_instance(e)
            s.add(v)
        return s

    def decode_enum(self, src_ins: Dict[str, Any]) -> Enum:
        d: Dict = self.decode_dw(src_ins)
        index: int = src_ins["__id"]
        cci: str = src_ins["__cci"]
        cc: List[str] = cci.split("/")
        mod: str = cc[0]
        cl: str = cc[1]
        name = d["_name_"]
        en = self.get_class_from_module(module_name=mod, class_name=cl)
        if en is None:
            self.lok.err(f"Could not create class from module '{mod}' and class name '{cl}'.")
        e: Enum = en[name]
        self.id_2_obj[index] = e
        return e
