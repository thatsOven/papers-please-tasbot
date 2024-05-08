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

# **TODO**
# - if wanted is found and detain flag is true, interrogate and set transcription detainable flag to true
# - skip end menu fade on endings
# - check for end of day via day duration instead of using sleep button
# - figure out occasional parsing errors in transcription and text recognition rare bugs
# - make methods to handle special encounters in different ways
# - maybe make a simple scripting language for runs
# - ~~linux compatibility~~ (technically done but not quite. also not tested)

from PIL               import ImageGrab, ImageFont, Image
from pathlib           import Path
from deskew            import determine_skew
from datetime          import date, timedelta
from skimage.color     import rgb2gray
from skimage.transform import rotate
from typing            import Callable, ClassVar, Type, TYPE_CHECKING
import platform, time, os, sys, math, pyautogui as pg, numpy as np

from modules.constants.delays import *
from modules.constants.screen import *
from modules.constants.other  import *
from modules.utils            import *

from modules.textRecognition          import STATIC_OBJ, parseText, digitCheck, digitLength
from modules.faceRecognition          import Face
from modules.transcription            import Transcription
from modules.person                   import Person
from modules.frames                   import Frames
from modules.documentStack            import DocumentStack
from modules.documents.document       import Document, BaseDocument
from modules.documents.entryTicket    import EntryTicket
from modules.documents.entryPermit    import EntryPermit
from modules.documents.workPass       import WorkPass
from modules.documents.diplomaticAuth import DiplomaticAuth
from modules.documents.arstotzkanID   import ArstotzkanID
from modules.documents.idSupplement   import IDSupplement
from modules.documents.grantOfAsylum  import GrantOfAsylum
from modules.documents.accessPermit   import AccessPermit
from modules.documents.vaxCert        import VaxCert
from modules.documents.passport       import (
    City, Nation, Sex, PassportData, PassportType, Passport
)

import logging

logger = logging.getLogger('tas.' + __name__)

WINDOWS = platform.system() == "Windows"
if WINDOWS:
    import win32gui

if TYPE_CHECKING:
    from modules.run import Run

class TAS:
    SETTINGS: ClassVar[dict] = {
        "debug": True
    }

    DAY3_PICTURE_CHECK: ClassVar[bool]      = False
    DAY4_PICTURE_CHECK: ClassVar[bool]      = True 
    ID_CHECK: ClassVar[bool]                = True 
    APPEARANCE_HEIGHT_CHECK: ClassVar[bool] = True 

    # this is *really* slow, and wanted criminals don't happen that often,
    # so i'm keeping this off. it's not fully tested so enable at your own risk
    WANTED_CHECK: ClassVar[bool] = False

    PROGRAM_DIR: ClassVar[str] = str(Path(__file__).parent.absolute())
    RUNS_DIR: ClassVar[str]    = os.path.join(PROGRAM_DIR, "runs")
    ASSETS: ClassVar[str]      = os.path.join(PROGRAM_DIR, "assets")

    DAY_1: ClassVar[date]  = date(1982, 11, 23) # beginning
    DAY_2: ClassVar[date]  = date(1982, 11, 24) # we start actually checking documents
    DAY_3: ClassVar[date]  = date(1982, 11, 25) # needed for DAY3_PICTURE_CHECK
    DAY_5: ClassVar[date]  = date(1982, 11, 27) # detain
    DAY_7: ClassVar[date]  = date(1982, 11, 29) # search all kolechians
    DAY_11: ClassVar[date] = date(1982, 12,  3) # seal forgeries start appearing
    DAY_14: ClassVar[date] = date(1982, 12,  6) # wanted criminals
    DAY_18: ClassVar[date] = date(1982, 12, 10) # reason of denial stamp (ugh)
    DAY_19: ClassVar[date] = date(1982, 12, 11) # no entry from impor
    DAY_20: ClassVar[date] = date(1982, 12, 12) # poison
    DAY_24: ClassVar[date] = date(1982, 12, 16) # confiscate all altan district passports
    DAY_25: ClassVar[date] = date(1982, 12, 17) # no entry from united federation
    DAY_27: ClassVar[date] = date(1982, 12, 19) # rulebook changes
    DAY_28: ClassVar[date] = date(1982, 12, 20) # confiscate all arstotzkan passports
    DAY_29: ClassVar[date] = date(1982, 12, 21) # you can now confiscate and keep obristan passports

    DOCUMENTS: ClassVar[list[Type[Document]]]          = None
    MOA_SEALS: ClassVar[tuple[Image.Image, ...]]       = None
    PASSPORT_TYPES: ClassVar[tuple[PassportType, ...]] = None

    NEXT_BUBBLE: ClassVar[np.ndarray]            = None
    MATCHING_DATA: ClassVar[Image.Image]         = None
    MATCHING_DATA_LINES: ClassVar[Image.Image]   = None
    VISA_SLIP: ClassVar[Image.Image]             = None
    WEIGHT_BG: ClassVar[np.ndarray]              = None
    BUTTONS: ClassVar[dict[str, Image.Image]]    = None
    DOLLAR_SIGN: ClassVar[Image.Image]           = None
    WANTED_CRIMINALS: ClassVar[Image.Image]      = None
    NO_CORRELATION: ClassVar[Image.Image]        = None
    SCREW: ClassVar[Image.Image]                 = None
    WIRES: ClassVar[Image.Image]                 = None
    TRANQ_GUN_KEYHOLE: ClassVar[Image.Image]     = None
    SNIPER_KEYHOLE: ClassVar[Image.Image]        = None
    DARTS: ClassVar[Image.Image]                 = None
    BULLETS: ClassVar[Image.Image]               = None
    SEIZURE_SLIP: ClassVar[Image.Image]          = None
    TICKS: ClassVar[dict[str, Image.Image]]      = None
    GIVE_BANNER: ClassVar[Image.Image]           = None
    PASSPORT_KORDON_KALLO: ClassVar[Image.Image] = None
    CLOSE_BUTTON: ClassVar[Image.Image]          = None

    SEX_F_GENERIC: ClassVar[np.ndarray]  = None
    SEX_M_OBRISTAN: ClassVar[np.ndarray] = None

    FONTS: ClassVar[dict[str, ImageFont.FreeTypeFont | dict[str, np.ndarray]]] = None
    NAMES: ClassVar[dict[str, dict[Sex, set[str]]]]                            = None

    checkDayEnd: bool
    allowWrongWeight: bool
    wrongWeight: bool
    skipReason: bool
    needId: bool
    newData: bool
    poison: bool
    doConfiscate: bool
    confiscate: bool
    detain: bool
    skipGive: bool
    needObri: int
    shutter: bool
    sTime: float | None
    endingsTime: dict[int, float]
    lastGiveArea: np.ndarray | None
    wanted: list[tuple[int, int]]
    currRun: "Run"

    person:        Person
    documentStack: DocumentStack
    transcription: Transcription

    def __init__(self):
        pg.useImageNotFoundException(False)
        pg.PAUSE = 0.05

        if WINDOWS: self.hwnd   = None
        else:       self.winPos = None

        self.checkDayEnd = False

        self.allowWrongWeight = False
        self.wrongWeight      = False

        self.skipReason = False

        # TODO this system needs further testing but in the AllEndings run
        # this can only happen in days 25 and 27, and has an approximately 
        # 0.6% chance of happening with every entrant
        self.needId  = False
        self.newData = True

        self.poison       = False
        self.doConfiscate = True
        self.confiscate   = False
        self.detain       = False

        self.skipGive = False
        self.needObri = 0

        self.shutter      = False
        self.lastGiveArea = None
        self.date         = None

        self.sTime       = None
        self.endingsTime = {}

        self.wanted = []

        self.currRun = None
        
        self.frames        = Frames()
        self.person        = Person()
        self.documentStack = DocumentStack(self)
        self.transcription = Transcription(self)

        logger.info("Preparing generic assets...")
        TAS.NEXT_BUBBLE = np.asarray(Image.open(
            os.path.join(TAS.ASSETS, "nextBubble.png")
        ).convert("RGB"))

        TAS.MATCHING_DATA = Image.open(
            os.path.join(TAS.ASSETS, "matchingData.png")
        ).convert("RGB")
        TAS.MATCHING_DATA_LINES = Image.open(
            os.path.join(TAS.ASSETS, "matchingDataLines.png")
        ).convert("RGB")
        TAS.NO_CORRELATION = Image.open(
            os.path.join(TAS.ASSETS, "noCorrelation.png")
        ).convert("RGB")

        TAS.VISA_SLIP = np.asarray(doubleImage(Image.open(
            os.path.join(TAS.ASSETS, "papers", "VisaSlipInner.png")
        ).convert("RGB")))
        TAS.SEIZURE_SLIP = np.asarray(doubleImage(Image.open(
            os.path.join(TAS.ASSETS, "papers", "SeizureSlipInner.png")
        ).convert("RGB")))

        TAS.WEIGHT_BG = np.asarray(Image.open(
            os.path.join(TAS.ASSETS, "weightBG.png")
        ).convert("RGB"))
        TAS.DOLLAR_SIGN = Image.open(
            os.path.join(TAS.ASSETS, "dollarSign.png")
        ).convert("RGB")
        TAS.WANTED_CRIMINALS = Image.open(
            os.path.join(TAS.ASSETS, "wantedCriminals.png")
        ).convert("RGB")
        TAS.SCREW = Image.open(
            os.path.join(TAS.ASSETS, "screw.png")
        ).convert("RGB")
        TAS.TRANQ_GUN_KEYHOLE = Image.open(
            os.path.join(TAS.ASSETS, "tranqGunKeyHole.png")
        ).convert("RGB")
        TAS.SNIPER_KEYHOLE = Image.open(
            os.path.join(TAS.ASSETS, "sniperKeyHole.png")
        ).convert("RGB")
        TAS.DARTS = Image.open(
            os.path.join(TAS.ASSETS, "darts.png")
        ).convert("RGB")
        TAS.BULLETS = Image.open(
            os.path.join(TAS.ASSETS, "bullets.png")
        ).convert("RGB")
        TAS.GIVE_BANNER = Image.open(
            os.path.join(TAS.ASSETS, "give.png")
        ).convert("RGB")
        TAS.PASSPORT_KORDON_KALLO = Image.open(
            os.path.join(TAS.ASSETS, "passportKordonKallo.png")
        ).convert("RGB")
        TAS.CLOSE_BUTTON = Image.open(
            os.path.join(TAS.ASSETS, "closeButton.png")
        ).convert("RGB")

        wires = Image.open(
            os.path.join(TAS.ASSETS, "wires.png")
        ).convert("RGB")
        TAS.WIRES = wires.resize((wires.size[0] // 3 * 2, wires.size[1] // 3 * 2), Image.Resampling.NEAREST)

        sealsPath = os.path.join(TAS.ASSETS, "sealsMOA")
        TAS.MOA_SEALS = tuple(
            Image.open(os.path.join(sealsPath, file)).convert("RGB") 
            for file in os.listdir(sealsPath)
        )

        buttonsPath = os.path.join(TAS.ASSETS, "buttons")
        TAS.BUTTONS = {
            file.split(".")[0]: Image.open(os.path.join(buttonsPath, file)).convert("RGB") 
            for file in os.listdir(buttonsPath)
        }

        ticksPath = os.path.join(TAS.ASSETS, "ticks")
        TAS.TICKS = {
            file.split(".")[0]: Image.open(os.path.join(ticksPath, file)).convert("RGB") 
            for file in os.listdir(ticksPath)
        }

        # just the first two i got while taking screenshots
        # obristan needs different texture cause the passport has different text and bg colors
        TAS.SEX_F_GENERIC = np.asarray(Image.open(
            os.path.join(TAS.ASSETS, "passports", "sex", "f.png")
        ).convert("RGB"))
        TAS.SEX_M_OBRISTAN = np.asarray(Image.open(
            os.path.join(TAS.ASSETS, "passports", "sex", "m_obristan.png")
        ).convert("RGB"))

        TAS.FONTS = {
            "bm-mini": ImageFont.truetype( 
                os.path.join(TAS.ASSETS, "fonts", "BMmini.TTF"), 
                size = 16
            ),
            "mini-kylie": ImageFont.truetype( 
                os.path.join(TAS.ASSETS, "fonts", "MiniKylie.ttf"),
                size = 16
            ),
            "04b03": ImageFont.truetype(
                os.path.join(TAS.ASSETS, "fonts", "04B_03.TTF"),
                size = 16
            ),
            "digits": None
        }

        digits = doubleImage(Image.open(os.path.join(TAS.ASSETS, "fonts", "digits.png")).convert("RGB"))
        TAS.FONTS["digits"] = {
            str(c): np.asarray(digits.crop((x * DIGITS_LENGTH, 0, (x + 1) * DIGITS_LENGTH, DIGITS_HEIGHT)))
            for x, c in enumerate(DIGITS)
        }

        # TODO remove this once face recognition is ready
        TAS.NAMES = {
            "full":  {Sex.M: None, Sex.F: None},
            "first": {Sex.M: None, Sex.F: None},
            "last":  {Sex.M: None, Sex.F: None}
        }

        for fold in TAS.NAMES:
            for s in ("m", "f"):
                with open(os.path.join(TAS.ASSETS, "names", fold, f"{s}.txt"), "r") as f:
                    TAS.NAMES[fold][Sex(s == "f")] = set(x.strip() for x in f.read().splitlines())

        TAS.PASSPORT_TYPES = (
            PassportType(
                Nation.ANTEGRIA,
                os.path.join(TAS.ASSETS, "passports", "antegria"),
                (City.ST_MARMERO, City.GLORIAN, City.OUTER_GROUSE),
                PassportData(
                    name       = ( 16, 278, 246, 294),
                    birth      = ( 70, 202, 136, 214),
                    sex        = ( 50, 220,  60, 232),
                    city       = ( 50, 238, 164, 254),
                    expiration = ( 70, 256, 136, 268),
                    number     = ( 16, 298, 250, 310),
                    picture    = (166, 176, 246, 272),
                    label      = ( 16, 176, 136, 194)
                )
            ),
            PassportType(
                Nation.ARSTOTZKA,
                os.path.join(TAS.ASSETS, "passports", "arstotzka"),
                (City.ORVECH_VONOR, City.EAST_GRESTIN, City.PARADIZNA),
                PassportData(
                    name       = ( 16, 176, 249, 192),
                    birth      = (156, 196, 222, 208),
                    sex        = (136, 212, 146, 224),
                    city       = (136, 228, 252, 244),
                    expiration = (156, 244, 222, 256),
                    number     = ( 16, 296, 140, 308),
                    picture    = ( 16, 196,  96, 292),
                    label      = (158, 266, 246, 286)
                )
            ),
            PassportType(
                Nation.IMPOR,
                os.path.join(TAS.ASSETS, "passports", "impor"),
                (City.ENKYO, City.HAIHAN, City.TSUNKEIDO),
                PassportData(
                    name       = ( 14, 172, 249, 188),
                    birth      = (160, 194, 228, 206),
                    sex        = (140, 210, 150, 222),
                    city       = (140, 226, 244, 242),
                    expiration = (160, 242, 228, 254),
                    number     = ( 80, 292, 246, 304),
                    picture    = ( 18, 192,  98, 288),
                    label      = ( 20, 294,  80, 306)
                )
            ),
            PassportType(
                Nation.KOLECHIA,
                os.path.join(TAS.ASSETS, "passports", "kolechia"),
                (City.YURKO_CITY, City.VEDOR, City.WEST_GRESTIN),
                PassportData(
                    name       = ( 16, 196, 248, 212),
                    birth      = (158, 214, 224, 226),
                    sex        = (138, 230, 148, 242),
                    city       = (138, 246, 248, 262),
                    expiration = (158, 262, 224, 274),
                    number     = ( 99, 296, 251, 308),
                    picture    = ( 16, 214,  96, 310),
                    label      = ( 16, 172, 244, 190)
                )
            ),
            PassportType(
                Nation.OBRISTAN,
                os.path.join(TAS.ASSETS, "passports", "obristan"),
                (City.SKAL, City.LORNDAZ, City.MERGEROUS),
                PassportData(
                    name       = ( 16, 196, 248, 212),
                    birth      = ( 74, 222, 140, 234),
                    sex        = ( 54, 238,  64, 250),
                    city       = ( 54, 254, 162, 270),
                    expiration = ( 74, 270, 140, 282),
                    number     = ( 20, 296, 168, 308),
                    picture    = (168, 214, 248, 310),
                    label      = ( 14, 172, 250, 192)
                )
            ),
            PassportType(
                Nation.REPUBLIA,
                os.path.join(TAS.ASSETS, "passports", "republia"),
                (City.TRUE_GLORIAN, City.LESRENADI, City.BOSTAN),
                PassportData(
                    name       = ( 16, 174, 249, 190),
                    birth      = ( 74, 196, 140, 208),
                    sex        = ( 54, 212,  64, 224),
                    city       = ( 54, 228, 169, 244),
                    expiration = ( 74, 244, 140, 256),
                    number     = ( 16, 296, 253, 308),
                    picture    = (170, 192, 250, 288),
                    label      = ( 18, 272, 142, 288)
                )
            ),
            PassportType(
                Nation.UNITEDFED,
                os.path.join(TAS.ASSETS, "passports", "unitedFed"),
                (City.GREAT_RAPID, City.SHINGLETON, City.KORISTA_CITY),
                PassportData(
                    name       = ( 16, 196, 250, 212),
                    birth      = (158, 212, 225, 224),
                    sex        = (138, 228, 148, 240),
                    city       = (138, 244, 250, 260),
                    expiration = (158, 260, 225, 272),
                    number     = (100, 296, 253, 308),
                    picture    = ( 16, 212,  96, 308),
                    label      = ( 16, 174, 250, 190)
                )
            )
        )

        _defaultEq = relativedelta.__eq__
        def _customEq(self, other):
            if _defaultEq(self, PERMIT_DURATIONS["VALID"]) or _defaultEq(other, PERMIT_DURATIONS["VALID"]):
                return True
            return _defaultEq(self, other)
        relativedelta.__eq__ = _customEq

        TAS.DOCUMENTS = Document.__subclasses__()

        # this weird thing avoids circular imports
        STATIC_OBJ.BM_MINI    = TAS.FONTS["bm-mini"]
        STATIC_OBJ.MINI_KYLIE = TAS.FONTS["mini-kylie"]
        STATIC_OBJ._04B03     = TAS.FONTS["04b03"]

        Face.TAS          = TAS
        Passport.TAS      = TAS
        Document.TAS      = TAS
        BaseDocument.TAS  = TAS
        Transcription.TAS = TAS

        logger.info("Initializing face recognition system...")
        Face.load()
        logger.info("Initializing Transcription...")
        Transcription.load()
    
        for DocumentSubclass in TAS.DOCUMENTS:
            logger.info(f"Initializing {DocumentSubclass.__name__}...")
            DocumentSubclass.TAS = TAS
            DocumentSubclass.load()

        logger.info("TASBOT initialized!")

    @staticmethod
    def getWinPos() -> tuple[int, int]:
        pos = pg.locateOnScreen(TAS.CLOSE_BUTTON)
        if pos is None:
            raise TASException("Unable to get window position")
        return offsetPoint(tuple(pos), (-CLOSE_BUTTON_OFFSET[0], -CLOSE_BUTTON_OFFSET[1]))

    if WINDOWS:
        @staticmethod
        def getWinHWND() -> str:
            """Get the Windows handle for a currently open Papers Please window.

            Returns:
                Handle for the Papers Please window.

            Raises:
                TASException: If no matching window exists.
            """
            topList = []
            winList = []
            win32gui.EnumWindows(
                lambda h, _: winList.append((h, win32gui.GetWindowText(h))),
                topList
            )

            for h, t, in winList:
                if t in ("Papers Please", "PapersPlease"):
                    return h
                
            raise TASException('No "Papers Please" window was found')
        
        def getScreen(self) -> Image.Image:
            """Get a screenshot of the window in its current state.

            Returns:
                Screenshot of the window as an Image in RGB format.
            """
            return ImageGrab.grab(win32gui.GetWindowRect(self.hwnd)).convert("RGB")
        
        def mouseOffset(self, x: int, y: int) -> tuple[int, int]:
            """Converts point from window coordinates to screen coordinates."""
            bX, bY, _, _ = win32gui.GetWindowRect(self.hwnd)
            return (bX + x, bY + y)       
    else:
        @staticmethod
        def getWinHWND() -> str:
            raise NotImplementedError
        
        def getScreen(self) -> Image.Image:
            """Get a screenshot of the window in its current state.

            Returns:
                Screenshot of the window as an Image in RGB format.
            """
            return ImageGrab.grab(self.winPos + offsetPoint(WINDOW_SIZE, self.winPos)).convert("RGB")
        
        def mouseOffset(self, x: int, y: int) -> tuple[int, int]:
            """Converts point from window coordinates to screen coordinates."""
            return offsetPoint((x, y), self.winPos)

    def moveTo(self, at: tuple[int, int]) -> None:
        """Moves mouse to point given in window coordinates."""
        pg.moveTo(*self.mouseOffset(*at))

    def click(self, at: tuple[int, int]) -> None:
        """Click on the point given in window coordinates."""
        self.moveTo(at)
        pg.mouseDown()
        pg.mouseUp()

    def dragTo(self, at: tuple[int, int]) -> None:
        """Drags from the current mouse position to the point given in window coordinates and releases."""
        pg.mouseDown()
        self.moveTo(at)
        pg.mouseUp()

    def dragToWithGive(self, at: tuple[int, int]) -> None:
        """Drags from the current mouse position to the point given, but waits for a "Give" banner before releasing.

        After dragging to the given coordinates, waits for a "Give" banner to appear indicating that the entrant
        will accept a document dropped on them. While waiting, moves the mouse around in a small area near the given
        point to allow the give banner to move out from behind textboxes.
        """
        pg.mouseDown()
        self.moveTo(at)

        if self.skipGive: self.skipGive = False
        else:
            pos = list(at)
            th  = [0, 0]
            while True:
                screen = self.getScreen()
                if pg.locate(TAS.GIVE_BANNER, screen.crop(PERSON_AREA), confidence = 0.5) is not None: break

                # needed in some edge cases so it doesn't get stuck
                if self.checkDayEnd and pg.locate(TAS.BUTTONS["sleep"], screen) is not None: break 

                pos[0] = at[0] + math.sin(th[0]) * DRAG_TO_WITH_GIVE_AMPLITUDE[0] - DRAG_TO_WITH_GIVE_POS_OFFS[0]
                pos[1] = at[1] + math.sin(th[1]) * DRAG_TO_WITH_GIVE_AMPLITUDE[1] - DRAG_TO_WITH_GIVE_POS_OFFS[1]
                th[0] += DRAG_TO_WITH_GIVE_THETA_INC[0]
                th[1] += DRAG_TO_WITH_GIVE_THETA_INC[1]
                self.moveTo(pos)

        pg.mouseUp()

    def waitForAreaChange(self, area: tuple[int, int, int, int]) -> np.ndarray:
        """Wait for a change in the given screen area, continuously scanning that area of the screen.

        Args:
            area: The (left, top, right, bottom) of an area on the screen in window coordinates.

        Returns:
            The cropped screen image of the give area after a change is seen.
        """
        before = np.asarray(self.getScreen().crop(area))
        while np.array_equal(before, np.asarray(self.getScreen().crop(area))): pass
        return before

    def waitForGiveAreaChange(self, *, update: bool = True, sleep: bool = True) -> None:
        """Waits for a change in the "give area" of the screen.

        Continuously scans the give area of the screen (the counter on the left side of the booth where the entrant
        gives their documents), waiting for a change.

        Args:
            update: Whether to update lastGiveArea with the current cropped screen image after waiting.
            sleep: Whether to sleep for an additional 0.25 seconds after waiting.
        """
        if update: self.lastGiveArea = self.waitForAreaChange(GIVE_AREA)
        else:                          self.waitForAreaChange(GIVE_AREA)

        if sleep: time.sleep(0.25)

    def waitFor(self, button: Image.Image, *, move: bool = True) -> pg.Point:
        """Waits for the button image to appear on screen.

        Continuously scans the screen, waiting for the button image to be visible.

        Args:
            button: The image of a button to wait for.
            move: Whether to move the mouse to the upper-left corner of the screen at the start before waiting, to
                ensure it is not in the way of the button.

        Returns:
            The coordinates of the center of the button.
        """
        if move: self.moveTo((0, 0))
        while True:
            box = pg.locate(button, self.getScreen())
            if box is not None: return pg.center(box)

    def waitForSleepButton(self) -> None:
        """Waits for the sleep button to appear, then waits an additional 0.5 seconds."""
        self.waitFor(TAS.BUTTONS["sleep"])
        time.sleep(0.5)

    def goToWantedCriminals(self) -> None:
        """Turns the page of the bulletin until the wanted criminals page is seen."""
        while pg.locate(TAS.WANTED_CRIMINALS, self.getScreen()) is None:
            self.click(BULLETIN_NEXT_BUTTON)

    def openShutter(self, *, wait = True) -> None:
        if not self.shutter:
            self.shutter = True
            self.click(SHUTTER_LEVER)
        
        if wait:
            time.sleep(SHUTTER_OPEN_TIME)

    def closeShutter(self, *, wait = True) -> None:
        if self.shutter:
            self.shutter = False
            self.click(SHUTTER_LEVER)

        if wait:
            time.sleep(SHUTTER_OPEN_TIME)

    def nextPartial(self) -> bool:
        # TODO rewrite this doc to explain new behavior
        """Waits for a change in the areas outside the door, then clicks the horn. Does not wait for entrant's arrival.

        If "weight" is None, indicating this is the first entrant, prepares the bulletin, flipping to the wanted
        criminals change if "WANTED_CHECK" is True, or otherwise moving the bulletin to its slot on the left desk.
        If "checkHorn" is True, checks the area above the horn for the "Next" message bubble and waits for the end of
        day sleep button if it did not appear.
        Once the entrant arrives, saves a picture of them.

        Returns:
            True if the next entrant was called, False it waited for the sleep button.
        """

        # if weight is none, this is first person: no need to wait
        if self.person.weight is None:
            if TAS.WANTED_CHECK and self.date >= TAS.DAY_14:
                self.goToWantedCriminals()
                self.moveTo(INITIAL_BULLETIN_POS)
                self.dragTo(RIGHT_BULLETIN_POS)
                self.wanted = list(WANTED) 
            
            self.click(HORN)
            self.openShutter(wait = False) # make sure shutter is open so you can quickly detect first person
            self.moveTo(HORN) # move cursor away so face recognition doesn't get confused
        else:
            # waits for "next!" bubble to appear
            while True:
                self.click(HORN)
                screen = self.getScreen()

                if np.array_equal(TAS.NEXT_BUBBLE, np.asarray(screen.crop(NEXT_BUBBLE_AREA))): break
                if self.checkDayEnd and pg.locate(TAS.BUTTONS["sleep"], screen) is not None: return False 

        # wait for person to appear (if the palette is detected, the person is there)
        while True:
            screen = self.getScreen()
            appearance = screen.crop(PERSON_AREA)

            if Face.getPalette(appearance) is not None: break
            if self.checkDayEnd and pg.locate(TAS.BUTTONS["sleep"], screen) is not None: return False 

        self.documentStack.reset()
        self.transcription.reset()
        
        self.person.reset(appearance)

        if TAS.SETTINGS["debug"]: 
            # cool trick to get caller function name without the code being implementation-dependent
            try: raise Exception
            except Exception:
                caller = sys.exc_info()[2].tb_frame.f_back.f_code.co_name

            if caller != "next":
                logger.info(self.person.face)

        return True

    def next(self) -> bool:
        # TODO rewrite this doc to explain new behavior
        """Waits for a change in the areas outside the door, clicks the horn, and waits for documents to appear.

        If "weight" is None, indicating this is the first entrant, prepares the bulletin, flipping to the wanted
        criminals change if "WANTED_CHECK" is True, or otherwise moving the bulletin to its slot on the left desk.
        If "checkHorn" is True, checks the area above the horn for the "Next" message bubble and waits for the end of
        day sleep button if it did not appear.
        Once the entrant arrives, saves a picture of them, waits for them to present their documents, then records their weight.

        Returns:
            True if it waited for the sleep button, False if the next entrant was called.
        """
        if self.nextPartial():
            self.waitForGiveAreaChange()

            # this converts the colored image from the screenshot to an image with
            # black background and white text (so it's easier to compare to the digits' images)
            weight = np.asarray(self.getScreen().crop(WEIGHT_AREA)).copy()
            weight[(TAS.WEIGHT_BG != weight).all(axis = -1)] = (255, 255, 255)
            weight[(TAS.WEIGHT_BG == weight).all(axis = -1)] = (  0,   0,   0)
            weightCheck = parseText(
                Image.fromarray(weight), None, TAS.FONTS["digits"], None,
                DIGITS, checkFn = digitCheck, lenFn = digitLength
            )

            if weightCheck == "": 
                self.waitForSleepButton()
                return True
            
            self.person.weight = int(weightCheck)
            self.wrongWeight = False

            if TAS.SETTINGS["debug"]: logger.info(self.person) 
            return False
        
        return True

    # menu utilities
    def waitForAllTicks(self) -> None:
        """Waits for all ticks on the night screen to appear."""
        self.waitFor(TAS.DOLLAR_SIGN)
        self.moveTo((0, 0))

    def clickOnTick(self, tick: str) -> None:
        """Clicks on a tick on the night screen.

        Locates the given tick on the night screen and clicks on the center of it.

        Args:
            tick: The name of the tick to click.

        Raises:
            TypeError: If tick is not located on screen.
        """
        self.click((END_TICK_X, pg.center(pg.locate(TAS.TICKS[tick], self.getScreen())).y))

    def story(self) -> None:
        """Clicks the Story button on the main menu of the game."""
        self.click(STORY_BUTTON)
        time.sleep(MENU_DELAY)

    def startRun(self) -> None:
        """Starts the run timer."""
        self.sTime = time.time()

    def endingTime(self, endingN: int) -> float:
        """Gets the time since the run started and records it in the endingTime dictionary.

        Args:
            endingN: The ending number and the key of endingTime to record to.

        Returns:
            The current time since the run started.

        Raises:
            TASException: If the timer was never started.
        """
        if self.sTime is None:
            raise TASException("Timer was never started (tas.sTime is None)")

        t = time.time() - self.sTime
        self.endingsTime[endingN] = t
        return t

    def newGame(self) -> None:
        """Starts a new run from the main menu and clicks through the intro cutscene."""
        self.date = TAS.DAY_1
        self.story()
        self.click(NEW_BUTTON)
        self.startRun()
        time.sleep(MENU_DELAY)
        pg.click(*self.mouseOffset(*INTRO_BUTTON), clicks = 11, interval = 0.05) # skip introduction
        time.sleep(MENU_DELAY)

    def daySetup(self) -> None:
        """Sets up for the day by clicking "Walk to work" and setting flags to their default state."""
        self.click(INTRO_BUTTON)
        time.sleep(DAY_DELAY)
        self.person.reset()
        self.checkDayEnd      = False
        self.allowWrongWeight = False
        self.doConfiscate     = True
        self.shutter          = False
        self.wanted           = []

    def dayEnd(self) -> None:
        """Ends the day by clicking the sleep button and incrementing the date."""
        self.checkDayEnd = False
        self.click(SLEEP_BUTTON)
        time.sleep(MENU_DELAY)
        self.date += timedelta(days = 1)

    def restartFrom(self, day: tuple[int, int], date: date, story: bool = True) -> None:
        """Restarts from an earlier day by clicking on given coordinates for the save and setting the date.

        Args:
            day: The point to click for the day save in window coordinates.
            date: The date of the day to load.
            story: Whether to click the story button before the day save. Should be True if currently on the main menu.
        """
        if story: self.story()
        self.click(day)
        time.sleep(0.25)
        self.click(CONTINUE_BUTTON)
        time.sleep(MENU_DELAY)
        self.date = date

    # endings
    def ending(self, endingN: int, clicks: int, *, credits: bool = False) -> None:
        """Clicks the "Next" button until an ending cutscene is complete and returns to the main menu.

        Args:
            endingN: The ending number. Only used for logging and recording when the ending was completed.
            clicks: How many times to click "Next" in the ending.
            credits: Whether the ending has credits. Determines how it returns to the main menu.
        """
        for _ in range(clicks):
            self.waitFor(TAS.BUTTONS["next"])
            self.click(INTRO_BUTTON)

        logger.info(f"ENDING {endingN}: {str(timedelta(seconds = self.endingTime(endingN)))}")

        if credits:
            self.waitFor(TAS.BUTTONS["credits"])
            time.sleep(2)
            self.click(INTRO_BUTTON)

            pos = self.waitFor(TAS.BUTTONS["done"])
            time.sleep(1)
            self.click(pos)
        else:
            self.waitFor(TAS.BUTTONS["mainMenu"])
            time.sleep(2)
            self.click(INTRO_BUTTON)

        time.sleep(2)

    def ending1(self) -> None:
        """Completes ending 1 by clicking the Next button several times and returning to the main menu."""
        self.ending(1, 5)

    def ending2(self) -> None:
        """Completes ending 2 by clicking the Next button several times and returning to the main menu."""
        self.ending(2, 5)

    def ending3(self) -> None:
        """Completes ending 3 by clicking the Next button several times and returning to the main menu."""
        self.ending(3, 3)

    def ending4(self) -> None:
        """Completes ending 4 by clicking the Next button several times and returning to the main menu."""
        self.ending(4, 5)

    def ending5(self) -> None:
        """Completes ending 5 by clicking the Next button several times and returning to the main menu."""
        self.ending(5, 5)

    def ending6(self) -> None:
        """Completes ending 6 by clicking the Next button several times and returning to the main menu."""
        self.ending(6, 5)

    def ending7(self) -> None:
        """Completes ending 7 by clicking the Next button several times and returning to the main menu."""
        self.ending(7, 5)

    def ending8(self) -> None:
        """Completes ending 8 by clicking the Next button several times and returning to the main menu."""
        self.ending(8, 5)

    def ending9(self) -> None:
        """Completes ending 9 by clicking the Next button several times and returning to the main menu."""
        self.ending(9, 10)

    def ending10(self) -> None:
        """Completes ending 10 by clicking the Next button several times and returning to the main menu."""
        self.ending(10, 10)

    def ending11(self) -> None:
        """Completes ending 11 by clicking the Next button several times and returning to the main menu."""
        self.ending(11, 5)

    def ending12(self) -> None:
        """Completes ending 12 by clicking the Next button several times and returning to the main menu."""
        self.ending(12, 5)

    def ending13(self) -> None:
        """Completes ending 13 by clicking the Next button several times and returning to the main menu."""
        self.ending(13, 5)

    def ending14(self) -> None:
        """Completes ending 14 by clicking the Next button several times and returning to the main menu."""
        self.ending(14, 14)

    def ending15(self) -> None:
        """Completes ending 15 by clicking the Next button several times and returning to the main menu."""
        self.ending(15, 7)

    def ending16(self) -> None:
        """Completes ending 16 by clicking the Next button several times and returning to the main menu."""
        self.ending(16, 16)

    def ending17(self) -> None:
        """Completes ending 17 by clicking the Next button several times and returning to the main menu."""
        self.ending(17, 11)

    def ending18(self) -> None:
        """Completes ending 18 by clicking the Next button several times and returning to the main menu."""
        self.ending(18, 19, credits = True)

    def ending19(self) -> None:
        """Completes ending 19 by clicking the Next button several times and returning to the main menu."""
        self.ending(19, 7, credits = True)

    def ending20(self) -> None:
        """Completes ending 20 by clicking the Next button several times and returning to the main menu."""
        self.ending(20, 11, credits = True)

    # basic document handling utilities
    def handleConfiscate(self, pos: tuple[int, int], *, detain: bool = False) -> None:
        """Confiscates the passport depending on the state of the "confiscate" flag.

        Confiscates the passport if the "confiscate" flag is set and this is not running from within "noConfiscate()".
        If confiscating, sets the "confiscate" flag to False.

        Args:
            pos: The position of the passport in window coordinates.
            detain: Whether the entrant will be detained after confiscation. If False, moves the Visa slip to "pos".

        Raises:
            TASException: If the "confiscate" flag is True and current date is a day before day 24, making
                confiscation impossible.
        """
        if self.doConfiscate and self.confiscate:
            self.confiscate = False

            if self.date < TAS.DAY_24:
                raise TASException(f"Cannot confiscate on day {dateToDay(self.date)}")

            self.moveTo(pos)
            self.dragTo(PASSPORT_CONFISCATE_POS)
            time.sleep(PASSPORT_DRAWER_OPEN_TIME)

            self.click(PASSPORT_CONFISCATE_POS)
            time.sleep(max(CONFISCATE_SLIP_APPEAR_TIME, PASSPORT_DRAWER_CLOSE_TIME))

            if (not detain) and pos != PASSPORT_ALLOW_POS:
                self.moveTo(onTable(centerOf(VISA_SLIP_AREA)))
                self.dragTo(pos)

        if not detain: self.detain = False

    def handleConfiscateAndDetain(self, pos: tuple[int, int]) -> bool:
        """Confiscates the passport and detains depending on the states of the "confiscate" and "detain" flags.

        Confiscates the passport if the "confiscate" flag is set and this is not running from within "noConfiscate()".
        If confiscating, sets the "confiscate" flag to False, and if detaining, sets the "detain" flag to False.

        Args:
            pos: The position of the passport in window coordinates.

        Returns:
            Whether the entrant was detained.

        Raises:
            TASException: If the "confiscate" flag is True and current date is a day before day 24, making
                confiscation impossible, or the "detain" flag is True and current date is a day before day 5,
                making detention impossible.
        """
        self.handleConfiscate(pos, detain = self.detain)

        if self.detain:
            self.detain = False

            if self.date < TAS.DAY_5:
                raise TASException(f"Cannot detain on day {dateToDay(self.date)}")

            if self.transcription.waitFor(self.transcription.getDetainable):
                pos = self.waitFor(TAS.BUTTONS["detain"])
                time.sleep(0.5)
                self.click(pos)

                # shutter gets closed when you detain, so this ensures it stays open 
                # for the next entrant for quicker detection
                self.shutter = False
                self.openShutter(wait = False)

                self.documentStack.reset() # all documents disappear when you press detain
                return True
        return False

    def allowAndGive(self, *, close: bool = False, waitClose: bool = True) -> None:
        """Approves the entrant and returns their passport.

        Opens the stamp bar and presses the approval stamp, then returns the passport.
        If the "confiscate" flag is True, confiscates the passport before approval.

        Args:
            close: Whether to close the stamp bar after stamping.
            waitClose: Whether to wait for the stamp bar to finish closing before returning the passport.
                Ignored if "close" is False.
        """
        self.handleConfiscate(PASSPORT_ALLOW_POS)

        self.click(STAMP_ENABLE)
        time.sleep(STAMP_OPEN_TIME)
        self.click(STAMP_APPROVE)

        if close: 
            time.sleep(0.25)
            self.click(STAMP_DISABLE)
            if waitClose: time.sleep(STAMP_CLOSE_TIME)

        self.moveTo(PASSPORT_ALLOW_POS)
        self.dragToWithGive(PERSON_PASSPORT_POS)

    def denyAndGive(self, *, close: bool = False, waitClose: bool = True) -> None:
        """Denies the entrant and returns their passport.

        Opens the stamp bar and presses the deny stamp, then returns the passport.
        If the "confiscate" flag is True, confiscates the passport before denial.

        Args:
            close: Whether to close the stamp bar after stamping.
            waitClose: Whether to wait for the stamp bar to finish closing before returning the passport.
                Ignored if "close" is False.
        """
        self.handleConfiscate(PAPER_SCAN_POS)

        self.click(STAMP_ENABLE)
        time.sleep(STAMP_OPEN_TIME)
        self.click(STAMP_DENY)

        if close: 
            time.sleep(0.25)
            self.click(STAMP_DISABLE)
            if waitClose: time.sleep(STAMP_CLOSE_TIME)

        self.moveTo(PASSPORT_DENY_POS)
        self.dragToWithGive(PERSON_PASSPORT_POS)

    def passportOnlyAllow(self, *, nextCheck: bool = True) -> bool:
        """Takes the passport from the left counter, approves it, and returns it to the entrant.

        Args:
            nextCheck: Whether to call the next entrant and wait for their documents first.

        Returns:
            True if the entrant was approved, False if no next entrant was available, and it waited for the sleep
            button instead.
        """
        if nextCheck:
            if self.next(): return False

        self.moveTo(PAPER_POS)
        self.dragTo(PASSPORT_ALLOW_POS)
        self.allowAndGive()

        return True

    def passportOnlyDeny(self, *, nextCheck: bool = True) -> bool:
        """Takes the passport from the left counter, denies it, and returns it to the entrant.

        Args:
            nextCheck: Whether to call the next entrant and wait for their documents first.

        Returns:
            True if the entrant was denied, False if no next entrant was available, and it waited for the sleep
            button instead.
        """
        if nextCheck:
            if self.next(): return False
        
        self.moveTo(PAPER_POS)
        self.dragTo(PASSPORT_DENY_POS)
        self.denyAndGive()

        return True
    
    I = 0 # TODO

    def docScan(self, *, move: bool = True) -> Document | Passport | None:
        """Drags the next document from the left counter and scans it, returning the appropriate document object.


        Raises:
            TASException: If the "poison" flag is True and current date is not day 20, making poisoning impossible.
        """
        # take document screenshot
        before = np.asarray(self.getScreen().crop(TABLE_AREA))
        if move: self.moveTo(PAPER_POS)
        self.dragTo(PAPER_SCAN_POS)
        self.moveTo(PAPER_POS) # get cursor out of the way
        docImg, offs = isolateNew(before, np.asarray(self.getScreen().crop(TABLE_AREA)))

        # TODO
        # docImg.save(f"doc{TAS.I}.png")
        # TAS.I += 1

        for Document in TAS.DOCUMENTS:
            if Document.checkMatch(docImg):
                doc = Document(docImg, offs)

                if self.doConfiscate and self.currRun.confiscatePassportWhen(doc):
                    self.confiscate = True

                if TAS.SETTINGS["debug"]: logger.info(doc)
                return doc
            
        if self.poison:
            self.poison = False

            if self.date != TAS.DAY_20:
                raise TASException(f"Unable to use poison on day {dateToDay(self.date)}")

            self.moveTo(SLOTS[-1])
            self.dragTo(PAPER_SCAN_POS)

            # open poison
            self.click((820, 505))
            self.click((740, 400))
            self.click((670, 455))

            # drag over passport and apply
            self.dragTo((520, 355))
            self.click((790, 370))

            # put aside
            self.dragTo(SLOTS[-1])

        for passportType in TAS.PASSPORT_TYPES:
            if np.array_equal(np.asarray(docImg.crop(passportType.layout.label)), passportType.backgrounds.label):
                type_ = passportType
                break
        else: return None

        passport = Passport(docImg, offs, type_)

        if self.doConfiscate and self.currRun.confiscatePassportWhen(passport):
            self.confiscate = True

        if TAS.SETTINGS["debug"]: logger.info(passport)
        return passport
    
    def fastPassportScan(self, before: np.ndarray, after: np.ndarray) -> Nation:
        papers = np.asarray(bgFilter(before, after))
        gray   = rgb2gray(papers)

        for i in range(3): # tries no rotation, max 45 degree rotation, and max 90 degree rotation
            rotated = Image.fromarray(papers)

            if i != 0:
                skew = determine_skew(gray, angle_pm_90 = bool(i - 1))
                if skew is not None:
                    rotated = Image.fromarray((rotate(papers, skew, resize = True) * 255).astype(np.uint8))

            for passportType in TAS.PASSPORT_TYPES:
                if passportType.nation in (Nation.ANTEGRIA, Nation.UNITEDFED, Nation.OBRISTAN): continue # only used on day 1, and these passports can't appear
                if pg.locate(passportType.outerTexture, rotated, grayscale = False, confidence = 0.6) is not None:
                    return passportType.nation

    def interrogate(self) -> None:
        self.click(INTERROGATE_BUTTON)
        time.sleep(0.35) # otherwise it doesn't rly work 

    def getRulebook(self) -> dict[str, dict | tuple[int, int]]:
        if self.date < TAS.DAY_27:
            return RULEBOOK
        return RULEBOOK_DAY_27
    
    def interrogateFailsafe(self) -> bool:
        # we allow if we hit the failsafe in final check. 
        # might get citations, but whatever, it doesn't really happen.
        # it's just here to avoid problems

        time.sleep(INSPECT_ALPHACHANGE_TIME)
        before = np.asarray(self.getScreen().crop(TABLE_AREA))
        time.sleep(INSPECT_TIME - INSPECT_ALPHACHANGE_TIME)
        msg = bgFilter(before, np.asarray(self.getScreen().crop(TABLE_AREA)))

        if (
            pg.locate(TAS.MATCHING_DATA,  msg, confidence = 0.6) is None and
            pg.locate(TAS.NO_CORRELATION, msg, confidence = 0.6) is None
        ): return False
        
        self.click(INSPECT_BUTTON)
        return True

    def interrogateMissingDoc(self, rule: str) -> bool:
        self.moveTo(RULEBOOK_POS)
        self.dragTo(PAPER_SCAN_POS)
        self.click(self.getRulebook()["basic-rules"]["pos"])
        self.click(INSPECT_BUTTON)
        self.click(self.getRulebook()["basic-rules"][rule])
        self.click(NO_PASSPORT_CLICK_POS)

        cond = self.interrogateFailsafe()
        if not cond:
            time.sleep(INSPECT_INTERROGATE_TIME - INSPECT_TIME)
            self.interrogate()

        return cond

    def noPassport(self, *, backToIndex: bool = True) -> None:
        self.interrogateMissingDoc("entrants-must-have-passport")

        if backToIndex:
            self.click(RULEBOOK_BOOKMARK_BUTTON)

        self.moveTo(PAPER_SCAN_POS)
        self.dragTo(RULEBOOK_POS)

    def giveAllGiveAreaDocs(self, before: np.ndarray, *, delay: bool = False) -> None:
        while True: 
            screen = self.getScreen()

            if np.array_equal(before, np.asarray(screen.crop(GIVE_AREA))): break

            # needed in some edge cases so it doesn't get stuck
            if self.checkDayEnd and pg.locate(TAS.BUTTONS["sleep"], screen) is not None: break 
            
            self.moveTo(PAPER_POS)
            self.dragTo(PERSON_POS)
            if delay: time.sleep(0.5)

    def denyAndGiveWithReason(self, *, close: bool = False, waitClose: bool = True) -> None:
        if self.handleConfiscateAndDetain(PAPER_SCAN_POS): return

        self.click(STAMP_ENABLE)
        time.sleep(STAMP_OPEN_TIME)
        self.click(STAMP_DENY)

        self.moveTo(PAPER_SCAN_POS)
        self.dragTo(PASSPORT_REASON_POS)
        self.click(REASON_STAMP)

        if close: 
            time.sleep(0.25)
            self.click(STAMP_DISABLE)
            if waitClose: time.sleep(STAMP_CLOSE_TIME)

        self.moveTo(PASSPORT_REASON_POS)
        self.dragToWithGive(PERSON_PASSPORT_POS)   

    def passportCheck(self, before: np.ndarray, befCheck: bool, denyWhen: Callable[[Passport], bool]) -> bool:
        if denyWhen(self.documentStack.passport):
            cond = befCheck and not np.array_equal(before, np.asarray(self.getScreen().crop(GIVE_AREA)))

            # speedrun strategy - weight discrepancy: if we get a weight discrepancy after 
            # a specific entrant, on some days, bombers are randomly generated and can end day early
            if self.allowWrongWeight and self.wrongWeight:
                self.allowAndGive(
                    close = self.documentStack.mulDocs(),
                    waitClose = cond
                )
            elif self.date >= TAS.DAY_18 and not self.skipReason:
                self.denyAndGiveWithReason(
                    close = self.documentStack.mulDocs(),
                    waitClose = cond
                )
            else:
                self.skipReason = False

                self.denyAndGive(
                    close = self.documentStack.mulDocs(),
                    waitClose = cond
                )

            t = time.time()
            if cond: 
                self.giveAllGiveAreaDocs(before)
                if self.documentStack.mulDocs():
                    t = STAMP_CLOSE_TIME - (time.time() - t)
                    if t > 0: time.sleep(t)

            if self.documentStack.mulDocs(): self.giveAllDocs()
            return True
        return False
    
    def multiDocNoPassport(self, denyWhen: Callable[[Passport], bool], forceAllow: bool = False) -> bool:
        if self.documentStack.passport is None:
            before = np.asarray(self.getScreen().crop(GIVE_AREA))
            self.noPassport()
            
            while True:
                screen = self.getScreen()
                if not np.array_equal(before, np.asarray(screen.crop(GIVE_AREA))): break

                if pg.locate(TAS.VISA_SLIP, screen, confidence = 0.9) is not None:
                    time.sleep(0.25)

                    if not forceAllow: 
                        self.moveTo(onTable(centerOf(VISA_SLIP_AREA)))
                        self.dragTo(VISA_SLIP_DENY_POS)
                    
                    self.click(STAMP_ENABLE)
                    time.sleep(STAMP_OPEN_TIME)

                    if forceAllow: 
                        self.click(STAMP_APPROVE)
                    else:          
                        self.click(STAMP_DENY)

                        if self.date >= TAS.DAY_18 and not self.skipReason:
                            self.moveTo(VISA_SLIP_DENY_POS)
                            self.dragTo(PASSPORT_REASON_POS)
                            self.click(REASON_STAMP)

                    if len(self.documentStack) != 0:
                        time.sleep(0.25)
                        self.click(STAMP_DISABLE)
                        wait = True
                    else: wait = False

                    t = time.time()
                    self.giveAllGiveAreaDocs(before)

                    if   forceAllow:                                      self.moveTo(VISA_SLIP_ALLOW_POS)
                    elif self.date >= TAS.DAY_18 and not self.skipReason: self.moveTo(PASSPORT_REASON_POS)
                    else:                                                 self.moveTo(VISA_SLIP_DENY_POS)

                    self.dragToWithGive(PERSON_PASSPORT_POS)

                    if wait:
                        t = STAMP_CLOSE_TIME - (time.time() - t)
                        if t > 0: time.sleep(t)

                    self.giveAllDocs()
                    return True

            time.sleep(0.5)
            self.moveTo(PAPER_POS)
            doc = self.docScan(move = False)
            self.documentStack.passport = doc
            self.moveTo(PAPER_SCAN_POS)
            if self.passportCheck(before, False, denyWhen):
                return True
        return False
    
    def checkDiscrepancies(self, doc: Document | Passport) -> bool:
        return getattr(self.currRun, f"check{type(doc).__name__}Discrepancies")(doc)

    def getAllDocs(self, *, nextCheck: bool = True) -> tuple[bool, bool]:
        if nextCheck:
            if self.next(): return True, False
        else:
            self.documentStack.reset()
            self.transcription.reset()
            
        discrepancy = False
        while True:
            self.moveTo(PAPER_POS)
            doc: Document | Passport = self.docScan(move = False)
            self.moveTo(PAPER_SCAN_POS)

            if type(doc) is Passport:
                self.documentStack.passport = doc

                if self.needId:
                    discrepancy |= self.checkDiscrepancies(doc)
                elif self.passportCheck(
                    self.lastGiveArea, True, 
                    lambda x: discrepancy or self.checkDiscrepancies(x)
                ): return False, True

                if np.array_equal(self.lastGiveArea, np.asarray(self.getScreen().crop(GIVE_AREA))): break

                self.documentStack.push(doc)
            else:
                if (discrepancy and self.needId) or ((not discrepancy) and doc is not None and self.checkDiscrepancies(doc)):
                    if type(doc) is ArstotzkanID:
                        self.needId = False

                    if self.documentStack.passport is None or self.needId: discrepancy = True
                    else:
                        self.documentStack.push(doc)
                        self.moveTo(SLOTS[0])

                        # check "speedrun strategy - weight discrepancy"
                        if self.allowWrongWeight and self.wrongWeight: 
                            self.dragTo(PASSPORT_ALLOW_POS)
                            self.allowAndGive(close = True, waitClose = False)
                        else:     
                            self.dragTo(PASSPORT_DENY_POS)

                            if self.date >= TAS.DAY_18 and not self.skipReason: 
                                self.denyAndGiveWithReason(close = True, waitClose = False)
                            else: 
                                self.skipReason = False
                                self.denyAndGive(close = True, waitClose = False)
                            
                        t = time.time()
                        self.giveAllGiveAreaDocs(self.lastGiveArea)
                        t = STAMP_CLOSE_TIME - (time.time() - t)
                        if t > 0: time.sleep(t)

                        self.giveAllDocs()
                        return False, True
                elif type(doc) is ArstotzkanID: self.needId = False

                self.documentStack.push(doc)

                if np.array_equal(self.lastGiveArea, np.asarray(self.getScreen().crop(GIVE_AREA))): break

        self.needId = False
        return False, self.multiDocNoPassport(
            lambda x: discrepancy or self.checkDiscrepancies(x), 
        )
    
    def noConfiscate(self, fn: Callable):
        tmp = self.doConfiscate
        self.doConfiscate = False
        res = fn()
        self.doConfiscate = tmp
        return res
    
    def multiDocAction(self, allow: bool, *, nextCheck: bool = True, force: bool = False) -> bool:
        if nextCheck:
            if self.next(): return True

        self.documentStack.reset()
        while True:
            self.moveTo(PAPER_POS)
            doc = self.noConfiscate(lambda: self.docScan(move = False))
            self.moveTo(PAPER_SCAN_POS)

            if type(doc) is Passport:
                if allow:
                    self.dragTo(PASSPORT_ALLOW_POS)
                    self.allowAndGive(close = self.documentStack.mulDocs())
                else:
                    self.denyAndGive(close = self.documentStack.mulDocs())

                if not np.array_equal(self.lastGiveArea, np.asarray(self.getScreen().crop(GIVE_AREA))): 
                    self.giveAllGiveAreaDocs(self.lastGiveArea)

                if self.documentStack.mulDocs(): self.giveAllDocs()
                return False
            
            self.documentStack.push(doc)

            if np.array_equal(self.lastGiveArea, np.asarray(self.getScreen().crop(GIVE_AREA))): break
        
        if self.multiDocNoPassport(lambda _: not allow, forceAllow = force and allow): return
        
        self.dragTo(PASSPORT_ALLOW_POS)
        self.allowAndGive(close = self.documentStack.mulDocs())
        if not np.array_equal(self.lastGiveArea, np.asarray(self.getScreen().crop(GIVE_AREA))): 
            self.giveAllGiveAreaDocs(self.lastGiveArea)
        if self.documentStack.mulDocs(): self.giveAllDocs()
        return False
    
    def giveAllDocs(self) -> None:
        while self.documentStack.pop() is not None: pass
        self.documentStack.reset()

    def compareDocs(self, leftPos: int, rightPos: int, moved: bool = True) -> None:
        self.moveTo(SLOTS[rightPos])
        if leftPos < 2: # the click will interfere with document we just placed
            self.dragTo(SLOTS[-1])
        else:
            self.dragTo(RIGHT_SCAN_SLOT)

        if moved: self.moveTo(SLOTS[leftPos])
        self.dragTo(LEFT_SCAN_SLOT)

        if leftPos < 2:
            self.moveTo(SLOTS[-1])
            self.dragTo(RIGHT_SCAN_SLOT)

        self.click(INSPECT_BUTTON)

    def comparePassportAndDoc(self, pos: int) -> None:
        self.compareDocs(0, pos, self.documentStack.moved)

    def putCompareDocsBack(self, leftPos: int, rightPos: int) -> None:
        self.moveTo(RIGHT_SCAN_SLOT)
        self.dragTo(SLOTS[rightPos])

        self.moveTo(LEFT_SCAN_SLOT)
        self.dragTo(SLOTS[leftPos])

    def interrogateAndDeny(self, leftPos: int, rightPos: int, delaySub: float = 0) -> None:
        time.sleep(INSPECT_INTERROGATE_TIME - delaySub)
        self.interrogate()

        self.putCompareDocsBack(leftPos, rightPos)

        self.moveTo(SLOTS[0])
        self.dragTo(PASSPORT_DENY_POS)
        self.denyAndGiveWithReason(close = True)

    def interrogateAndDenyWithPassport(self, pos: int, delaySub: float = 0) -> None:
        time.sleep(INSPECT_INTERROGATE_TIME - delaySub)
        self.interrogate()

        self.moveTo(RIGHT_SCAN_SLOT)
        if pos < 3:
            self.dragTo(SLOTS[-1])
        else:
            self.dragTo(SLOTS[pos])

        self.moveTo(LEFT_SCAN_SLOT)
        self.dragTo(PASSPORT_DENY_POS)
        self.denyAndGiveWithReason(close = True)

        if pos < 3:
            self.moveTo(SLOTS[-1])
            self.dragTo(SLOTS[pos])

    def allowWithPassport(self, pos: int) -> None:
        self.moveTo(RIGHT_SCAN_SLOT)
        if pos < 3:
            self.dragTo(SLOTS[-1])
        else:
            self.dragTo(SLOTS[pos])

        self.moveTo(LEFT_SCAN_SLOT)
        self.dragTo(PASSPORT_ALLOW_POS)
        self.allowAndGive(close = True)

        if pos < 3:
            self.moveTo(SLOTS[-1])
            self.dragTo(SLOTS[pos])

    def putRulebookBack(self) -> None:
        self.click(RULEBOOK_BOOKMARK_BUTTON)
        self.moveTo(PAPER_SCAN_POS)
        self.dragTo(RULEBOOK_POS)

    def missingDoc(self, rule: str, Type_: Type[Document]) -> bool:
        self.interrogateMissingDoc(rule)
        self.putRulebookBack()

        if self.newData:
            tmp = self.lastGiveArea
            self.lastGiveArea = np.asarray(self.getScreen().crop(GIVE_AREA))

            if not self.documentStack.moved:
                self.documentStack.moved = True
                self.moveTo(PAPER_SCAN_POS)
                self.dragTo(SLOTS[0])
            
            if self.transcription.waitFor(lambda: self.transcription.getMissingDocGiven(Type_.__name__)):
                self.waitForGiveAreaChange(update = False)
                doc = self.docScan()

                discrepancy = self.checkDiscrepancies(doc)
                self.moveTo(PAPER_SCAN_POS)
                self.documentStack.push(doc)
                if not discrepancy: 
                    self.lastGiveArea = tmp
                    return False
            
            self.lastGiveArea = tmp
                
        if self.documentStack.moved:
            self.moveTo(SLOTS[0])
            self.dragTo(PASSPORT_DENY_POS)

        self.denyAndGiveWithReason(close = True)
        self.giveAllDocs()
        self.giveAllGiveAreaDocs(self.lastGiveArea)
        return True

    # guns and attacks
    def getTranqGun(self) -> None:
        # wait for keyhole
        while pg.locate(TAS.TRANQ_GUN_KEYHOLE, self.getScreen()) is None: pass
        time.sleep(0.5)
        # open rifle
        self.moveTo(SLOTS[-1])
        self.dragTo(TRANQ_GUN_ENABLE_KEY_POS)
        # wait for darts
        while pg.locate(TAS.DARTS, self.getScreen().crop(TABLE_AREA)): pass
        time.sleep(GUN_BULLETS_APPEAR_TIME)
        # click on darts
        self.click(pg.center(pg.locate(TAS.DARTS, self.getScreen())))

    def getSniper(self) -> None:
        # wait for keyhole
        while pg.locate(TAS.SNIPER_KEYHOLE, self.getScreen()) is None: pass
        time.sleep(0.5)
        # open rifle
        self.moveTo(SLOTS[-1])
        self.dragTo(SNIPER_ENABLE_KEYPOS)
        # wait for bullets
        while pg.locate(TAS.BULLETS, self.getScreen().crop(TABLE_AREA)): pass
        time.sleep(GUN_BULLETS_APPEAR_TIME)
        # click on bullets
        self.click(pg.center(pg.locate(TAS.BULLETS, self.getScreen())))

    def detectPeople(self, area: tuple[int, int, int, int], *, tranq: bool = False) -> tuple[tuple[int, int], ...]:
        ys, xs = np.where((np.asarray(self.getScreen().crop(area)) == PEOPLE_COLOR).all(axis = -1))
        if tranq:
            return (
                offsetPoint((xs[0           ], ys[0           ]), area[:2]), 
                offsetPoint((xs[len(xs) // 2], ys[len(ys) // 2]), area[:2]), 
                offsetPoint((xs[-1          ], ys[-1          ]), area[:2])
            )
        else:
            return (
                offsetPoint((xs[ 0], ys[ 0]), area[:2]), 
                offsetPoint((xs[-1], ys[-1]), area[:2])
            )
        
    def day15Bomb(self) -> None:
        # bomb on desk
        self.next()
        self.moveTo(PAPER_POS)
        self.dragTo(PAPER_SCAN_POS)
        # wait for screws
        while pg.locate(TAS.SCREW, self.getScreen().crop(TABLE_AREA)) is None: pass
        time.sleep(0.25)
        # unscrew
        self.click((695, 405))
        self.click((810, 405))
        self.click((695, 490))
        self.click((810, 490))
        # wait for wires and calensk
        while pg.locate(TAS.WIRES, self.getScreen().crop(TABLE_AREA)) is None: pass
        while pg.locate(TAS.WIRES, self.getScreen().crop(TABLE_AREA)) is not None:
            # try to cut first wire
            self.click((735, 440))
            self.moveTo(TABLE_AREA[:2])
        # when cutting first wire succeeds, wires is no longer located, 
        # so it falls here and cuts all other wires
        self.click((688, 440))
        self.click((816, 440))
        self.click((770, 440))
        # give bomb to calensk
        self.dragTo(PAPER_POS)
        self.giveAllGiveAreaDocs(self.lastGiveArea, delay = True)

    # document handling
    def handleNoDocs(self) -> bool:
        if len(self.documentStack) == 0:
            if self.documentStack.moved: 
                self.moveTo(SLOTS[0])
                self.dragTo(PASSPORT_DENY_POS)

            self.denyAndGive(close = False)
            return True
        return False

    def handleArstotzkanId(self) -> bool:
        if self.documentStack.passport.type_.nation == Nation.ARSTOTZKA:
            arstotzkanId: ArstotzkanID = self.documentStack.get(ArstotzkanID)

            if self.documentStack.moved: self.moveTo(SLOTS[0])
            if arstotzkanId is None or (
                arstotzkanId.birth != self.documentStack.passport.birth or
                arstotzkanId.name  != self.documentStack.passport.name
            ):
                if self.documentStack.moved: self.dragTo(PASSPORT_DENY_POS)
                self.denyAndGive(close = True)
            else:
                self.dragTo(PASSPORT_ALLOW_POS)
                self.allowAndGive(close = True)
            
            self.giveAllDocs()
            return True
        return False
    
    def handleEntryPermit(self) -> bool:
        entryPermit: EntryPermit = self.documentStack.get(EntryPermit)

        if entryPermit is None or (
            entryPermit.name   != self.documentStack.passport.name   or
            entryPermit.number != self.documentStack.passport.number        
        ):
            if self.documentStack.moved:
                self.moveTo(SLOTS[0]) 
                self.dragTo(PASSPORT_DENY_POS)

            self.denyAndGive(close = True)
            self.giveAllDocs()
            return True
        return False
    
    def handlePurposeDuration(self) -> bool:
        entryPermit: EntryPermit = self.documentStack.get(EntryPermit)

        duration = self.transcription.waitFor(self.transcription.getDuration)
        purpose  = self.transcription.getPurpose()

        if self.documentStack.moved: self.moveTo(SLOTS[0])
        if (
            entryPermit.purpose  != purpose or
            entryPermit.duration != duration
        ):
            if self.documentStack.moved: self.dragTo(PASSPORT_DENY_POS)
            self.denyAndGive(close = True)
            self.giveAllDocs()
            return True
        return False
    
    def handleWorkPass(self) -> bool:
        entryPermit: EntryPermit = self.documentStack.get(EntryPermit)

        if entryPermit.purpose == Purpose.WORK:
            workPass: WorkPass = self.documentStack.get(WorkPass)

            if workPass is None or (
                workPass.name != self.documentStack.passport.name or
                workPass.until < self.date + entryPermit.duration
            ):
                if self.documentStack.moved:
                    self.moveTo(SLOTS[0]) 
                    self.dragTo(PASSPORT_DENY_POS)

                self.denyAndGive(close = True)
                self.giveAllDocs()
                return True
        return False

    def handleDiplomaticAuth(self) -> bool:
        diplomaticAuth: DiplomaticAuth = self.documentStack.get(DiplomaticAuth)
        if diplomaticAuth is None: return False

        if self.documentStack.moved: self.moveTo(SLOTS[0])
        if (
            diplomaticAuth.name   != self.documentStack.passport.name   or
            diplomaticAuth.number != self.documentStack.passport.number or
            diplomaticAuth.nation != self.documentStack.passport.type_.nation
        ):
            if self.documentStack.moved: self.dragTo(PASSPORT_DENY_POS)
            self.denyAndGive(close = True)
        else:
            self.dragTo(PASSPORT_ALLOW_POS)
            self.allowAndGive(close = True)
        self.giveAllDocs()
        return True
    
    def handleIdSuppl(self) -> bool:
        idSupplement: IDSupplement = self.documentStack.get(IDSupplement)

        if idSupplement is None:
            if self.documentStack.moved:
                self.moveTo(SLOTS[0]) 
                self.dragTo(PASSPORT_DENY_POS)

            self.denyAndGive(close = True)
            self.giveAllDocs()
            return True
        return False
    
    def handleArstotzkanIdWithReason(self) -> bool:
        if self.documentStack.passport.type_.nation == Nation.ARSTOTZKA:
            arstotzkanId: ArstotzkanID = self.documentStack.get(ArstotzkanID)

            if arstotzkanId is None and self.missingDoc("citizens-must-have-id", ArstotzkanID):
                return True
            
            arstotzkanId    = self.documentStack.get(ArstotzkanID)
            arstotzkanIdPos = self.documentStack.getSlot(ArstotzkanID)

            birthDiscrepancy = arstotzkanId.birth != self.documentStack.passport.birth
            nameDiscrepancy  = arstotzkanId.name  != self.documentStack.passport.name

            if birthDiscrepancy or nameDiscrepancy:
                self.comparePassportAndDoc(arstotzkanIdPos)

                if birthDiscrepancy:
                    self.click(onTable(textFieldOffset(rightSlot(arstotzkanId.getTableBox("birth")[:2]))))
                    self.click(onTable(textFieldOffset(leftSlot(self.documentStack.passport.getTableBox("birth")[:2]))))
                else:
                    self.click(onTable(textFieldOffset(rightSlot(arstotzkanId.getTableBox("last-name")[:2]))))
                    self.click(onTable(textFieldOffset(leftSlot(self.documentStack.passport.getTableBox("name")[:2]))))

                if self.interrogateFailsafe():
                    self.allowWithPassport(arstotzkanIdPos)
                else:
                    self.interrogateAndDenyWithPassport(arstotzkanIdPos, INSPECT_TIME)
                self.giveAllDocs()
            else:
                if self.documentStack.moved: self.moveTo(SLOTS[0])
                self.dragTo(PASSPORT_ALLOW_POS)
                self.allowAndGive(close = True)
                self.giveAllDocs()

            return True
        
    def handleDiplomaticAuthWithReason(self) -> bool:
        diplomaticAuth: DiplomaticAuth = self.documentStack.get(DiplomaticAuth)
        if diplomaticAuth is None: return False

        diplomaticAuthPos = self.documentStack.getSlot(DiplomaticAuth)

        nameDiscrepancy   = diplomaticAuth.name   != self.documentStack.passport.name
        numberDiscrepancy = diplomaticAuth.number != self.documentStack.passport.number
        nationDiscrepancy = diplomaticAuth.nation != self.documentStack.passport.type_.nation

        if nameDiscrepancy or numberDiscrepancy or nationDiscrepancy:
            self.comparePassportAndDoc(diplomaticAuthPos)

            if nameDiscrepancy:
                self.click(onTable(rightSlot(centerOf(diplomaticAuth.getTableBox("name")))))
                self.click(onTable(textFieldOffset(leftSlot(self.documentStack.passport.getTableBox("name")[:2]))))
            elif numberDiscrepancy:
                self.click(onTable(rightSlot(centerOf(diplomaticAuth.getTableBox("number")))))
                self.click(onTable(leftSlot(self.documentStack.passport.getNumberClick())))
            else:
                self.click(onTable(textFieldOffset(rightSlot(diplomaticAuth.getTableBox("nation")[:2]))))
                self.click(onTable(leftSlot(centerOf(self.documentStack.passport.getTableBox("label")))))

            if self.interrogateFailsafe():
                self.allowWithPassport(diplomaticAuthPos)
            else:
                self.interrogateAndDenyWithPassport(diplomaticAuthPos, INSPECT_TIME)
        else:
            if self.documentStack.moved: self.moveTo(SLOTS[0])
            self.dragTo(PASSPORT_ALLOW_POS)
            self.allowAndGive(close = True)
        self.giveAllDocs()
        return True
    
    def handleEntryPermitWithReason(self) -> bool:
        entryPermit: EntryPermit = self.documentStack.get(EntryPermit)

        if entryPermit is None and self.missingDoc("foreigners-require-entry-permit", EntryPermit):
            return True
        
        entryPermit    = self.documentStack.get(EntryPermit)
        entryPermitPos = self.documentStack.getSlot(EntryPermit)

        nameDiscrepancy   = entryPermit.name   != self.documentStack.passport.name
        numberDiscrepancy = entryPermit.number != self.documentStack.passport.number

        if nameDiscrepancy or numberDiscrepancy:
            self.comparePassportAndDoc(entryPermitPos)

            if nameDiscrepancy:
                self.click(onTable(rightSlot(centerOf(entryPermit.getTableBox("name")))))
                self.click(onTable(textFieldOffset(leftSlot(self.documentStack.passport.getTableBox("name")[:2]))))
            else:
                self.click(onTable(rightSlot(centerOf(entryPermit.getTableBox("number")))))
                self.click(onTable(leftSlot(self.documentStack.passport.getNumberClick())))

            if self.interrogateFailsafe():
                self.allowWithPassport(entryPermitPos)
            else:
                self.interrogateAndDenyWithPassport(entryPermitPos, INSPECT_TIME)
            self.giveAllDocs()
            return True
        return False
        
    def handleWorkPassWithReason(self, PermitType: type) -> bool:
        permit: EntryPermit | AccessPermit = self.documentStack.get(PermitType)

        if permit.purpose == Purpose.WORK:
            workPass: WorkPass = self.documentStack.get(WorkPass)

            if workPass is None and self.missingDoc("workers-must-have-workpass", WorkPass):
                return True
            
            workPass    = self.documentStack.get(WorkPass)
            workPassPos = self.documentStack.getSlot(WorkPass)

            nameDiscrepancy     = workPass.name != self.documentStack.passport.name
            durationDiscrepancy = workPass.until < self.date + permit.duration

            if nameDiscrepancy:
                self.comparePassportAndDoc(workPassPos)
                self.click(onTable(rightSlot(centerOf(workPass.getTableBox("name")))))
                self.click(onTable(textFieldOffset(leftSlot(self.documentStack.passport.getTableBox("name")[:2]))))

                if self.interrogateFailsafe():
                    self.allowWithPassport(workPassPos)
                else:
                    self.interrogateAndDenyWithPassport(workPassPos, INSPECT_TIME)
                self.giveAllDocs()
                return True
            elif durationDiscrepancy:
                self.moveTo(SLOTS[workPassPos])
                self.dragTo(PAPER_SCAN_POS)

                self.click(INSPECT_BUTTON)
                self.click(centerOf(workPass.getTableBox("until")))
                self.click(CLOCK_POS)

                if self.interrogateFailsafe():
                    self.moveTo(PAPER_SCAN_POS)
                    self.dragTo(SLOTS[workPassPos])

                    if self.documentStack.moved: self.moveTo(SLOTS[0])
                    else:                        self.moveTo(PAPER_SCAN_POS)

                    self.dragTo(PASSPORT_ALLOW_POS)
                    self.allowAndGive(close = True)
                else:
                    time.sleep(INSPECT_INTERROGATE_TIME - INSPECT_TIME)
                    self.interrogate()

                    self.moveTo(PAPER_SCAN_POS)
                    self.dragTo(SLOTS[workPassPos])

                    if self.documentStack.moved: 
                        self.moveTo(SLOTS[0])
                        self.dragTo(PASSPORT_DENY_POS)

                    self.denyAndGiveWithReason(close = True)
                self.giveAllDocs()
                return True
        return False
    
    def handleIdSupplWithReason(self) -> bool:
        idSupplement: IDSupplement = self.documentStack.get(IDSupplement)

        if idSupplement is None and self.missingDoc("foreigners-require-idsuppl", IDSupplement):
            return True
        return False
    
    def handlePurposeDurationWithReason(self, PermitType: Type[EntryPermit | AccessPermit], alignFn: Callable[[tuple[int, int, int, int]], tuple[int, int]]) -> bool:
        duration = self.transcription.waitFor(self.transcription.getDuration)
        purpose  = self.transcription.getPurpose()

        permit: EntryPermit | AccessPermit = self.documentStack.get(PermitType)

        purposeDiscrepancy  = permit.purpose  != purpose
        durationDiscrepancy = permit.duration != duration

        if purposeDiscrepancy or durationDiscrepancy:
            purposePos  = self.transcription.getPurposePos()
            durationPos = self.transcription.getDurationPos()

            permitPos = self.documentStack.getSlot(PermitType)

            self.moveTo(SLOTS[permitPos])
            self.dragTo(RIGHT_SCAN_SLOT)

            self.moveTo(TRANSCRIPTION_POS)
            self.dragTo(LEFT_SCAN_SLOT)

            self.click(INSPECT_BUTTON)

            if purposeDiscrepancy:
                self.click(onTable(textFieldOffset(leftSlot(purposePos[:2]))))
                self.click(onTable(rightSlot(alignFn(permit.getTableBox("purpose")))))
            else:
                self.click(onTable(textFieldOffset(leftSlot(durationPos[:2]))))
                self.click(onTable(rightSlot(alignFn(permit.getTableBox("duration")))))

            if not self.interrogateFailsafe():
                time.sleep(INSPECT_INTERROGATE_TIME - INSPECT_TIME)
                self.interrogate()

            self.moveTo(LEFT_SCAN_SLOT)
            self.dragTo(TRANSCRIPTION_POS)

            self.moveTo(RIGHT_SCAN_SLOT)
            self.dragTo(SLOTS[permitPos])

        if self.documentStack.moved: 
            self.moveTo(SLOTS[0])
        else:
            self.moveTo(PAPER_SCAN_POS)    

        self.dragTo(PASSPORT_ALLOW_POS)
        self.allowAndGive(close = True) # entrants always correct themselves on wrong purposes or durations
        self.giveAllDocs()
        return True
    
    def handleGrantOfAsylumWithReason(self) -> bool:
        grantOfAsylum: GrantOfAsylum = self.documentStack.get(GrantOfAsylum)

        if grantOfAsylum is None and self.missingDoc("asylum-seekers-need-grant", GrantOfAsylum):
            return True
        
        grantOfAsylum    = self.documentStack.get(GrantOfAsylum)
        grantOfAsylumPos = self.documentStack.getSlot(GrantOfAsylum)

        nameDiscrepancy   = grantOfAsylum.name   != self.documentStack.passport.name
        numberDiscrepancy = grantOfAsylum.number != self.documentStack.passport.number
        nationDiscrepancy = grantOfAsylum.nation != self.documentStack.passport.type_.nation
        birthDiscrepancy  = grantOfAsylum.birth  != self.documentStack.passport.birth

        if nameDiscrepancy or numberDiscrepancy or nationDiscrepancy or birthDiscrepancy:
            self.comparePassportAndDoc(grantOfAsylumPos)

            if nameDiscrepancy:
                self.click(onTable(rightSlot(textFieldOffset(grantOfAsylum.getTableBox("first-name")))))
                self.click(onTable(textFieldOffset(leftSlot(self.documentStack.passport.getTableBox("name")[:2]))))
            elif numberDiscrepancy:
                self.click(onTable(rightSlot(textFieldOffset(grantOfAsylum.getTableBox("number")))))
                self.click(onTable(leftSlot(self.documentStack.passport.getNumberClick())))
            elif nationDiscrepancy:
                self.click(onTable(textFieldOffset(rightSlot(grantOfAsylum.getTableBox("nation")[:2]))))
                self.click(onTable(leftSlot(centerOf(self.documentStack.passport.getTableBox("label")))))
            else:
                self.click(onTable(textFieldOffset(rightSlot(grantOfAsylum.getTableBox("birth")[:2]))))
                self.click(onTable(leftSlot(textFieldOffset(self.documentStack.passport.getTableBox("birth")))))

            if self.interrogateFailsafe():
                self.allowWithPassport(grantOfAsylumPos)
            else:
                self.interrogateAndDenyWithPassport(grantOfAsylumPos, INSPECT_TIME)
        else:
            if self.documentStack.moved: self.moveTo(SLOTS[0])
            self.dragTo(PASSPORT_ALLOW_POS)
            self.allowAndGive(close = True)
        self.giveAllDocs()
        return True

    def handleVaxCertWithReason(self) -> bool:
        vaxCert: VaxCert = self.documentStack.get(VaxCert)

        if vaxCert is None and self.missingDoc("entrants-must-have-vaxcert", VaxCert):
            return True

        vaxCert    = self.documentStack.get(VaxCert)
        vaxCertPos = self.documentStack.getSlot(VaxCert)

        nameDiscrepancy   = vaxCert.name   != self.documentStack.passport.name
        numberDiscrepancy = vaxCert.number != self.documentStack.passport.number

        if nameDiscrepancy or numberDiscrepancy:
            self.comparePassportAndDoc(vaxCertPos)

            if nameDiscrepancy:
                self.click(onTable(rightSlot(centerOf(vaxCert.getTableBox("name")))))
                self.click(onTable(textFieldOffset(leftSlot(self.documentStack.passport.getTableBox("name")[:2]))))
            else:
                self.click(onTable(rightSlot(centerOf(vaxCert.getTableBox("number")))))
                self.click(onTable(leftSlot(self.documentStack.passport.getNumberClick())))

            if self.interrogateFailsafe():
                self.allowWithPassport(vaxCertPos)
            else:
                self.interrogateAndDenyWithPassport(vaxCertPos, INSPECT_TIME)
            self.giveAllDocs()
            return True
        return False
    
    def handleAccessPermitWithReason(self) -> bool:
        accessPermit: AccessPermit = self.documentStack.get(AccessPermit)

        if accessPermit is None and self.missingDoc("foreigners-require-access-permit", AccessPermit): 
            return True
        
        accessPermit    = self.documentStack.get(AccessPermit)
        accessPermitPos = self.documentStack.getSlot(AccessPermit)

        nameDiscrepancy   = accessPermit.name   != self.documentStack.passport.name
        numberDiscrepancy = accessPermit.number != self.documentStack.passport.number
        nationDiscrepancy = accessPermit.nation != self.documentStack.passport.type_.nation

        if nameDiscrepancy or numberDiscrepancy or nationDiscrepancy:
            self.comparePassportAndDoc(accessPermitPos)

            if nameDiscrepancy:
                self.click(onTable(rightSlot(centerOf(accessPermit.getTableBox("name")))))
                self.click(onTable(textFieldOffset(leftSlot(self.documentStack.passport.getTableBox("name")[:2]))))
            elif numberDiscrepancy:
                self.click(onTable(rightSlot(textFieldOffset(accessPermit.getTableBox("number")[:2]))))
                self.click(onTable(leftSlot(self.documentStack.passport.getNumberClick())))
            else:
                self.click(onTable(rightSlot(textFieldOffset(accessPermit.getTableBox("nation")[:2]))))
                self.click(onTable(leftSlot(centerOf(self.documentStack.passport.getTableBox("label")))))

            if self.interrogateFailsafe():
                self.allowWithPassport(accessPermitPos)
            else:
                self.interrogateAndDenyWithPassport(accessPermitPos, INSPECT_TIME)
            self.giveAllDocs()
            return True
        return False
    
    def endAllow(self) -> None:
        if self.documentStack.moved: self.moveTo(SLOTS[0])         
        self.dragTo(PASSPORT_ALLOW_POS)
        self.allowAndGive(close = True)
        self.giveAllDocs()
    
    # checks
    def day1Check(self) -> bool:
        if self.next(): return False
        nation = self.fastPassportScan(self.lastGiveArea, np.asarray(self.getScreen().crop(GIVE_AREA)))

        if nation is None:
            fastScan = False
            nation = self.docScan().type_.nation
        else:
            fastScan = True
            self.moveTo(PAPER_POS)

        if nation == Nation.ARSTOTZKA:
            if not fastScan: self.moveTo(PAPER_SCAN_POS)
            self.dragTo(PASSPORT_ALLOW_POS)
            self.allowAndGive()
        else:
            if fastScan: self.dragTo(PASSPORT_DENY_POS)
            self.denyAndGive()

        return True
    
    def day2Check(self, *, wrong: bool) -> bool:
        if self.next(): return False
        passport: Passport = self.docScan()

        cond = self.checkDiscrepancies(passport)

        if (cond if wrong else not cond):
            self.moveTo(PAPER_SCAN_POS)
            self.dragTo(PASSPORT_ALLOW_POS)
            self.allowAndGive()
        else:
            self.denyAndGive()
            
        return True
    
    def day3Check(self) -> bool:
        nextRet, done = self.getAllDocs()
        if nextRet: return False
        if done:    return True

        if self.documentStack.moved: self.moveTo(SLOTS[0])
        if self.documentStack.passport.type_.nation == Nation.ARSTOTZKA or len(self.documentStack) != 0:
            self.dragTo(PASSPORT_ALLOW_POS)
            self.allowAndGive(close = True)
        else:
            if self.documentStack.moved: self.dragTo(PASSPORT_DENY_POS)
            self.denyAndGive(close = True)
        self.giveAllDocs()
        return True
    
    def day4Check(self) -> bool:
        nextRet, done = self.getAllDocs()
        if nextRet: return False
        if done:    return True

        if self.handleNoDocs():          return True
        if self.handleArstotzkanId():    return True
        if self.handleEntryPermit():     return True  
        if self.handlePurposeDuration(): return True
               
        self.endAllow()
        return True
    
    def day6Check(self) -> bool:
        nextRet, done = self.getAllDocs()
        if nextRet: return False
        if done:    return True

        if self.handleNoDocs():          return True
        if self.handleArstotzkanId():    return True
        if self.handleEntryPermit():     return True
        if self.handleWorkPass():        return True
        if self.handlePurposeDuration(): return True
        
        self.endAllow()
        return True
    
    def day8Check(self) -> bool:
        nextRet, done = self.getAllDocs()
        if nextRet: return False
        if done:    return True

        if self.handleNoDocs():          return True
        if self.handleArstotzkanId():    return True
        if self.handleDiplomaticAuth():  return True
        if self.handleEntryPermit():     return True
        if self.handleWorkPass():        return True
        if self.handlePurposeDuration(): return True
        
        self.endAllow()
        return True
    
    def day13Check(self) -> bool:
        nextRet, done = self.getAllDocs()
        if nextRet: return False
        if done:    return True

        if self.handleNoDocs():          return True
        if self.handleArstotzkanId():    return True
        if self.handleDiplomaticAuth():  return True
        if self.handleEntryPermit():     return True
        if self.handleWorkPass():        return True
        if self.handleIdSuppl():         return True
        if self.handlePurposeDuration(): return True

        self.endAllow()
        return True
    
    def day18Check(self) -> bool:
        nextRet, done = self.getAllDocs()
        if nextRet: return False
        if done:    return True
        
        if self.handleArstotzkanIdWithReason():        return True
        if self.handleDiplomaticAuthWithReason():      return True
        if self.handleEntryPermitWithReason():         return True 
        if self.handleWorkPassWithReason(EntryPermit): return True
        if self.handleIdSupplWithReason():             return True
        if self.handlePurposeDurationWithReason(EntryPermit, centerOf): 
            return True
        
        self.endAllow()
        return True
    
    def day21Check(self) -> bool:
        nextRet, done = self.getAllDocs()
        if nextRet: return False
        if done:    return True
        
        if self.handleArstotzkanIdWithReason():   return True
        if self.handleDiplomaticAuthWithReason(): return True

        purpose = self.transcription.waitFor(self.transcription.getPurpose)
        if purpose == Purpose.ASYLUM:
            if self.handleGrantOfAsylumWithReason(): return True
        else:
            if self.handleEntryPermitWithReason():         return True
            if self.handleWorkPassWithReason(EntryPermit): return True
            if self.handleIdSupplWithReason():             return True
            if self.handlePurposeDurationWithReason(EntryPermit, centerOf): 
                return True
        
        self.endAllow()
        return True
    
    def day26Check(self, *, nextCheck: bool = True) -> bool:
        nextRet, done = self.getAllDocs(nextCheck = nextCheck)
        if nextRet: return False
        if done:    return True

        if self.handleVaxCertWithReason():        return True
        if self.handleArstotzkanIdWithReason():   return True
        if self.handleDiplomaticAuthWithReason(): return True

        purpose = self.transcription.waitFor(self.transcription.getPurpose)
        if purpose == Purpose.ASYLUM:
            if self.handleGrantOfAsylumWithReason(): return True
        else:
            if self.handleEntryPermitWithReason():         return True
            if self.handleWorkPassWithReason(EntryPermit): return True
            if self.handleIdSupplWithReason():             return True
            if self.handlePurposeDurationWithReason(EntryPermit, centerOf): 
                return True
        
        self.endAllow()
        return True

    def day27Check(self, *, nextCheck: bool = True) -> bool:
        nextRet, done = self.getAllDocs(nextCheck = nextCheck)
        if nextRet: return False
        if done:    return True

        if self.handleVaxCertWithReason():        return True
        if self.handleArstotzkanIdWithReason():   return True
        if self.handleDiplomaticAuthWithReason(): return True

        purpose = self.transcription.waitFor(self.transcription.getPurpose)
        if purpose == Purpose.ASYLUM:
            if self.handleGrantOfAsylumWithReason(): return True
        else:
            if self.handleAccessPermitWithReason():         return True
            if self.handleWorkPassWithReason(AccessPermit): return True
            if self.handlePurposeDurationWithReason(
                AccessPermit, lambda box: textFieldOffset(box[:2])
            ): return True
        
        self.endAllow()
        return True
    
    # special encounters and utilities
    def prepareItem(self, pos: tuple[int, int]) -> None:
        self.moveTo(pos)
        self.dragTo(SLOTS[-1])

    def ezicMessenger(self, *, nextCheck: bool = True) -> None:
        if nextCheck: self.next()
        # "read" message and give it back
        self.moveTo(PAPER_POS)
        self.dragTo(PAPER_SCAN_POS)
        self.click(EZIC_MESSAGE_OPEN)
        self.dragTo(PERSON_POS) 

    def knownCriminal(self, checkFn: Callable) -> None:
        # if we do have the wanted check, we have to see which one of 
        # the criminals the first person is so we can remove them from the list
        if TAS.WANTED_CHECK: checkFn() 
        else:                self.multiDocAction(self.date >= TAS.DAY_18)

    def noPictureCheck(self, func: Callable) -> None:
        tmp = TAS.DAY4_PICTURE_CHECK
        TAS.DAY4_PICTURE_CHECK = False
        func()
        TAS.DAY4_PICTURE_CHECK = tmp