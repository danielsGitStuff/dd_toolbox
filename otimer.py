import time


class OTimer:
    def __init__(self, name: str) -> None:
        self.name = name
        self.sum = 0
        self.start_time = 0
        self.fps = 0
        self.start_count = 0

    def start(self) -> 'OTimer':
        self.start_time = time.time()
        self.start_count += 1
        return self

    def fps(self) -> int:
        duration = (time.time() - self.fps)
        self.fps = time.time()
        if duration > 0:
            return int(1000 / duration)
        return 0

    def __str__(self) -> str:
        return f"Timer[{self.name}]: {self.get_duration_in_ms()}ms"

    def stop(self) -> 'OTimer':
        self.sum += int((time.time() - self.start_time) * 1e9)
        return self

    def get_duration_in_ms(self) -> int:
        return int(self.sum / 1e6)

    def get_duration_in_ns(self) -> int:
        return self.sum

    def get_duration_in_s(self) -> int:
        return int((time.time() - self.start_time))

    def print(self) -> 'OTimer':
        print(f"{self.__class__.__name__}.'{self.name}'.print: {self.get_duration_in_ms()}")
        return self

    def reset(self) -> 'OTimer':
        self.sum = 0
        self.start_count = 0
        return self

    def get_start_count(self) -> int:
        return self.start_count

    def get_average_duration(self) -> int:
        return int(self.sum / self.start_count)
