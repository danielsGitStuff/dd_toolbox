import shutil

from pathlib import Path
from shared.workhorse import Workhorse, Workload
from typing import Any
from unittest import TestCase


class FileWorkload(Workload):
    def __init__(self, f: Path):
        super().__init__()
        self.f: Path = f

    def run_impl(self) -> Any:
        print(f"touch '{self.f}'")
        assert not self.f.exists()
        self.f.touch(exist_ok=True)
        return 11


class TestWorkhorse(TestCase):
    def setUp(self):
        self.directory: Path = Path("test_workhorse")
        shutil.rmtree(self.directory, ignore_errors=True)
        self.directory.mkdir(exist_ok=True)
        self.wh: Workhorse = Workhorse(threads=2).batch()

    def tearDown(self):
        shutil.rmtree(self.directory)

    def test_batch_1(self):
        wh: Workhorse = self.wh

        for i in range(5):
            wh.add_runnable(FileWorkload(f=Path(self.directory, f"f{i}.txt")))
        wh.join()
        print('asdasd')
