# **NOTE**
# this is an experimental patch for the bot to work for the latest version of the game (1.4.11.124).
# it currently doesn't do much, but it's here as a start.
# 
# for the bot to work, the game language has to be english, 
# the date format must be 1982-1-23, and the game must be fullscreen in 1920x1080 resolution
import json
import logging
import logging.config
import os
import pathlib
import time
from typing import ClassVar, Callable

import dxcam
import numpy as np
import pyautogui as pg
import win32com.client
import win32gui
from PIL import Image

import modules.constants.screen_new as screen
import modules.constants.delays as delays
from modules.documents.passport import City, Nation, PassportData, PassportType
from modules.frames import Frames
from runs.AllEndings import AllEndings

MOMENTUM_STOP_TIME = 0.15

logger = logging.getLogger(__name__)


class FilterVenvLogging(logging.Filter):
    """Without this, log file is filled with debug logs from imported modules."""

    def filter(self, record):
        return 'venv' not in record.pathname


class TasException(Exception):
    pass


class TAS:
    PROGRAM_DIR: ClassVar[str] = str(pathlib.Path(__file__).parent.absolute())
    RUNS_DIR: ClassVar[str] = os.path.join(PROGRAM_DIR, 'runs')
    ASSETS: ClassVar[str] = os.path.join(PROGRAM_DIR, 'assets')

    # TODO Only Republia updated, probably other passports are wrong too but this still needs testing
    PASSPORT_TYPES = (
        PassportType(
            Nation.ANTEGRIA,
            os.path.join(ASSETS, 'passports', 'antegria'),
            (City.ST_MARMERO, City.GLORIAN, City.OUTER_GROUSE),
            PassportData().offsets(
                name=(271, 327, 500, 342),
                birth=(325, 251, 390, 262),
                sex=(305, 269, 314, 280),
                city=(305, 287, 418, 302),
                expiration=(325, 305, 390, 316),
                number=(271, 347, 504, 358),
                picture=(421, 225, 500, 320),
                label=(271, 225, 390, 242)
            )
        ),
        PassportType(
            Nation.ARSTOTZKA,
            os.path.join(ASSETS, 'passports', 'arstotzka'),
            (City.ORVECH_VONOR, City.EAST_GRESTIN, City.PARADIZNA),
            PassportData().offsets(
                name=(271, 225, 503, 240),
                birth=(411, 245, 476, 256),
                sex=(391, 261, 400, 272),
                city=(391, 277, 506, 292),
                expiration=(411, 293, 476, 304),
                number=(271, 345, 394, 356),
                picture=(271, 245, 350, 340),
                label=(413, 315, 500, 334)
            )
        ),
        PassportType(
            Nation.IMPOR,
            os.path.join(ASSETS, 'passports', 'impor'),
            (City.ENKYO, City.HAIHAN, City.TSUNKEIDO),
            PassportData().offsets(
                name=(269, 221, 503, 236),
                birth=(415, 243, 482, 254),
                sex=(395, 259, 404, 270),
                city=(395, 275, 498, 290),
                expiration=(415, 291, 482, 302),
                number=(335, 341, 500, 352),
                picture=(273, 241, 352, 336),
                label=(275, 343, 334, 354)
            )
        ),
        PassportType(
            Nation.KOLECHIA,
            os.path.join(ASSETS, 'passports', 'kolechia'),
            (City.YURKO_CITY, City.VEDOR, City.WEST_GRESTIN),
            PassportData().offsets(
                name=(271, 245, 502, 260),
                birth=(413, 263, 478, 274),
                sex=(393, 279, 402, 290),
                city=(393, 295, 502, 310),
                expiration=(413, 311, 478, 322),
                number=(354, 345, 505, 356),
                picture=(271, 263, 350, 358),
                label=(271, 221, 498, 238)
            )
        ),
        PassportType(
            Nation.OBRISTAN,
            os.path.join(ASSETS, 'passports', 'obristan'),
            (City.SKAL, City.LORNDAZ, City.MERGEROUS),
            PassportData().offsets(
                name=(271, 245, 502, 260),
                birth=(329, 271, 394, 282),
                sex=(309, 287, 318, 298),
                city=(309, 303, 416, 318),
                expiration=(329, 319, 394, 330),
                number=(275, 345, 422, 356),
                picture=(423, 263, 502, 358),
                label=(269, 221, 504, 240)
            )
        ),
        PassportType(
            Nation.REPUBLIA,
            os.path.join(ASSETS, 'patches', 'republianPassport'),
            (City.TRUE_GLORIAN, City.LESRENADI, City.BOSTAN),
            PassportData().offsets(
                name=(271, 223, 503, 238),
                birth=(329, 245, 394, 256),
                sex=(309, 261, 318, 272),
                city=(309, 277, 423, 292),
                expiration=(329, 293, 394, 304),
                number=(271, 345, 507, 356),
                picture=(425, 241, 504, 336),
                label=(273, 321, 396, 336)
            )
        ),
        PassportType(
            Nation.UNITEDFED,
            os.path.join(ASSETS, 'passports', 'unitedFed'),
            (City.GREAT_RAPID, City.SHINGLETON, City.KORISTA_CITY),
            PassportData().offsets(
                name=(271, 245, 504, 260),
                birth=(413, 261, 479, 272),
                sex=(393, 277, 402, 288),
                city=(393, 293, 504, 308),
                expiration=(413, 309, 479, 320),
                number=(355, 345, 507, 356),
                picture=(271, 261, 350, 356),
                label=(271, 223, 504, 238)
            )
        )
    )

    IMAGE_NEXT_X = np.asarray(Image.open(
        os.path.join(ASSETS, "nextBubbleX.png")
    ).convert("RGB")),

    COLOR_BLACK = np.array([0, 0, 0])
    COLOR_BOOTH_WALL = np.array([50, 37, 37])
    COLOR_BOOTH_LEFT_DESK = np.array([132, 138, 107])
    COLOR_SHUTTER = np.array([53, 45, 41])

    def __init__(self):
        self.setupLogging()
        logger.info('**EXPERIMENTAL VERSION**')

        pg.useImageNotFoundException(False)
        pg.PAUSE = 0

        self.hwnd = self.getWinHWND()
        shell = win32com.client.Dispatch('WScript.Shell')
        shell.SendKeys('%')
        win32gui.SetForegroundWindow(self.hwnd)

        self.day: int = 0
        self.entrant: int = 0

        self.start_time: float = 0
        self.rta_start_time: float = 0
        self.day_start_time: float = 0
        self.entrant_start_time: float = 0
        self.frames = Frames()

        self.camera = dxcam.create(output_idx=1)
        x1, y1, x2, y2 = self.areaOffset(0, 0, 570, 320)
        while x1 < 0:
            x1 += 1920
            x2 += 1920
        self.camera.start(region=(x1, y1, x2, y2))

    @classmethod
    def getWinHWND(cls) -> str:
        papers_please_hwnd = ['']

        def callback(hwnd, hwnd_container):
            if win32gui.GetWindowText(hwnd) in ('Papers Please', 'PapersPlease'):
                logging.debug(f'Found window ({hwnd=})')
                hwnd_container[0] = hwnd

        win32gui.EnumWindows(callback, papers_please_hwnd)
        if papers_please_hwnd[0] == '':
            logging.error('Unable to find window')
            raise TasException('No "Papers Please" window was found')
        return papers_please_hwnd[0]

    @staticmethod
    def setupLogging():
        config_path = os.path.join(TAS.PROGRAM_DIR, 'config/logging_config.json')
        with open(config_path) as f:
            config = json.load(f)
        logging.config.dictConfig(config)

    def pointOffset(self, x: int, y: int) -> tuple[int, int]:
        window_x, window_y, _, _ = win32gui.GetWindowRect(self.hwnd)
        return screen.Point(
            3 * x + window_x + screen.ZERO_POINT.x,
            3 * y + window_y + screen.ZERO_POINT.y,
        )

    def areaOffset(self, x1: int, y1: int, x2: int, y2: int) -> tuple[int, int, int, int]:
        window_x, window_y, _, _ = win32gui.GetWindowRect(self.hwnd)
        return screen.Area(*self.pointOffset(x1, y1), *self.pointOffset(x2, y2))

    def regionOffset(self, x: int, y: int, width: int, height: int) -> tuple[int, int, int, int]:
        window_x, window_y, _, _ = win32gui.GetWindowRect(self.hwnd)
        return screen.Region(*self.pointOffset(x, y), width, height)

    def getArea(self, area: screen.Area) -> np.array:
        """Get np array of pixels in screen area. DO NOT offset area coordinates"""
        left, top, right, bottom = area
        frame = self.camera.get_latest_frame()
        return frame[3 * top:3 * bottom, 3 * left:3 * right]

    def getPixel(self, point: screen.Point) -> np.array:
        """Get np array of colors at pixel location on screen. DO NOT offset point coordinates"""
        x, y = point
        frame = self.camera.get_latest_frame()
        return frame[3 * y, 3 * x]

    def quickDrag(self, from_point: screen.Point, to_point: screen.Point) -> None:
        logger.debug(f'Drag from {from_point} to {to_point}')
        self.frames.sleep(2)
        self.moveTo(from_point)
        self.frames.sleep(2)
        pg.mouseDown()
        self.frames.sleep(2)
        self.moveTo(to_point)
        self.frames.sleep(2)
        pg.mouseUp()
        self.frames.sleep(2)

    def moveTo(self, point: screen.Point) -> None:
        logger.debug(f'Move to {point}')
        pg.moveTo(self.pointOffset(*point))

    def click(self, at: tuple[int, int], clicks: int = 1, interval_frames: int = 2):
        """Clicks `clicks` number of times. Waits at least `interval_frames` between clicks"""
        self.moveTo(at)
        if clicks == 1:
            logger.debug(f'Click at {at}')
        else:
            logger.debug(f'Multi-click at {at}, {clicks=}, {interval_frames=}F')

        for _ in range(clicks):
            pg.mouseDown()
            pg.mouseUp()
            self.frames.sleep(interval_frames)

    def clickUntil(self, at: tuple[int, int], condition: Callable[[], bool], timeout_seconds: float = 10,
                   interval_frames: int = 2):
        """Clicks until condition is true. Waits at least `interval_frames` between clicks"""
        self.moveTo(at)
        logger.debug(f'Clicking until {condition.__name__}')

        first_frame = self.frames.get_frame() + interval_frames
        for frame in range(first_frame, first_frame + timeout_seconds * Frames.FRAME_RATE, interval_frames):
            if condition():
                return
            pg.mouseDown()
            pg.mouseUp()
            self.frames.sleep_to(frame)
            if self.frames.get_frame() > frame:
                logger.debug(f'Missed frame {frame}')
        logger.warning(f'Clicking {at} until {condition.__name__} timed out after {timeout_seconds} seconds')

    def waitUntil(self, condition: Callable[[], bool], timeout_seconds: float = 0, interval_seconds: float = 0):
        """Waits until condition is true"""
        logger.debug(f'Waiting until {condition.__name__}')

        start_time = time.time()
        while not condition():
            if 0 < timeout_seconds < time.time() - start_time:
                logger.warning(f'Waiting for {condition.__name__} timed out after {timeout_seconds} seconds')
                break
            if interval_seconds > 0:
                time.sleep(interval_seconds)

    def matchingPixel(self, at: tuple[int, int], color: np.array, tolerance: float = 0) -> bool:
        """Returns true if the pixel at the given coordinates matches the color.

        Params:
            at: the (x, y) coordinates of the pixel
            color: numpy array of 3 rgb values from 0 to 255
            tolerance: How closely it must match, from 0 to 1 (default 0)
                If tolerance is 0, will only return True if pixel and color exactly match
                If tolerance is 1, pixel and color must be opposites (pure white and black) to return False
        """
        pixel = self.getPixel(at)
        difference = sum(np.abs(pixel - color))
        return difference < tolerance * 765 or difference == 0

    def nextMessageVisible(self) -> bool:
        return (TAS.IMAGE_NEXT_X == self.getArea(screen.OUTSIDE_SPEAKER_NEXT)).all()

    def boothShutterDown(self) -> bool:
        return self.matchingPixel(screen.BOOTH_SHUTTER_CHECK, TAS.COLOR_SHUTTER)

    def newGame(self):
        self.start_time = time.time()
        self.frames.start()
        self.day = 1

        self.click(screen.MAIN_STORY)
        self.frames.sleep(10)

        def saveScreenVisible():
            return not self.matchingPixel(screen.SAVE_PIXEL, TAS.COLOR_BLACK)

        self.waitUntil(saveScreenVisible, timeout_seconds=3)

        self.rta_start_time = time.time()
        self.click(screen.SAVE_NEW)
        self.frames.sleep(10)

        def outsideVisible():
            return not self.matchingPixel(screen.OUTSIDE_GROUND, TAS.COLOR_BLACK)

        self.clickUntil(screen.CUTSCENE_INTRO_NEXT, outsideVisible, timeout_seconds=7)
        logger.debug(f'newGame() done at frame {self.frames.get_frame()}')

    def daySetup(self):
        def outsideVisible():
            return not self.matchingPixel(screen.OUTSIDE_GROUND, TAS.COLOR_BLACK)

        self.clickUntil(screen.WALK_TO_WORK, outsideVisible, timeout_seconds=10)
        self.day_start_time = time.time()
        self.entrant = 0

    def callEntrant(self):
        self.clickUntil(screen.OUTSIDE_HORN, self.nextMessageVisible, timeout_seconds=10)
        if self.boothShutterDown():
            self.click(screen.BOOTH_SHUTTER_TOGGLE)
        logger.debug(f'Entrant called at frame {self.frames.get_frame()}')

    def waitForEntrant(self):
        def blankWallVisible():
            return self.matchingPixel(screen.BOOTH_WALL_CHECK, TAS.COLOR_BOOTH_WALL)

        def blankWallNotVisible():
            return not self.matchingPixel(screen.BOOTH_WALL_CHECK, TAS.COLOR_BOOTH_WALL)

        self.waitUntil(blankWallVisible, timeout_seconds=3)
        self.waitUntil(blankWallNotVisible, timeout_seconds=8)

    def waitForPapers(self):
        def blankDeskVisible():
            return self.matchingPixel(screen.BOOTH_LEFT_PAPERS, TAS.COLOR_BOOTH_LEFT_DESK)

        def blankDeskNotVisible():
            return not self.matchingPixel(screen.BOOTH_LEFT_PAPERS, TAS.COLOR_BOOTH_LEFT_DESK)

        self.waitUntil(blankDeskVisible, timeout_seconds=3)
        self.waitUntil(blankDeskNotVisible, timeout_seconds=8)

    def returnPassport(self, from_point: tuple[int, int]):
        text_delay = 0
        if len(delays.ENTRANT_TEXT_DELAYS[self.day]) > self.entrant:
            text_delay = delays.ENTRANT_TEXT_DELAYS[self.day][self.entrant]
        # print(self.day, self.entrant, delays.ENTRANT_TEXT_DELAYS[self.day])
        # print(text_delay)
        text_delay -= time.time() - self.entrant_start_time
        if text_delay > 0:
            time.sleep(text_delay)
        self.quickDrag(from_point, screen.BOOTH_ENTRANT)

    def nextEntrant(self):
        self.entrant += 1
        self.callEntrant()
        self.waitForEntrant()
        self.click(screen.BOOTH_STAMP_BAR_TOGGLE)
        self.waitForPapers()
        self.entrant_start_time = time.time()

    def passportOnlyAllow(self) -> bool:
        self.nextEntrant()
        self.quickDrag(screen.BOOTH_LEFT_PAPERS, screen.BOOTH_PASSPORT_FLING)
        self.click(screen.STAMP_APPROVE)
        self.returnPassport(screen.BOOTH_PASSPORT_REGRAB)
        return True

    def passportOnlyDeny(self) -> bool:
        self.nextEntrant()
        self.quickDrag(screen.BOOTH_LEFT_PAPERS, screen.BOOTH_PASSPORT_FLING)
        self.click(screen.STAMP_DENY)
        self.returnPassport(screen.BOOTH_PASSPORT_REGRAB)
        return True

    def day1Check(self) -> bool:
        self.nextEntrant()
        self.quickDrag(screen.BOOTH_LEFT_PAPERS, screen.BOOTH_PASSPORT_FLING)

        return True

    def run(self):
        Run = AllEndings()
        Run.tas = self
        Run.run()


if __name__ == '__main__': TAS().run()
