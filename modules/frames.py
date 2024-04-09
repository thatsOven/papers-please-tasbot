import time
import logging

logger = logging.getLogger(__name__)


class Frames:
    FRAME_RATE = 60

    def __init__(self):
        self.start_time = time.time()

    def start(self):
        self.start_time = time.time()

    def get_frame(self) -> int:
        return int((time.time() - self.start_time) * Frames.FRAME_RATE)

    def sleep(self, frames: int):
        sleep_frame = self.get_frame() + frames
        self.sleep_to(sleep_frame)

    def sleep_to(self, frame: int):
        sleep_time = (frame / 60) - (time.time() - self.start_time)
        if sleep_time <= 0:
            return
        time.sleep(sleep_time)
