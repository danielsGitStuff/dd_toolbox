from __future__ import annotations

import sys

import datetime
import importlib
import json
from enum import Enum
from pathlib import Path
from typing import Optional, Any, Dict, List, Type, Set

SKIP: Set[str] = {'__id', '__ci', '__r'}
T_SIMPLE: Set[Type] = {str, bool, int, float}


class JS3Dec:
    def __init__(self):
        self.src: Optional[str] = None
        self.dicts: Optional[Dict[Any, Any] | List] = None
        self.id_2_obj: Dict[int, Any] = {}

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
        self.dicts = json.loads(self.src)

    def source(self, src: Path | str) -> JS3Dec:
        if isinstance(src, str):
            self.src = src
        else:
            with open(src, 'r', encoding='utf-8') as f:
                self.src = f.read()
        return self

    def decode(self) -> Any:
        self.__read_src()
        return self.decode_instance(self.dicts)

    def instance(self, cls: type):
        try:
            return cls()
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

    def decode_enum(self, src_ins: Dict[str,Any]) -> Enum:
        d: Dict = self.decode_dw(src_ins)
        index: int = src_ins["__id"]
        cci: str = src_ins["__cci"]
        cc: List[str] = cci.split("/")
        mod: str = cc[0]
        cl: str = cc[1]
        name = d["_name_"]
        en = self.get_class_from_module(module_name=mod, class_name=cl)
        e: Enum = en[name]
        self.id_2_obj[index] = e
        return e
