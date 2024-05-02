# **NOTE**
# this is an experimental patch for the bot to work for the latest version of the game (1.4.11.124).
# it currently doesn't do much, but it's here as a start.
# 
# for the bot to work, the game language has to be english, 
# the date format must be 1982-1-23, and the game must be fullscreen in 1920x1080 resolution

from tas import *

from modules.frames import Frames

import logging

logger = logging.getLogger('tas.' + __name__)

OLD_WINDOW_OFFSET     = (8, 31)
OLD_WINDOW_RESOLUTION = (1140, 640)
FULLSCREEN_REAL_BOX   = (105, 60, 1815, 1020)
NEW_MOUSE_OFFSET      = (2, 2)

class NewTAS(TAS):
    def __init__(self):
        super().__init__()

        self.frames = Frames()
        
        logger.info("**EXPERIMENTAL VERSION**")
        pg.PAUSE = 0.034 

    def getScreen(self) -> Image.Image:
        realScreen = ImageGrab.grab(win32gui.GetWindowRect(self.hwnd)).convert("RGB").crop(FULLSCREEN_REAL_BOX)
        size = offsetPoint(OLD_WINDOW_RESOLUTION, OLD_WINDOW_OFFSET)
        offsetImg = Image.new("RGB", size)
        offsetImg.paste(realScreen.resize(OLD_WINDOW_RESOLUTION, Image.Resampling.NEAREST), OLD_WINDOW_OFFSET + size)
        return offsetImg
    
    def mouseOffset(self, x: int, y: int) -> tuple[int, int]:
        bX, bY, _, _ = win32gui.GetWindowRect(self.hwnd)
        return (
            bX + FULLSCREEN_REAL_BOX[0] + NEW_MOUSE_OFFSET[0] + (x - OLD_WINDOW_OFFSET[0]) // 2 * 3,
            bY + FULLSCREEN_REAL_BOX[1] + NEW_MOUSE_OFFSET[1] + (y - OLD_WINDOW_OFFSET[1]) // 2 * 3,
        )
    
    def dragTo(self, at: tuple[int, int]) -> None:
        pg.mouseDown()
        pg.dragTo(*self.mouseOffset(*at), button = 'left', mouseDownUp = False)
        self.frames.sleep(8) # stops momentum and fixes some issues with early releasing
        pg.mouseUp()

    def newGame(self) -> None:
        self.date = TAS.DAY_1
        self.story()
        self.click(NEW_BUTTON)
        self.startRun()
        time.sleep(MENU_DELAY + 1.5)
        pg.click(*self.mouseOffset(*INTRO_BUTTON), clicks = 11, interval = 0.05) # skip introduction
        time.sleep(MENU_DELAY)

    def waitForGiveAreaChange(self, *, update: bool = True, sleep: bool = True) -> None:
        self.frames.sleep(8) # the new version has some more movement frames that trip the give area change check
        super().waitForGiveAreaChange(update = update, sleep = sleep)