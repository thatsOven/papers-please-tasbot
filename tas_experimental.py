# **NOTE**
# this is an experimental patch for the bot to work for the latest version of the game (1.4.11.124).
# it currently doesn't do much, but it's here as a start.
# 
# for the bot to work, the game language has to be english, 
# the date format must be 1982-1-23, and the game must be fullscreen in 1920x1080 resolution on the primary monitor

import json
import logging
import logging.config
import os
import pathlib
import time
from typing import ClassVar, Callable, Optional

import cv2
import dxcam
import numpy as np
import pyautogui as pg
import win32api
import win32com.client
import win32con
import win32gui
import win32process
from PIL import Image

import modules.constants.delays as delays
import modules.constants.other as other
import modules.constants.screen_new as screen
from modules.constants.screen_new import Point
from modules.documents.passport import PassportType, Nation, City, PassportData
from modules.entrant import Entrant
from modules.frames import Frames
from runs.AllEndings import AllEndings

logger = logging.getLogger(__name__)


class FilterVenvLogging(logging.Filter):
    """Without this, log file is filled with debug logs from imported modules."""

    def filter(self, record):
        return 'venv' not in record.pathname


class TAS:
    PROGRAM_DIR: ClassVar[pathlib.Path] = pathlib.Path(__file__).parent
    RUNS_DIR: ClassVar[pathlib.Path] = PROGRAM_DIR / 'runs'
    NEW_ASSETS: ClassVar[pathlib.Path] = PROGRAM_DIR / 'assets' / 'new'
    ASSETS: ClassVar[pathlib.Path] = PROGRAM_DIR / 'assets'

    IMAGE_NIGHT: ClassVar[dict[str, np.ndarray]] = None
    IMAGE_OUTSIDE: ClassVar[dict[str, np.ndarray]] = None
    IMAGE_PAPER_CORNERS: ClassVar[dict[str, np.ndarray]] = None



    PIXEL_SIZE = 3

    def __init__(self):
        self.setupLogging()
        logger.info('**EXPERIMENTAL VERSION**')

        if os.name == 'nt':
            self.hwnd = self.getWinHWND()
            shell = win32com.client.Dispatch('WScript.Shell')
            shell.SendKeys('%')
            win32gui.SetForegroundWindow(self.hwnd)
            pid = win32api.GetCurrentProcessId()
            handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, pid)
            win32process.SetPriorityClass(handle, win32process.ABOVE_NORMAL_PRIORITY_CLASS)
        else:
            raise OSError('Only Windows is currently supported')

        pg.useImageNotFoundException(False)
        pg.PAUSE = 0

        self.day: int = 0
        self.entrant: int = 0  # Entrant = Entrant()
        self.expected_ticks: list[str] = []
        self.ticks_to_click: list[int] = []  # List of indices in expected_ticks

        self.start_time: float = 0
        self.rta_start_time: float = 0
        self.day_start_time: float = 0
        self.entrant_start_time: float = 0
        self.frames: Frames = Frames()

        self.camera: dxcam.DXCamera = dxcam.create()
        self.camera.start(region=self.areaOffset((0, 0, 570, 320)))

        self.loadImageFiles()

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
            raise ProcessLookupError('No "Papers Please" window was found')
        return papers_please_hwnd[0]

    @staticmethod
    def setupLogging():
        config_path = os.path.join(TAS.PROGRAM_DIR, 'config/logging_config.json')
        with open(config_path) as f:
            config = json.load(f)
        logging.config.dictConfig(config)

    @staticmethod
    def loadImageFiles():
        TAS.IMAGE_NIGHT = {
            path.stem: np.array(Image.open(path).convert('RGB')) for path in TAS.NEW_ASSETS.glob('night/*.png')
        }
        TAS.IMAGE_OUTSIDE = {
            path.stem: np.array(Image.open(path).convert('RGB')) for path in TAS.NEW_ASSETS.glob('outside/*.png')
        }
        TAS.IMAGE_PAPER_CORNERS = {
            path.stem: np.array(Image.open(path).convert('RGB')) for path in TAS.NEW_ASSETS.glob('paper_corners/*.png')
        }

    @staticmethod
    def pixelToCoordinate(point: screen.Point) -> screen.Point:
        return screen.Point(point[0] * TAS.PIXEL_SIZE, point[1] * TAS.PIXEL_SIZE)

    @staticmethod
    def coordinateToPixel(point: screen.Point) -> screen.Point:
        return screen.Point(point[0] // TAS.PIXEL_SIZE, point[1] // TAS.PIXEL_SIZE)

    def pointOffset(self, point: screen.Point) -> screen.Point:
        window_x, window_y, _, _ = win32gui.GetWindowRect(self.hwnd)
        return screen.Point(
            TAS.PIXEL_SIZE * point[0] + window_x + screen.ZERO_POINT.x,
            TAS.PIXEL_SIZE * point[1] + window_y + screen.ZERO_POINT.y,
        )

    def areaOffset(self, area: screen.Area) -> screen.Area:
        window_x, window_y, _, _ = win32gui.GetWindowRect(self.hwnd)
        return screen.Area(*self.pointOffset((area[0], area[1])), *self.pointOffset((area[2], area[3])))

    def getArea(self, area: screen.Area) -> np.ndarray:
        """Get np array of pixels in screen area. DO NOT offset area coordinates"""
        left, top, right, bottom = area
        left, top = self.pixelToCoordinate((left, top))
        right, bottom = self.pixelToCoordinate((right, bottom))
        frame = self.camera.get_latest_frame()
        return frame[top:bottom, left:right]

    def getPixel(self, point: screen.Point) -> np.ndarray:
        """Get np array of colors at pixel location on screen. DO NOT offset point coordinates"""
        x, y = self.pixelToCoordinate(point)
        frame = self.camera.get_latest_frame()
        return frame[y, x]

    def drag(self, from_point: screen.Point, to_point: screen.Point) -> None:
        logger.debug(f'Drag from {from_point} to {to_point}')
        self.moveTo(from_point)
        self.frames.sleep(1)
        pg.mouseDown()
        self.frames.sleep(1)
        self.moveTo(to_point)

    def moveTo(self, point: screen.Point) -> None:
        pg.moveTo(self.pointOffset(point))

    def click(self, point: screen.Point, clicks: int = 1, interval_frames: int = 2):
        """Clicks `clicks` number of times. Waits at least `interval_frames` between clicks"""
        self.moveTo(point)
        if clicks == 1:
            logger.debug(f'Click {point}')
        else:
            logger.debug(f'Multi-click {point}, {clicks=}, {interval_frames=}F')

        for _ in range(clicks):
            pg.mouseDown()
            pg.mouseUp()
            self.frames.sleep(interval_frames)

    def clickUntil(self, point: screen.Point, condition: Callable[[], bool], timeout_seconds: float = 10,
                   interval_frames: int = 2):
        """Clicks until condition is true. Waits at least `interval_frames` between clicks"""
        self.moveTo(point)
        logger.debug(f'Clicking {point} until {condition.__name__}')

        start_time = time.perf_counter()
        while time.perf_counter() - start_time < timeout_seconds:
            if condition():
                return
            pg.mouseDown()
            pg.mouseUp()
            self.frames.sleep(interval_frames)
        logger.warning(f'Clicking {point} until {condition.__name__} timed out after {timeout_seconds} seconds')

    @staticmethod
    def waitUntil(condition: Callable[[], bool], timeout_seconds: float = 0, interval_seconds: float = 0):
        """Waits until condition is true"""
        logger.debug(f'Waiting until {condition.__name__}')

        start_time = time.perf_counter()
        while not condition():
            if 0 < timeout_seconds < time.perf_counter() - start_time:
                logger.warning(f'Waiting for {condition.__name__} timed out after {timeout_seconds} seconds')
                break
            if interval_seconds > 0:
                time.sleep(interval_seconds)

    def isMatchingPixel(self, point: screen.Point, color: np.array, tolerance: float = 0) -> bool:
        """Returns true if the pixel at the given coordinates matches the color.

        Params:
            point: the (x, y) coordinates of the pixel
            color: numpy array of 3 rgb values from 0 to 255
            tolerance: How closely it must match, from 0 to 1 (default 0)
                If tolerance is 0, will only return True if pixel and color exactly match
                If tolerance is 1, pixel and color must be opposites (pure white and black) to return False
        """
        pixel = self.getPixel(point)
        difference = np.sum(np.abs(pixel - color))
        return difference < tolerance * 765 or difference == 0

    def isMatchingArea(self, area: tuple[int, int, int, int], image: np.array, tolerance: float = 0) -> bool:
        """Returns true if the area at the given coordinates matches the image.

        Params:
            area: the (left, top, right, bottom) coordinates of the area
            image: image as numpy array with shape (height, width, 3)
            tolerance: How closely it must match, from 0 to 1 (default 0)
                If tolerance is 0, will only return True if area and image exactly match
                If tolerance is 1, area and image must be opposites (pure white and black) to return False
        """
        area_image = self.getArea(area)
        difference = np.sum(np.abs(image - area_image))
        left, top, right, bottom = area
        scaled_tolerance = tolerance * 765 * (right - left) * (bottom - top)
        return difference < scaled_tolerance or difference == 0

    def isMatchingAnyPixel(self, area: tuple[int, int, int, int], color: np.array, tolerance: float = 0) -> bool:
        """Returns true if any pixel in the given area coordinates matches the color.

        Params:
            area: the (left, top, right, bottom) coordinates of the area
            color: numpy array of 3 rgb values from 0 to 255
            tolerance: How closely it must match, from 0 to 1 (default 0)
                If tolerance is 0, will only return True if a pixel in the area exactly matches color
                If tolerance is 1, all pixels in area must be opposite of color (pure white and black) to return False
        """
        area = self.getArea(area)
        difference = np.abs(color - area).sum(axis=2).min()
        return difference < tolerance * 765 or difference == 0

    def identifyInitialPapers(self):
        pass

    def newGame(self):
        self.start_time = time.perf_counter()
        self.frames.start()
        self.day = 1

        self.click(screen.MAIN_STORY)
        self.frames.sleep(10)
        self.moveTo(screen.SAVE_NEW)

        def saveScreenVisible():
            return not self.isMatchingPixel(screen.SAVE_PIXEL, other.COLOR_BLACK)

        self.waitUntil(saveScreenVisible, timeout_seconds=3)

        self.rta_start_time = time.perf_counter()
        self.click(screen.SAVE_NEW)
        self.frames.sleep(10)

        def outsideVisible():
            return not self.isMatchingPixel(screen.OUTSIDE_GROUND, other.COLOR_BLACK)

        self.clickUntil(screen.CUTSCENE_INTRO_NEXT, outsideVisible, timeout_seconds=7)
        logger.debug(f'newGame() done at frame {self.frames.get_frame()}')

    def daySetup(self):
        def outsideVisible():
            return not self.isMatchingPixel(screen.OUTSIDE_GROUND, other.COLOR_BLACK)

        self.clickUntil(screen.WALK_TO_WORK, outsideVisible, timeout_seconds=10)
        self.day_start_time = time.perf_counter()
        self.entrant = 0

    def callEntrant(self):
        def isBubbleNextVisible():
            return np.all(TAS.IMAGE_OUTSIDE['nextBubbleX'] == self.getArea(screen.OUTSIDE_SPEAKER_NEXT))

        self.clickUntil(screen.OUTSIDE_HORN, isBubbleNextVisible, timeout_seconds=10)
        logger.debug(f'Entrant {self.entrant} called')

        if self.isMatchingPixel(screen.BOOTH_SHUTTER_CHECK, other.COLOR_SHUTTER):
            self.click(screen.BOOTH_SHUTTER_TOGGLE)

    def waitForEntrant(self):
        def blankWallVisible():
            return self.isMatchingPixel(screen.BOOTH_WALL_CHECK, other.COLOR_BOOTH_WALL)

        def blankWallNotVisible():
            return not self.isMatchingPixel(screen.BOOTH_WALL_CHECK, other.COLOR_BOOTH_WALL)

        self.waitUntil(blankWallVisible, timeout_seconds=3)
        self.waitUntil(blankWallNotVisible, timeout_seconds=8)

    def waitForPapers(self):
        def blankDeskVisible():
            return self.isMatchingPixel(screen.BOOTH_LEFT_PAPERS, other.COLOR_BOOTH_LEFT_DESK)

        def blankDeskNotVisible():
            return not self.isMatchingPixel(screen.BOOTH_LEFT_PAPERS, other.COLOR_BOOTH_LEFT_DESK)

        self.waitUntil(blankDeskVisible, timeout_seconds=3)
        self.waitUntil(blankDeskNotVisible, timeout_seconds=8)

    def findImage(self, screenshot: np.array, image: np.array, search_area: screen.Area = None,
                  tolerance: float = 0.01) -> Optional[Point]:
        """Finds location of `paper_img` in `screenshot`

        :param
            screenshot: image to search in as numpy array
            paper_img: image to search for as numpy array
            search_area: area of screenshot to search (default None, search whole screenshot)
            tolerance: How closely it must match, from 0 to 1 (default 0.01)
                A tolerance of 0.01 or lower will usually require an exact match

        :return
            (x, y) coordinates of match if found, None if not found
        """
        if search_area is None:
            search_area = screen.Area(0, 0, screenshot.shape[1], screenshot.shape[0])
        left, top = self.pixelToCoordinate((search_area[0], search_area[1]))
        right, bottom = self.pixelToCoordinate((search_area[2], search_area[3]))
        screenshot = screenshot[top:bottom, left:right]

        match = cv2.matchTemplate(screenshot, image, cv2.TM_CCOEFF_NORMED)
        if match.max() + tolerance < 1:
            return None

        y, x = np.unravel_index(match.argmax(), match.shape)
        x, y = self.coordinateToPixel((x, y))
        return screen.Point(x + search_area[0], y + search_area[1])

    def waitTextDelay(self):
        text_delay = 0
        if len(delays.ENTRANT_TEXT_DELAYS[self.day]) >= self.entrant:
            text_delay = delays.ENTRANT_TEXT_DELAYS[self.day][self.entrant - 1]
        while time.perf_counter() < self.entrant_start_time + text_delay:
            pass

    def passportFlingCorrection(self) -> bool:
        """Searches for a passport on the right side to correct a poorly flung passport

        :return
            True if a passport was found (and is now correctly placed under stamps)
            False if there was no passport found
        """
        screenshot = self.camera.get_latest_frame()
        for name, image in TAS.IMAGE_PAPER_CORNERS.items():
            if not name.startswith('passport'):
                continue

            passport_corner = self.findImage(screenshot, image)
            if passport_corner is not None:
                logger.warning(f'Found poorly flung passport {name} at {passport_corner}')
                break
        else:
            return False

        passport_corner = screen.Point(passport_corner.x + 5, passport_corner.y)
        self.drag(passport_corner, screen.BOOTH_PASSPORT_FLING_CORRECTION)
        return True

    def nextEntrant(self):
        self.entrant += 1
        self.callEntrant()
        self.waitForEntrant()
        self.click(screen.BOOTH_STAMP_BAR_TOGGLE)
        self.waitForPapers()
        self.identifyInitialPapers()
        self.entrant_start_time = time.perf_counter()

    def nextPartial(self):
        self.entrant += 1
        self.callEntrant()
        self.waitForEntrant()
        self.entrant_start_time = time.perf_counter()

    def fastApprove(self):
        self.click(screen.STAMP_APPROVE)
        self.drag(screen.BOOTH_LEFT_PAPERS, screen.BOOTH_PASSPORT_STAMP_POSITION)
        self.frames.sleep(2)
        self.moveTo(screen.BOOTH_ENTRANT)
        self.frames.sleep(2)
        self.waitTextDelay()
        pg.mouseUp()
        self.frames.sleep(5)

    def fastDeny(self):
        self.click(screen.STAMP_DENY)
        self.drag(screen.BOOTH_LEFT_PAPERS, screen.BOOTH_PASSPORT_STAMP_POSITION)
        self.frames.sleep(2)
        self.moveTo(screen.BOOTH_ENTRANT)
        self.frames.sleep(2)
        self.waitTextDelay()
        pg.mouseUp()
        self.frames.sleep(5)

    def passportOnlyAllow(self) -> bool:
        self.nextEntrant()
        self.fastApprove()
        return True

    def passportOnlyDeny(self) -> bool:
        self.nextEntrant()
        self.fastDeny()
        return True

    def day1Check(self) -> bool:
        self.nextEntrant()
        x, y = screen.BOOTH_LEFT_PAPERS
        passport_area = screen.Area(x, y, x + 10, y + 10)
        # for nation, color in (other.COLOR_PASSPORT_ARSTOTZKA, other.COLOR_PASSPORT_IMPOR,
        #               other.COLOR_PASSPORT_KOLECHIA, other.COLOR_PASSPORT_REPUBLIA):
        if self.isMatchingAnyPixel(passport_area, other.COLOR_PASSPORT_ARSTOTZKA):
            self.fastApprove()
        else:
            self.fastDeny()
        return True

    def day2Check(self):
        self.passportOnlyDeny()

    def waitForSleepButton(self):
        self.ticks_to_click = []

        def sleepButtonVisible():
            return self.isMatchingArea(screen.NIGHT_SLEEP_TEXT_AREA, TAS.IMAGE_NIGHT['sleep'])

        timeout = 30
        if self.day == 1:
            timeout = 180
        self.waitUntil(sleepButtonVisible, timeout_seconds=timeout)

    def waitForAllTicks(self):
        """Overriding behavior, does not actually wait
        Instead, sets up order that ticks are expected to appear, so they can be clicked instantly
        Expected ticks should always be in order they will appear
        """
        if self.day == 1:
            self.expected_ticks = ['rent', 'heat', 'food']
        else:
            self.expected_ticks = ['rent', 'heat', 'food']

    def clickOnTick(self, tick):
        """Overriding behavior, does not actually click
        Instead, adds tick to queue, so it will be clicked instantly upon appearing
        """
        if tick not in self.expected_ticks:
            logger.error(f'Got request to click unexpected tick {tick}, only expecting {self.expected_ticks}')
            return

        self.ticks_to_click.append(self.expected_ticks.index(tick))

    def dayEnd(self):
        """Click queued up ticks in order as they appear, then sleep"""
        self.ticks_to_click.sort()

        # First expected tick should always be rent or something similar, happens before any real ticks
        def firstTickVisible():
            return self.findImage(self.camera.get_latest_frame(), TAS.IMAGE_NIGHT[self.expected_ticks[0]],
                                  search_area=screen.NIGHT_TICK_AREA) is not None

        self.waitUntil(firstTickVisible, timeout_seconds=10)
        frame_timer = Frames()
        frame = 0
        ticks_clicked = 0
        for tick in self.ticks_to_click:
            while frame < 200:  # Timeout in case a tick is never found
                frame += 15
                frame_timer.sleep_to(frame)
                point = self.findImage(self.camera.get_latest_frame(), TAS.IMAGE_NIGHT[self.expected_ticks[tick]],
                                       search_area=screen.NIGHT_TICK_AREA)
                if point is None:
                    continue

                logger.debug(f'Found tick {self.expected_ticks[tick]} on frame {frame}')
                self.click((point.x + screen.NIGHT_TICK_CLICK_OFFSET.x, point.y + screen.NIGHT_TICK_CLICK_OFFSET.y))
                ticks_clicked += 1
                break

        if ticks_clicked < len(self.ticks_to_click):
            logger.error(f'Could not find tick {self.expected_ticks[self.ticks_to_click[ticks_clicked]]}, timed out '
                         f'after {frame / 60:.2f} seconds')

        self.click(screen.NIGHT_SLEEP_CLICK, clicks=5)
        exit(0)

    def run(self):
        Run = AllEndings()
        Run.tas = self
        Run.run()


if __name__ == '__main__': TAS().run()
