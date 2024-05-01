import time
import logging

logger = logging.getLogger('tas.' + __name__)


class Frames:
    FRAME_RATE = 60

    def __init__(self):
        self.start_time = time.perf_counter()

    def start(self):
        self.start_time = time.perf_counter()

    def getFrame(self) -> int:
        return int((time.perf_counter() - self.start_time) * Frames.FRAME_RATE)

    def sleep(self, frames: int):
        sleep_frame = self.getFrame() + frames
        self.sleepTo(sleep_frame)

    def sleepTo(self, frame: int):
        sleep_end = (frame / 60) + self.start_time
        current_time = time.perf_counter()
        while current_time < sleep_end:
            current_time = time.perf_counter()
        if current_time > sleep_end + 0.005:
            logger.debug(f'Slept extra {sleep_end - current_time} seconds')