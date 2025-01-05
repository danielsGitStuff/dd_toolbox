import datetime
import os
from pathlib import Path
from shared.js3 import JS3, JS3Enc
from shared.js3dec import JS3Dec
from typing import Optional, List, Dict, Any
from unittest import TestCase


class DummyDate(JS3):
    def __init__(self):
        self.d: Optional[datetime.date] = None
        self.dict: Dict[datetime.date, int] = {}


class Dummy(JS3):
    def __init__(self):
        self.name: str = "name not set"
        self.related: Optional[Dummy] = None
        self.related_ls: List[Dummy] = []
        self.any_list_1: Optional[List[Any]] = None
        self.any_list_2: Optional[List[Any]] = None


class TestJS3Enc(TestCase):

    # def __init__(self, asdf):
    #     super().__init__()
    #     x
    def setUp(self):
        print("setup")
        self.js: Path = Path("testjson.json")
        self.dummy_date: DummyDate = DummyDate()
        self.dummy_date.d = datetime.date(2024, 8, 3)
        self.dummy_a: Dummy = Dummy()
        self.dummy_a.name = "AAA"
        self.dummy_b: Dummy = Dummy()
        self.dummy_b.name = "BBB"

    def doCleanups(self):
        print("clean")
        os.remove(self.js)

    def test_encode_date(self):
        JS3Enc(self.dummy_date).save(self.js)

    def test_decode_date(self):
        self.test_encode_date()
        des = JS3Dec().source(self.js).decode()
        self.assertEqual(self.dummy_date.d, des.d)

    def test_date_in_dict(self):
        d: datetime.date = datetime.date(2024, 8, 3)
        self.dummy_date.dict[d] = 4
        JS3Enc(self.dummy_date).save(self.js)
        decoded: DummyDate = JS3Dec().source(self.js).decode()
        print("")

    def test_ref_1(self):
        self.dummy_a.related = self.dummy_b
        self.dummy_b.related = self.dummy_a
        JS3Enc(self.dummy_a).save(self.js, indent=2)
        a: Dummy = JS3Dec().source(self.js).decode()
        b: Dummy = a.related
        self.assertEqual(a.related, b)
        self.assertEqual(a, b.related)

    def test_ref_ls(self):
        self.dummy_a.related_ls += [self.dummy_a, self.dummy_b]
        self.dummy_b.related_ls += [self.dummy_a, self.dummy_b]
        JS3Enc(self.dummy_a).save(self.js, indent=2)
        a: Dummy = JS3Dec().source(self.js).decode()
        b: Dummy = a.related_ls[1]
        self.assertEqual(a.related_ls[0], a)
        self.assertEqual(a.related_ls[1], b)
        self.assertEqual(b.related_ls[0], a)
        self.assertEqual(b.related_ls[1], b)

    def test_ref_ls2(self):
        self.dummy_a.any_list_1 = [1, 2, 3]
        self.dummy_a.any_list_2 = self.dummy_a.any_list_1
        JS3Enc(self.dummy_a).save(self.js, indent=2)
        d: Dummy = JS3Dec().source(self.js).decode()
        self.assertEqual(d.any_list_1, self.dummy_a.any_list_1)
