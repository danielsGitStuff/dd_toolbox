from __future__ import annotations

import sys
import traceback
from concurrent.futures import ProcessPoolExecutor
from typing import List, Any, Optional


class Workload:

    def __init__(self):
        self.executed: bool = False
        self.result: Any = None
        self.index: Optional[int] = None

    def run(self):
        if self.executed:
            return
        self.executed = True
        self.result = self.run_impl()

    def run_impl(self) -> Any:
        raise NotImplementedError

    def get_result(self) -> Any:
        if not self.executed:
            self.run()
        return self.result

    def check_past_execution(self):
        return self.executed

    def pre_execution(self):
        pass


class Workhorse:
    class StaticMethods:
        @staticmethod
        def partition_list(ls: List[Any], n: int, max_size: Optional[int] = None) -> List[List[Any]]:
            """
            Partitions a list into n parts or more such that each sublist
            contains at most max_size parts (if specified).

            Args:
                ls: The list to partition.
                n: The desired minimum number of partitions.
                max_size: Optional. The maximum size of each sublist.

            Returns:
                A list of sublists.
            """

            if max_size is None:
                q, r = divmod(len(ls), n)
                return [ls[i * q + min(i, r):(i + 1) * q + min(i + 1, r)] for i in range(n)]
            else:
                num_partitions = max(n, (len(ls) + max_size - 1) // max_size)
                result = []
                for i in range(num_partitions):
                    start = i * max_size
                    end = min((i + 1) * max_size, len(ls))
                    if start < end:  # Ensure we don't add empty sublists
                        result.append(ls[start:end])
                return result

        @staticmethod
        def static_execute(workload: Workload):
            try:
                return workload.get_result()
            except Exception as e:
                print(f"got exception on workload '{e.__class__.__qualname__}' '{e}'", file=sys.stderr)
                traceback.print_exc()

        @staticmethod
        def format_elapsed_time(elapsed_time: float) -> str:
            """
            Format elapsed time in hours, minutes, and seconds (hh:mm:ss).

            Parameters:
            - elapsed_time (float): The elapsed time in seconds.

            Returns:
            - str: Formatted elapsed time.
            """
            # Convert elapsed_time to hours, minutes, and seconds
            hours, remainder = divmod(elapsed_time, 3600)
            minutes, seconds = divmod(remainder, 60)

            # Format and return the result
            formatted_time = "{:02}:{:02}:{:02}".format(int(hours), int(minutes), int(seconds))
            return formatted_time

    def __init__(self, threads: int = 4):
        self.threads: int = threads
        self.workloads: List[Workload] = []
        self.closed: bool = False
        self.executor: ProcessPoolExecutor = ProcessPoolExecutor(max_workers=self.threads)

    def add_runnable(self, workload: Workload):
        workload.index = len(self.workloads)
        self.workloads.append(workload)

    def join(self) -> List:
        if self.closed:
            raise RuntimeError('pool already closed!')
        self.closed = True
        futures = []
        remaining_work: List[Workload] = [w for w in self.workloads if not w.check_past_execution()]
        work = self.workloads
        print(f"'{type(self).__name__}' will work on {len(work)} workloads using {self.threads} processes.")
        for w in remaining_work:
            w.pre_execution()
        # todo serialise lib objects
        for w in remaining_work:
            f = self.executor.submit(Workhorse.StaticMethods.static_execute, workload=w)
            futures.append(f)
        self.executor.shutdown()
        debug = [f.result() for f in futures]
        for w, fr in zip(remaining_work, debug):
            w: Workload = w
            w.result = fr
            w.executed = True
        results = [w.get_result() for w in self.workloads]
        return results

    def reset(self) -> Workhorse:
        self.closed = False
        self.workloads = []
        self.executor = ProcessPoolExecutor(max_workers=self.threads)
        return self
