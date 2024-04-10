# MIT License
#
# Copyright (c) 2024 thatsOven, Bryan Allaire
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# **NOTE**
# this is an experimental patch for the bot to work for the latest version of the game (1.4.11.124).
# it currently doesn't do much, but it's here as a start.
# 
# for the bot to work, the game language has to be English,
# the date format must be 1982-1-23, and the game must be
# fullscreen in 1920x1080 resolution on the primary monitor.

import json
import logging
import logging.config
import os
import pathlib
import time
from typing import ClassVar, Callable, Optional, Sequence

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
from modules.frames import Frames
import runs.run as run
import runs.AllEndings as AllEndings

logger = logging.getLogger('tas')


class TAS:
    """TAS that should eventually contain methods to do any run, but currently limited to day 1 activities.

    Attributes:
        day: The current day from 1 to 31
        entrant: The current entrant number starting from 1 to match the entrant counter on the game screen.
    """
    PROGRAM_DIR: ClassVar[pathlib.Path] = pathlib.Path(__file__).parent
    RUNS_DIR: ClassVar[pathlib.Path] = PROGRAM_DIR / 'runs'
    NEW_ASSETS: ClassVar[pathlib.Path] = PROGRAM_DIR / 'assets' / 'new'
    ASSETS: ClassVar[pathlib.Path] = PROGRAM_DIR / 'assets'

    IMAGE_NIGHT: ClassVar[dict[str, np.ndarray]] = None
    IMAGE_OUTSIDE: ClassVar[dict[str, np.ndarray]] = None
    IMAGE_PAPER_CORNERS: ClassVar[dict[str, np.ndarray]] = None

    PIXEL_SIZE = 3

    def __init__(self):
        self._setupLogging()
        logger.info('**EXPERIMENTAL VERSION**')

        if os.name == 'nt':
            self.hwnd = self._getWinHWND()
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

        self._loadImageFiles()
        self._camera: dxcam.DXCamera = dxcam.create()
        self._camera.start(region=self._areaOffset((0, 0, 570, 320)))

        self.day: int = 0
        self.entrant: int = 0

        self._expected_ticks: list[str] = []
        self._ticks_to_click: list[int] = []  # List of indices of expected_ticks

        self._frames: Frames = Frames()
        self._start_time: float = 0
        self._rta_start_time: float = 0
        self._day_start_time: float = 0
        self._entrant_start_time: float = 0

    @staticmethod
    def _getWinHWND() -> str:
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
    def _setupLogging():
        config_path = os.path.join(TAS.PROGRAM_DIR, 'config/logging_config.json')
        with open(config_path) as f:
            config = json.load(f)
        logging.config.dictConfig(config)

    @staticmethod
    def _loadImageFiles():
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
    def _pixelToCoordinate(point: screen.Point) -> screen.Point:
        """Converts point given in game pixels to game coordinates (not screen coordinates; use _pointOffset())"""
        return screen.Point(point[0] * TAS.PIXEL_SIZE, point[1] * TAS.PIXEL_SIZE)

    @staticmethod
    def _coordinateToPixel(point: screen.Point) -> screen.Point:
        """Converts point given in game coordinates (not screen coordinates) to game pixels"""
        return screen.Point(point[0] // TAS.PIXEL_SIZE, point[1] // TAS.PIXEL_SIZE)

    def _pointOffset(self, point: screen.Point) -> screen.Point:
        """Converts point given in pixels in the game to screen coordinates."""
        window_x, window_y, _, _ = win32gui.GetWindowRect(self.hwnd)
        return screen.Point(
            TAS.PIXEL_SIZE * point[0] + window_x + screen.ZERO_POINT.x,
            TAS.PIXEL_SIZE * point[1] + window_y + screen.ZERO_POINT.y,
        )

    def _areaOffset(self, area: screen.Area) -> screen.Area:
        """Converts area given in pixels in the game to screen coordinates."""
        window_x, window_y, _, _ = win32gui.GetWindowRect(self.hwnd)
        return screen.Area(*self._pointOffset((area[0], area[1])), *self._pointOffset((area[2], area[3])))

    def _getArea(self, area: screen.Area) -> np.ndarray:
        """Get image as numpy array in given area of the game screen.

        Args:
            area: Area on the screen in game pixels.

        Returns:
            An image as a numpy array in the shape (height, width, 3).
        """
        left, top, right, bottom = area
        left, top = self._pixelToCoordinate((left, top))
        right, bottom = self._pixelToCoordinate((right, bottom))
        frame = self._camera.get_latest_frame()
        return frame[top:bottom, left:right]

    def _getPixel(self, point: screen.Point) -> np.ndarray:
        """Get 1x1 pixel image as numpy array at pixel location on the game screen.

        Args:
            point: Point on the screen in game pixels.

        Returns:
            A one-dimensional numpy array of length 3 with the RGB values of the pixel.
        """
        x, y = self._pixelToCoordinate(point)
        frame = self._camera.get_latest_frame()
        return frame[y, x]

    def _drag(self, from_point: screen.Point, to_point: screen.Point):
        """Drag from one point to another without releasing at the end.

        Args:
            from_point: The point to drag from in game pixels. The mouse will click down at this point.
            to_point: The point to drag to in game pixels. The mouse will NOT release at this point.
        """
        logger.debug(f'Drag from {from_point} to {to_point}')
        self.moveTo(from_point)
        self._frames.sleep(1)
        pg.mouseDown()
        self._frames.sleep(1)
        self.moveTo(to_point)

    def _clickUntil(self, point: screen.Point, condition: Callable[[], bool], timeout_seconds: float = 10,
                    interval_frames: int = 2):
        """Clicks on point given in game pixels until condition is True.

        Args:
            point: The point to click in game pixels.
            condition: A function that should return True once clicking should stop.
            timeout_seconds: Number of seconds until clicking will stop even if condition is False. If set
                to 0, there is no timeout and clicking will happen indefinitely until condition is True.
            interval_frames: Number of frames to wait after every click. Recommended to be at least 2 unless
                checking condition takes a significant amount of time.
        """
        self.moveTo(point)
        logger.debug(f'Clicking {point} until {condition.__name__}')

        start_time = time.perf_counter()
        while time.perf_counter() - start_time < timeout_seconds:
            if condition():
                return
            pg.mouseDown()
            pg.mouseUp()
            self._frames.sleep(interval_frames)
        logger.warning(f'Clicking {point} until {condition.__name__} timed out after {timeout_seconds} seconds')

    def _waitUntil(self, condition: Callable[[], bool], timeout_seconds: float = 0, interval_frames: int = 0):
        """Waits until condition is True.

        Args:
            condition: A function that should return True once waiting should stop.
            timeout_seconds: Number of seconds until waiting will stop even if condition is False. If set
                to 0, there is no timeout and this will wait indefinitely until condition is True.
            interval_frames: Number of frames to wait after each check of condition.
        """
        logger.debug(f'Waiting until {condition.__name__}')

        start_time = time.perf_counter()
        while not condition():
            if 0 < timeout_seconds < time.perf_counter() - start_time:
                logger.warning(f'Waiting for {condition.__name__} timed out after {timeout_seconds} seconds')
                return
            if interval_frames > 0:
                self._frames.sleep(interval_frames)

    def _isMatchingPixel(self, point: screen.Point, color: Sequence[int], tolerance: float = 0) -> bool:
        """Returns True if the pixel at the given coordinates matches the color.

        Args:
            point: The point to click in game pixels.
            color: A sequence of length 3 with the RGB values of the pixel.
            tolerance: A value from 0 to 1 representing how closely it must match to return True.
                If tolerance is 0 (default), will only return True if pixel and color exactly match.
                If tolerance is 1, pixel and color must be opposites (pure white and black) to return False.
        """
        pixel = self._getPixel(point)
        difference = np.sum(np.abs(pixel - color))
        return difference < tolerance * 765 or difference == 0

    def _isMatchingArea(self, area: screen.Area, image: np.array, tolerance: float = 0) -> bool:
        """Returns True if the area at the given coordinates matches the image.

        Params:
            area: The (left, top, right, bottom) coordinates of the game screen area given in game pixels.
            image: An image as a numpy array with shape (height, width, 3) to check against the screen area.
            tolerance: A value from 0 to 1 representing how closely it must match to return True.
                If tolerance is 0 (default), will only return True if area and image exactly match.
                If tolerance is 1, area and image must be opposites (pure white and black) to return False.
        """
        area_image = self._getArea(area)
        difference = np.sum(np.abs(image - area_image))
        left, top, right, bottom = area
        scaled_tolerance = tolerance * 765 * (right - left) * (bottom - top)
        return difference < scaled_tolerance or difference == 0

    def _isMatchingAnyPixel(self, area: screen.Area, color: Sequence[int], tolerance: float = 0) -> bool:
        """Returns True if any pixel in the given area coordinates matches the color.

        Params:
            area: The (left, top, right, bottom) coordinates of the game screen area given in game pixels.
            color: A sequence of length 3 with the RGB values of the pixel.
            tolerance: A value from 0 to 1 representing how closely it must match to return True.
                If tolerance is 0, will only return True if a pixel in the area exactly matches color.
                If tolerance is 1, all pixels in area must be of opposite color (pure white and black) to return False.
        """
        area = self._getArea(area)
        difference = np.abs(color - area).sum(axis=2).min()
        return difference < tolerance * 765 or difference == 0

    def _findImage(self, screenshot: np.array, image: np.array, search_area: screen.Area = None,
                   tolerance: float = 0.01) -> Optional[Point]:
        """Finds location of image on screen.

        Args:
            screenshot: Image capture of game screen to search in.
            image: Image to search for as numpy array of shape (height, width, 3).
            search_area: The (left, top, right, bottom) coordinates of the screenshot to search. If None (default),
                searches the entire screenshot.
            tolerance: A value from 0 to 1 representing how closely it must match to return True.
                If tolerance is 0.01 (default) or lower, it will usually require an exact match. A tolerance of 0 may
                cause it to never match, even if an exact match exists.
                As tolerance approaches 1, it becomes likely to always match, even if no close match exists.

        Returns:
            Point coordinates of upper left corner of closest match if a match was found within the given tolerance.
            None if no close enough match was found.
        """
        if search_area is None:
            search_area = screen.Area(0, 0, screenshot.shape[1], screenshot.shape[0])
        left, top = self._pixelToCoordinate((search_area[0], search_area[1]))
        right, bottom = self._pixelToCoordinate((search_area[2], search_area[3]))
        screenshot = screenshot[top:bottom, left:right]

        match = cv2.matchTemplate(screenshot, image, cv2.TM_CCOEFF_NORMED)
        if match.max() + tolerance < 1:
            return None

        y, x = np.unravel_index(match.argmax(), match.shape)
        x, y = self._coordinateToPixel((x, y))
        return screen.Point(x + search_area[0], y + search_area[1])

    def moveTo(self, point: screen.Point):
        """Move to point given in game pixels."""
        pg.moveTo(self._pointOffset(point))

    def click(self, point: screen.Point, clicks: int = 1, interval_frames: int = 2):
        """Clicks on the point given in game pixels once or more than once.

        Args:
            point: The point to click in game pixels.
            clicks: The number of times to click.
            interval_frames: The number of frames to wait after every click. Recommended to be at least 2.
        """
        self.moveTo(point)
        if clicks == 1:
            logger.debug(f'Click {point}')
        else:
            logger.debug(f'Multi-click {point}, {clicks=}, {interval_frames=}F')

        for _ in range(clicks):
            pg.mouseDown()
            pg.mouseUp()
            self._frames.sleep(interval_frames)

    def newGame(self):
        """Starts a new game up to the point that the area outside the booth is visible."""
        self._start_time = time.perf_counter()
        self._frames.start()
        self.day = 1

        self.click(screen.MAIN_STORY)
        self._frames.sleep(10)
        self.moveTo(screen.SAVE_NEW)

        def saveScreenVisible():
            return not self._isMatchingPixel(screen.SAVE_PIXEL, other.COLOR_BLACK)

        self._waitUntil(saveScreenVisible, timeout_seconds=3)

        self._rta_start_time = time.perf_counter()
        self.click(screen.SAVE_NEW)
        self._frames.sleep(10)

        def outsideVisible():
            return not self._isMatchingPixel(screen.OUTSIDE_GROUND, other.COLOR_BLACK)

        self._clickUntil(screen.CUTSCENE_INTRO_NEXT, outsideVisible, timeout_seconds=7)
        logger.debug(f'newGame() done at frame {self._frames.get_frame()}')

    def daySetup(self):
        """Sets up for a new day. Clicks "Walk to Work" until the area outside the booth is visible."""

        def outsideVisible():
            return not self._isMatchingPixel(screen.OUTSIDE_GROUND, other.COLOR_BLACK)

        self._clickUntil(screen.WALK_TO_WORK, outsideVisible, timeout_seconds=10)
        self._day_start_time = time.perf_counter()
        self.entrant = 0

    def callEntrant(self):
        """Calls the next entrant by clicking the horn until the word "NEXT" is visible above it."""

        def isBubbleNextVisible():
            return np.all(TAS.IMAGE_OUTSIDE['nextBubbleX'] == self._getArea(screen.OUTSIDE_SPEAKER_NEXT))

        self._clickUntil(screen.OUTSIDE_HORN, isBubbleNextVisible, timeout_seconds=10)
        logger.debug(f'Entrant {self.entrant} called')

        if self._isMatchingPixel(screen.BOOTH_SHUTTER_CHECK, other.COLOR_SHUTTER):
            self.click(screen.BOOTH_SHUTTER_TOGGLE)

    def waitForEntrant(self):
        """Waits for the next entrant to arrive after calling them."""

        def blankWallVisible():
            return self._isMatchingPixel(screen.BOOTH_WALL_CHECK, other.COLOR_BOOTH_WALL)

        def blankWallNotVisible():
            return not self._isMatchingPixel(screen.BOOTH_WALL_CHECK, other.COLOR_BOOTH_WALL)

        self._waitUntil(blankWallVisible, timeout_seconds=3)
        self._waitUntil(blankWallNotVisible, timeout_seconds=8)

    def waitForPapers(self):
        """Waits for papers to be visible on the desk in front of the entrant."""

        def blankDeskVisible():
            return self._isMatchingPixel(screen.BOOTH_LEFT_PAPERS, other.COLOR_BOOTH_LEFT_DESK)

        def blankDeskNotVisible():
            return not self._isMatchingPixel(screen.BOOTH_LEFT_PAPERS, other.COLOR_BOOTH_LEFT_DESK)

        self._waitUntil(blankDeskVisible, timeout_seconds=3)
        self._waitUntil(blankDeskNotVisible, timeout_seconds=8)

    def waitTextDelay(self):
        """Waits until the time the last document should be returned as the last textbox from the entrant appears.

        Waits until a set time, given the day and entrant number, after the moment the documents were first dropped
        onto the desk.
        """
        text_delay = 0
        if len(delays.ENTRANT_TEXT_DELAYS[self.day]) >= self.entrant:
            text_delay = delays.ENTRANT_TEXT_DELAYS[self.day][self.entrant - 1]
        while time.perf_counter() < self._entrant_start_time + text_delay:
            pass

    def passportFlingCorrection(self) -> bool:
        """Searches for and corrects a passport on the right side desk.

        Returns:
            True if a passport was found (and is now correctly placed under stamps)
            False if there was no passport found
        """
        screenshot = self._camera.get_latest_frame()
        for name, image in TAS.IMAGE_PAPER_CORNERS.items():
            if not name.startswith('passport'):
                continue

            passport_corner = self._findImage(screenshot, image)
            if passport_corner is not None:
                logger.warning(f'Found poorly flung passport {name} at {passport_corner}')
                break
        else:
            return False

        passport_corner = screen.Point(passport_corner.x + 5, passport_corner.y)
        self._drag(passport_corner, screen.BOOTH_PASSPORT_FLING_CORRECTION)
        self._frames.sleep(1)
        pg.mouseUp()
        return True

    def nextEntrant(self):
        """Increments the entrant counter and gets the next entrant.

        Calls the next entrant and waits for them to arrive in the booth and place their papers on the left counter.
        """
        self.entrant += 1
        self.callEntrant()
        self.waitForEntrant()
        self.click(screen.BOOTH_STAMP_BAR_TOGGLE)
        self.waitForPapers()
        self._entrant_start_time = time.perf_counter()

    def nextPartial(self):
        """Increments the entrant counter and partially gets the next entrant.

        Calls the next entrant and waits for them to arrive, but does not wait for papers to appear on the left counter.
        """
        self.entrant += 1
        self.callEntrant()
        self.waitForEntrant()
        self._entrant_start_time = time.perf_counter()

    def fastApprove(self):
        """Quickly approves an entrant with only a passport on the left counter."""
        self.click(screen.STAMP_APPROVE)
        self._drag(screen.BOOTH_LEFT_PAPERS, screen.BOOTH_PASSPORT_STAMP_POSITION)
        self._frames.sleep(2)
        self.moveTo(screen.BOOTH_ENTRANT)
        self._frames.sleep(2)
        self.waitTextDelay()
        pg.mouseUp()
        self._frames.sleep(5)

    def fastDeny(self):
        """Quickly denies an entrant with only a passport on the left counter."""
        self.click(screen.STAMP_DENY)
        self._drag(screen.BOOTH_LEFT_PAPERS, screen.BOOTH_PASSPORT_STAMP_POSITION)
        self._frames.sleep(2)
        self.moveTo(screen.BOOTH_ENTRANT)
        self._frames.sleep(2)
        self.waitTextDelay()
        pg.mouseUp()
        self._frames.sleep(5)

    def passportOnlyAllow(self) -> bool:
        """Calls and approves the next entrant. Assumes they have only a passport."""
        self.nextEntrant()
        self.fastApprove()
        return True

    def passportOnlyDeny(self) -> bool:
        """Calls and denies the next entrant. Assumes they have only a passport."""
        self.nextEntrant()
        self.fastDeny()
        return True

    def day1Check(self) -> bool:
        """Calls and processes the next entrant according to day 1 rules. Assumes they have only a passport.

        Approves the entrant if they are Arstotzkan, denies them otherwise.
        """
        self.nextEntrant()
        x, y = screen.BOOTH_LEFT_PAPERS
        passport_area = screen.Area(x, y, x + 10, y + 10)
        # for nation, color in (other.COLOR_PASSPORT_ARSTOTZKA, other.COLOR_PASSPORT_IMPOR,
        #               other.COLOR_PASSPORT_KOLECHIA, other.COLOR_PASSPORT_REPUBLIA):
        if self._isMatchingAnyPixel(passport_area, other.COLOR_PASSPORT_ARSTOTZKA):
            self.fastApprove()
        else:
            self.fastDeny()
        return True

    def day2Check(self, wrong: bool = False):
        """Calls and processes the next entrant according to day 2 rules. Assumes they have only a passport.

        Args:
            wrong: Whether to intentionally process the entrant incorrectly to get a citation.
        """
        # TODO Implement day2Check
        self.passportOnlyDeny()

    def waitForSleepButton(self):
        """Waits for the sleep button to appear."""
        self._ticks_to_click = []

        def sleepButtonVisible():
            return self._isMatchingArea(screen.NIGHT_SLEEP_TEXT_AREA, TAS.IMAGE_NIGHT['sleep'])

        timeout = 30
        if self.day == 1:
            timeout = 180
        self._waitUntil(sleepButtonVisible, timeout_seconds=timeout)

    def waitForAllTicks(self):
        """Overriding behavior, does not actually wait. Instead, sets up order that ticks are expected to appear.

        Expected ticks should always be in order they will appear on the night screen.
        """
        if self.day == 1:
            self._expected_ticks = ['rent', 'heat', 'food']
        else:
            self._expected_ticks = ['rent', 'heat', 'food']

    def clickOnTick(self, tick):
        """Overriding behavior, does not actually click. Instead, adds tick to queue to be clicked."""
        if tick not in self._expected_ticks:
            logger.error(f'Tick {tick} not found in expected ticks {self._expected_ticks}')
            return

        self._ticks_to_click.append(self._expected_ticks.index(tick))

    def dayEnd(self):
        """Clicks added ticks in order as they appear, then clicks sleeps."""
        self._ticks_to_click.sort()

        # First expected tick should always be rent or something similar, happens before any real ticks
        def firstTickVisible():
            return self._findImage(self._camera.get_latest_frame(), TAS.IMAGE_NIGHT[self._expected_ticks[0]],
                                   search_area=screen.NIGHT_TICK_AREA) is not None

        self._waitUntil(firstTickVisible, timeout_seconds=10)
        frame_timer = Frames()
        frame = 0
        ticks_clicked = 0
        for tick in self._ticks_to_click:
            while frame < 200:  # Timeout in case a tick is never found
                frame += 15
                frame_timer.sleep_to(frame)
                point = self._findImage(self._camera.get_latest_frame(), TAS.IMAGE_NIGHT[self._expected_ticks[tick]],
                                        search_area=screen.NIGHT_TICK_AREA)
                if point is None:
                    continue

                logger.debug(f'Found tick {self._expected_ticks[tick]} on frame {frame}')
                self.click((point.x + screen.NIGHT_TICK_CLICK_OFFSET.x, point.y + screen.NIGHT_TICK_CLICK_OFFSET.y))
                ticks_clicked += 1
                break

        if ticks_clicked < len(self._ticks_to_click):
            logger.error(f'Could not find tick {self._expected_ticks[self._ticks_to_click[ticks_clicked]]}, timed out '
                         f'after {frame / 60:.2f} seconds')

        self.click(screen.NIGHT_SLEEP_CLICK, clicks=5)

    def run(self, route: run.Run):
        """Runs TAS by calling the route's run() method."""
        route.tas = self
        route.run()


if __name__ == '__main__':
    run = AllEndings.AllEndings()
    TAS().run(run)
