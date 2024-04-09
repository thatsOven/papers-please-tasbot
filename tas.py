# MIT License
#
# Copyright (c) 2024 thatsOven
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
# *IMPORTANT*: the only tested version is 1.1.67-S. 
#              this bot will currently NOT work for the latest version of the game.
# 
# for the bot to work, the game language has to be english, 
# the date format must be 1982-1-23, and the game must be windowed, in default resolution
# 
# *FOR DEVELOPERS*: when modifying methods of the TAS class, or adding new ones, be sure to run
#                   (or edit, in some cases) makeTASDef.py for better syntax highlighting and ide hints
#                   when creating runs.
#
# **TODO**
# - maybe rewrite text recognition in cython for performance + integrate build/run tool with makeTASDef.py
# - make gui
# - skip end menu fade on endings
# - check for end of day via day duration instead of using "next!" bubble
# - try to implement picture/face recognition and height recognition
# - figure out occasional parsing errors in transcription and text recognition rare bugs
# - linux compatibility(?)
# - make methods to handle special encounters in different ways
# - maybe make a simple scripting language for runs

from PIL               import ImageGrab, ImageFont, Image
from pathlib           import Path
from deskew            import determine_skew
from datetime          import date, timedelta
from skimage.color     import rgb2gray
from skimage.transform import rotate
from typing            import Callable, ClassVar, Any
import win32gui, win32com.client, time, os, math, pyautogui as pg, numpy as np

from modules.constants.delays import *
from modules.constants.screen import *
from modules.constants.other  import *
from modules.utils            import *

from modules.textRecognition          import charCheck, parseText, digitCheck, digitLength
from modules.transcription            import Transcription
from modules.documentStack            import DocumentStack, TASException
from modules.documents.document       import Document
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

from runs.run import Run

import json
import logging
logger = logging.getLogger(__name__)


class FilterVenvLogging(logging.Filter):
    """Without this, log file is filled with debug logs from imported modules."""

    def filter(self, record):
        return 'venv' not in record.pathname


class TAS:
    DEBUG: ClassVar[bool] = True

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

    RUNS: ClassVar[list]                               = None
    DOCUMENTS: ClassVar[list[Document]]                = None
    MOA_SEALS: ClassVar[tuple[Image.Image, ...]]       = None
    PASSPORT_TYPES: ClassVar[tuple[PassportType, ...]] = None

    NEXT_BUBBLE: ClassVar[np.ndarray]            = None
    MATCHING_DATA: ClassVar[Image.Image]         = None
    MATCHING_DATA_LINES: ClassVar[Image.Image]   = None
    VISA_SLIP: ClassVar[Image.Image]             = None
    WEIGHT_BG: ClassVar[np.ndarray]              = None
    WEIGHT_FILTER: ClassVar[np.ndarray]          = None
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

    SEX_F_GENERIC: ClassVar[np.ndarray]  = None
    SEX_M_OBRISTAN: ClassVar[np.ndarray] = None

    FONTS: ClassVar[dict[str, ImageFont.FreeTypeFont | dict[str, np.ndarray]]] = None
    NAMES: ClassVar[dict[str, dict[Sex, set[str]]]]                            = None

    checkHorn: bool
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
    sTime: float | None
    endingsTime: dict[int, float]
    weight: int | None
    lastGiveArea: np.ndarray | None
    wanted: list[tuple[int, int]]
    
    documentStack: Any
    transcription: Any

    def __init__(self):
        self.setupLogging()

        pg.useImageNotFoundException(False)
        pg.PAUSE = 0.05
        self.hwnd = None

        self.checkHorn = False

        self.allowWrongWeight = False
        self.wrongWeight      = False

        self.skipReason = False

        # TODO this system needs further testing but in the AllEndings run
        # this can only happen in days 25 and 27, and has an approximately 
        # 0.6% chance of happening with every entrant
        self.needId     = False
        self.newData    = True

        self.poison       = False
        self.doConfiscate = True
        self.confiscate   = False
        self.detain       = False

        self.skipGive = False
        self.needObri = 0

        self.weight       = None
        self.lastGiveArea = None
        self.date         = None

        self.sTime       = None
        self.endingsTime = {}

        self.wanted = []
        
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

        visaSlip = Image.open(
            os.path.join(TAS.ASSETS, "papers", "VisaSlipInner.png")
        ).convert("RGB")
        seizureSlip = Image.open(
            os.path.join(TAS.ASSETS, "papers", "SeizureSlipInner.png")
        ).convert("RGB")
        TAS.VISA_SLIP    = np.asarray(   visaSlip.resize((   visaSlip.size[0] * 2,    visaSlip.size[1] * 2), Image.Resampling.NEAREST))
        TAS.SEIZURE_SLIP = np.asarray(seizureSlip.resize((seizureSlip.size[0] * 2, seizureSlip.size[1] * 2), Image.Resampling.NEAREST))

        weightBg = Image.open(
            os.path.join(TAS.ASSETS, "weightBG.png")
        ).convert("RGB")
        weightFilter = weightBg.copy()
        weightFilter.paste((255, 255, 255), (0, 0) + weightFilter.size)
        TAS.WEIGHT_BG = np.asarray(weightBg)
        TAS.WEIGHT_FILTER = weightFilter

        TAS.DOLLAR_SIGN = Image.open(
            os.path.join(TAS.ASSETS, "dollarSign.png")
        ).convert("RGB")
        TAS.WANTED_CRIMINALS = Image.open(
            os.path.join(TAS.ASSETS, "wantedCriminals.png")
        ).convert("RGB")
        TAS.SCREW = Image.open(
            os.path.join(TAS.ASSETS, "screw.png")
        ).convert("RGB")
        TAS.WIRES = Image.open(
            os.path.join(TAS.ASSETS, "wires.png")
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

        digits = Image.open(os.path.join(TAS.ASSETS, "fonts", "digits.png")).convert("RGB")
        digits = digits.resize((digits.size[0] * 2, digits.size[1] * 2), Image.Resampling.NEAREST)
        TAS.FONTS["digits"] = {
            str(c): np.asarray(digits.crop((x * DIGITS_LENGTH, 0, (x + 1) * DIGITS_LENGTH, DIGITS_HEIGHT)))
            for x, c in enumerate(DIGITS)
        }

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
                PassportData().offsets(
                    name       = (271, 327, 500, 342),
                    birth      = (325, 251, 390, 262),
                    sex        = (305, 269, 314, 280),
                    city       = (305, 287, 418, 302),
                    expiration = (325, 305, 390, 316),
                    number     = (271, 347, 504, 358),
                    picture    = (421, 225, 500, 320),
                    label      = (271, 225, 390, 242)
                )
            ),
            PassportType(
                Nation.ARSTOTZKA,
                os.path.join(TAS.ASSETS, "passports", "arstotzka"),
                (City.ORVECH_VONOR, City.EAST_GRESTIN, City.PARADIZNA),
                PassportData().offsets(
                    name       = (271, 225, 503, 240),
                    birth      = (411, 245, 476, 256),
                    sex        = (391, 261, 400, 272),
                    city       = (391, 277, 506, 292),
                    expiration = (411, 293, 476, 304),
                    number     = (271, 345, 394, 356),
                    picture    = (271, 245, 350, 340),
                    label      = (413, 315, 500, 334)
                )
            ),
            PassportType(
                Nation.IMPOR,
                os.path.join(TAS.ASSETS, "passports", "impor"),
                (City.ENKYO, City.HAIHAN, City.TSUNKEIDO),
                PassportData().offsets(
                    name       = (269, 221, 503, 236),
                    birth      = (415, 243, 482, 254),
                    sex        = (395, 259, 404, 270),
                    city       = (395, 275, 498, 290),
                    expiration = (415, 291, 482, 302),
                    number     = (335, 341, 500, 352),
                    picture    = (273, 241, 352, 336),
                    label      = (275, 343, 334, 354)
                )
            ),
            PassportType(
                Nation.KOLECHIA,
                os.path.join(TAS.ASSETS, "passports", "kolechia"),
                (City.YURKO_CITY, City.VEDOR, City.WEST_GRESTIN),
                PassportData().offsets(
                    name       = (271, 245, 502, 260),
                    birth      = (413, 263, 478, 274),
                    sex        = (393, 279, 402, 290),
                    city       = (393, 295, 502, 310),
                    expiration = (413, 311, 478, 322),
                    number     = (354, 345, 505, 356),
                    picture    = (271, 263, 350, 358),
                    label      = (271, 221, 498, 238)
                )
            ),
            PassportType(
                Nation.OBRISTAN,
                os.path.join(TAS.ASSETS, "passports", "obristan"),
                (City.SKAL, City.LORNDAZ, City.MERGEROUS),
                PassportData().offsets(
                    name       = (271, 245, 502, 260),
                    birth      = (329, 271, 394, 282),
                    sex        = (309, 287, 318, 298),
                    city       = (309, 303, 416, 318),
                    expiration = (329, 319, 394, 330),
                    number     = (275, 345, 422, 356),
                    picture    = (423, 263, 502, 358),
                    label      = (269, 221, 504, 240)
                )
            ),
            PassportType(
                Nation.REPUBLIA,
                os.path.join(TAS.ASSETS, "passports", "republia"),
                (City.TRUE_GLORIAN, City.LESRENADI, City.BOSTAN),
                PassportData().offsets(
                    name       = (271, 223, 503, 238),
                    birth      = (329, 245, 394, 256),
                    sex        = (309, 261, 318, 272),
                    city       = (309, 277, 423, 292),
                    expiration = (329, 293, 394, 304),
                    number     = (271, 345, 507, 356),
                    picture    = (425, 241, 504, 336),
                    label      = (273, 321, 396, 336)
                )
            ),
            PassportType(
                Nation.UNITEDFED,
                os.path.join(TAS.ASSETS, "passports", "unitedFed"),
                (City.GREAT_RAPID, City.SHINGLETON, City.KORISTA_CITY),
                PassportData().offsets(
                    name       = (271, 245, 504, 260),
                    birth      = (413, 261, 479, 272),
                    sex        = (393, 277, 402, 288),
                    city       = (393, 293, 504, 308),
                    expiration = (413, 309, 479, 320),
                    number     = (355, 345, 507, 356),
                    picture    = (271, 261, 350, 356),
                    label      = (271, 223, 504, 238)
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
        charCheck.BM_MINI    = TAS.FONTS["bm-mini"]
        charCheck.MINI_KYLIE = TAS.FONTS["mini-kylie"]
        charCheck._04B03     = TAS.FONTS["04b03"]

        Run.TAS           = TAS
        Passport.TAS      = TAS
        Document.TAS      = TAS
        Transcription.TAS = TAS
        Transcription.load()

        for document in TAS.DOCUMENTS:
            logger.info(f"Initializing {document.__name__}...")
            document.TAS = TAS
            document.load()

        # import all runs
        for module in os.listdir(TAS.RUNS_DIR):
            if module.endswith(".py") and module != "run.py":
                __import__(f"runs.{module[:-3]}", locals(), globals())

        TAS.RUNS = []
        for run in Run.__subclasses__():
            logger.info(f'Initializing Run "{run.__name__}"...')
            run.TAS = TAS
            inst = run()
            inst.tas = self
            TAS.RUNS.append(inst)

        logger.info("TASBOT initialized!")

    @classmethod
    def getWinHWDN(self) -> str:
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

    @staticmethod
    def setupLogging():
        config_path = os.path.join(TAS.PROGRAM_DIR, "config/logging_config.json")
        with open(config_path) as f:
            config = json.load(f)
        logging.config.dictConfig(config)

    def getScreen(self) -> Image.Image:
        return ImageGrab.grab(win32gui.GetWindowRect(self.hwnd)).convert("RGB")
    
    def mouseOffset(self, x: int, y: int) -> tuple[int, int]:
        bX, bY, _, _ = win32gui.GetWindowRect(self.hwnd)
        return (bX + x, bY + y)        

    def moveTo(self, at: tuple[int, int]) -> None:
        pg.moveTo(*self.mouseOffset(*at))

    def click(self, at: tuple[int, int]) -> None:
        self.moveTo(at)
        pg.mouseDown()
        pg.mouseUp()

    def dragTo(self, at: tuple[int, int]) -> None:
        pg.mouseDown()
        self.moveTo(at)
        pg.mouseUp()

    def dragToWithGive(self, at: tuple[int, int]) -> None:
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
                if self.checkHorn and pg.locate(TAS.BUTTONS["sleep"], screen) is not None: break 

                pos[0] = at[0] + math.sin(th[0]) * DRAG_TO_WITH_GIVE_AMPLITUDE[0] - DRAG_TO_WITH_GIVE_POS_OFFS[0]
                pos[1] = at[1] + math.sin(th[1]) * DRAG_TO_WITH_GIVE_AMPLITUDE[1] - DRAG_TO_WITH_GIVE_POS_OFFS[1]
                th[0] += DRAG_TO_WITH_GIVE_THETA_INC[0]
                th[1] += DRAG_TO_WITH_GIVE_THETA_INC[1]
                self.moveTo(pos)

        pg.mouseUp()

    def waitForDoorChange(self) -> None:
        screen = self.getScreen()
        before = (
            np.asarray(screen.crop(EXIT_AREAS[0])),
            np.asarray(screen.crop(EXIT_AREAS[1])),
        )

        while True:
            screen = self.getScreen()
            # needed in some edge cases so it doesn't get stuck
            if self.checkHorn and pg.locate(TAS.BUTTONS["sleep"], screen) is not None: break 

            if not (
                np.array_equal(before[0], np.asarray(screen.crop(EXIT_AREAS[0]))) and
                np.array_equal(before[1], np.asarray(screen.crop(EXIT_AREAS[1])))
            ): break

    def waitForAreaChange(self, area: tuple[int, int, int, int]) -> np.ndarray:
        before = np.asarray(self.getScreen().crop(area))
        while np.array_equal(before, np.asarray(self.getScreen().crop(area))): pass
        return before

    def waitForGiveAreaChange(self, *, update: bool = True, sleep: bool = True) -> None:
        if update: self.lastGiveArea = self.waitForAreaChange(GIVE_AREA)
        else:                          self.waitForAreaChange(GIVE_AREA)

        if sleep: time.sleep(0.25)

    def waitFor(self, button: Image.Image, *, move: bool = True) -> pg.Point:
        if move: self.moveTo((0, 0))
        while True:
            box = pg.locate(button, self.getScreen())
            if box is not None: return pg.center(box)

    def waitForSleepButton(self) -> None:
        self.waitFor(TAS.BUTTONS["sleep"])
        time.sleep(0.5)

    def goToWantedCriminals(self) -> None:
        while pg.locate(TAS.WANTED_CRIMINALS, self.getScreen()) is None:
            self.click(BULLETIN_NEXT_BUTTON)

    def nextPartial(self) -> bool:
        # if weight is none, this is first person: no need to wait
        if self.weight is None: 
            if TAS.WANTED_CHECK and self.date >= TAS.DAY_14:
                self.goToWantedCriminals()
                self.moveTo(INITIAL_BULLETIN_POS)
                self.dragTo(RIGHT_BULLETIN_POS)
                self.wanted = list(WANTED)
            else: 
                # the animation confuses the piece of code that waits for the person to give documents
                # so this manually moves the bulletin in place when the day starts
                self.moveTo(INITIAL_BULLETIN_POS)
                self.dragTo(BULLETIN_POS)
        else:
            self.waitForDoorChange()

        self.documentStack.reset()
        self.transcription.reset()

        if self.checkHorn:
            before = np.asarray(self.getScreen().crop(HORN_MESSAGE_AREA))
            self.click(HORN)
            time.sleep(HORN_MESSAGE_APPEAR_TIME)
            msgImg = bgFilter(before, np.asarray(self.getScreen().crop(HORN_MESSAGE_AREA)))

            if np.array_equal(TAS.NEXT_BUBBLE, msgImg): return True
            else:
                self.waitForSleepButton()
                return False
        else:
            self.click(HORN)
            return True

    def next(self) -> bool:
        if self.nextPartial():
            self.waitForGiveAreaChange()

            # this converts the colored image from the screenshot to an image with
            # black background and white text (so it's easier to compare to the digits' images)
            diff = bgFilter(TAS.WEIGHT_BG, np.asarray(self.getScreen().crop(WEIGHT_AREA)))
            np.copyto(diff, TAS.WEIGHT_FILTER, where = diff != 0)
            weightCheck = parseText(
                Image.fromarray(diff), None, TAS.FONTS["digits"], None,
                DIGITS, checkFn = digitCheck, lenFn = digitLength
            )

            if weightCheck == "": 
                self.waitForSleepButton()
                return True
            
            self.weight = int(weightCheck)
            self.wrongWeight = False
            return False
        
        return True

    # menu utilities
    def waitForAllTicks(self) -> None:
        self.waitFor(TAS.DOLLAR_SIGN)
        self.moveTo((0, 0))

    def clickOnTick(self, tick: str) -> None:
        self.click((END_TICK_X, pg.center(pg.locate(TAS.TICKS[tick], self.getScreen())).y))

    def story(self) -> None:
        self.click(STORY_BUTTON)
        time.sleep(MENU_DELAY)

    def startRun(self) -> None:
        self.sTime = time.time()

    def endingTime(self, endingN: int) -> float:
        if self.sTime is None:
            raise TASException("Timer was never started (tas.sTime is None)")

        t = time.time() - self.sTime
        self.endingsTime[endingN] = t
        return t

    def newGame(self) -> None:
        self.date = TAS.DAY_1
        self.story()
        self.click(NEW_BUTTON)
        self.startRun()
        time.sleep(MENU_DELAY)
        pg.click(*self.mouseOffset(*INTRO_BUTTON), clicks = 11, interval = 0.05) # skip introduction
        time.sleep(MENU_DELAY)

    def daySetup(self) -> None:
        self.click(INTRO_BUTTON)
        time.sleep(DAY_DELAY)
        self.checkHorn        = False
        self.allowWrongWeight = False
        self.doConfiscate     = True
        self.weight           = None
        self.wanted           = []

    def dayEnd(self) -> None:
        self.checkHorn = False
        self.click(SLEEP_BUTTON)
        time.sleep(MENU_DELAY)
        self.date += timedelta(days = 1)

    def restartFrom(self, day: tuple[int, int], date: date, story: bool = True) -> None:
        if story: self.story()
        self.click(day)
        time.sleep(0.25)
        self.click(CONTINUE_BUTTON)
        time.sleep(MENU_DELAY)
        self.date = date 

    # endings
    def ending(self, endingN: int, clicks: int, *, credits: bool = False) -> None:
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
        self.ending(1, 5)

    def ending2(self) -> None:
        self.ending(2, 5)

    def ending3(self) -> None:
        self.ending(3, 3)

    def ending4(self) -> None:
        self.ending(4, 5)

    def ending5(self) -> None:
        self.ending(5, 5)

    def ending6(self) -> None:
        self.ending(6, 5)

    def ending7(self) -> None:
        self.ending(7, 5)

    def ending8(self) -> None:
        self.ending(8, 5)

    def ending9(self) -> None:
        self.ending(9, 10)

    def ending10(self) -> None:
        self.ending(10, 10)

    def ending11(self) -> None:
        self.ending(11, 5)

    def ending12(self) -> None:
        self.ending(12, 5)

    def ending13(self) -> None:
        self.ending(13, 5)

    def ending14(self) -> None:
        self.ending(14, 14)

    def ending15(self) -> None:
        self.ending(15, 7)

    def ending16(self) -> None:
        self.ending(16, 16)

    def ending17(self) -> None:
        self.ending(17, 11)

    def ending18(self) -> None:
        self.ending(18, 19, credits = True)

    def ending19(self) -> None:
        self.ending(19, 7, credits = True)

    def ending20(self) -> None:
        self.ending(20, 11, credits = True)

    # basic document handling utilities
    def handleConfiscate(self, pos: tuple[int, int], *, detain: bool = False) -> None:
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
        self.handleConfiscate(pos, detain = self.detain)

        if self.detain:
            self.detain = False

            if self.date < TAS.DAY_5:
                raise TASException(f"Cannot detain on day {dateToDay(self.date)}")

            if self.transcription.waitFor(self.transcription.getDetainable):
                pos = self.waitFor(TAS.BUTTONS["detain"])
                time.sleep(0.5)
                self.click(pos)

                self.documentStack.reset() # all documents disappear when you press detain
                self.waitForDoorChange()   # extra delay when detaining, so we wait for door change twice
                return True
        return False

    def allowAndGive(self, *, close: bool = False, waitClose: bool = True) -> None:
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
        if nextCheck:
            if self.next(): return False

        self.moveTo(PAPER_POS)
        self.dragTo(PASSPORT_ALLOW_POS)
        self.allowAndGive()

        return True

    def passportOnlyDeny(self, *, nextCheck: bool = True) -> bool:
        if nextCheck:
            if self.next(): return False
        
        self.moveTo(PAPER_POS)
        self.dragTo(PASSPORT_DENY_POS)
        self.denyAndGive()

        return True

    def docScan(self, *, move: bool = True) -> Document | Passport | Nation | None:
        # take document screenshot
        before = np.asarray(self.getScreen().crop(TABLE_AREA))
        if move: self.moveTo(PAPER_POS)
        self.dragTo(PAPER_SCAN_POS)
        self.moveTo(PAPER_POS) # get cursor out of the way
        docImg = Image.fromarray(bgFilter(before, np.asarray(self.getScreen().crop(TABLE_AREA))))

        for document in TAS.DOCUMENTS:
            if document.checkMatch(docImg):
                doc: Document = document.parse(docImg)

                if self.doConfiscate and doc.confiscatePassportWhen(self):
                    self.confiscate = True

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

        if self.date == TAS.DAY_1: return type_.nation

        passport: Passport = Passport.parse(docImg, type_)

        if self.doConfiscate and passport.confiscateWhen(self):
            self.confiscate = True

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
            if self.checkHorn and pg.locate(TAS.BUTTONS["sleep"], screen) is not None: break 
            
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
            if TAS.DEBUG: logger.info(doc)
            else:         logger.debug(doc)
            self.moveTo(PAPER_SCAN_POS)

            if type(doc) is Passport:
                self.documentStack.passport = doc

                if self.needId:
                    discrepancy |= doc.checkDiscrepanciesInternal(self)
                elif self.passportCheck(
                    self.lastGiveArea, True, 
                    lambda x: discrepancy or x.checkDiscrepanciesInternal(self)
                ): return False, True

                if np.array_equal(self.lastGiveArea, np.asarray(self.getScreen().crop(GIVE_AREA))): break

                self.documentStack.push(doc)
            else:
                if (discrepancy and self.needId) or ((not discrepancy) and doc is not None and doc.checkDiscrepanciesInternal(self)):
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
            lambda x: discrepancy or x.checkDiscrepanciesInternal(self), 
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

    def missingDoc(self, rule: str, type_: type) -> bool:
        self.interrogateMissingDoc(rule)
        self.putRulebookBack()

        if self.newData:
            tmp = self.lastGiveArea
            self.lastGiveArea = np.asarray(self.getScreen().crop(GIVE_AREA))
            
            if self.transcription.waitFor(lambda: self.transcription.getMissingDocGiven(type_.__name__)):
                self.waitForGiveAreaChange(update = False)
                doc = self.docScan()

                discrepancy = doc.checkDiscrepanciesInternal(self)
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
        people = self.getScreen().crop(area)
        testImg = people.copy()
        testImg.paste(PEOPLE_COLOR, (0, 0) + testImg.size)
        filter = people.copy()
        filter.paste((0, 0, 0), (0, 0) + filter.size)

        people  = np.asarray(people).copy()
        testImg = np.asarray(testImg)
        filter  = np.asarray(filter)

        np.copyto(people, filter, where = people != testImg)

        ys, xs, _ = people.nonzero()
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
        self.click((800, 405))
        self.click((695, 490))
        self.click((800, 490))
        # wait for wires and calensk
        while pg.locate(TAS.WIRES, self.getScreen().crop(TABLE_AREA)) is None: pass
        while pg.locate(TAS.WIRES, self.getScreen().crop(TABLE_AREA)) is not None:
            # try to cut first wire
            self.click((735, 440))
            self.moveTo(TABLE_AREA[:2])
        # when cutting first wire succeeds, wires is no longer located, 
        # so it falls here and cuts all other wires
        self.click((700, 440))
        self.click((785, 440))
        self.click((760, 440))
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
                    self.click(onTable(textFieldOffset(rightSlot(ArstotzkanID.LAYOUT["birth"][:2]))))
                    self.click(onTable(textFieldOffset(leftSlot(self.documentStack.passport.type_.layout.birth[:2]))))
                else:
                    self.click(onTable(textFieldOffset(rightSlot(ArstotzkanID.LAYOUT["last-name"][:2]))))
                    self.click(onTable(textFieldOffset(leftSlot(self.documentStack.passport.type_.layout.name[:2]))))

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
                self.click(onTable(rightSlot(centerOf(DiplomaticAuth.LAYOUT["name"]))))
                self.click(onTable(textFieldOffset(leftSlot(self.documentStack.passport.type_.layout.name[:2]))))
            elif numberDiscrepancy:
                self.click(onTable(rightSlot(centerOf(DiplomaticAuth.LAYOUT["number"]))))
                self.click(onTable(leftSlot(self.documentStack.passport.type_.getNumberClick())))
            else:
                self.click(onTable(textFieldOffset(rightSlot(DiplomaticAuth.LAYOUT["nation"][:2]))))
                self.click(onTable(leftSlot(centerOf(self.documentStack.passport.type_.layout.label))))

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
                self.click(onTable(rightSlot(centerOf(EntryPermit.LAYOUT["name"]))))
                self.click(onTable(textFieldOffset(leftSlot(self.documentStack.passport.type_.layout.name[:2]))))
            else:
                self.click(onTable(rightSlot(centerOf(EntryPermit.LAYOUT["number"]))))
                self.click(onTable(leftSlot(self.documentStack.passport.type_.getNumberClick())))

            if self.interrogateFailsafe():
                self.allowWithPassport(entryPermitPos)
            else:
                self.interrogateAndDenyWithPassport(entryPermitPos, INSPECT_TIME)
            self.giveAllDocs()
            return True
        return False
        
    def handleWorkPassWithReason(self, permitType: type) -> bool:
        permit: EntryPermit | AccessPermit = self.documentStack.get(permitType)

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
                self.click(onTable(rightSlot(centerOf(WorkPass.LAYOUT["name"]))))
                self.click(onTable(textFieldOffset(leftSlot(self.documentStack.passport.type_.layout.name[:2]))))

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
                self.click(centerOf(WorkPass.LAYOUT["until"]))
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
    
    def handlePurposeDurationWithReason(self, permitType: type, alignFn: Callable[[tuple[int, int, int, int]], tuple[int, int]]) -> bool:
        duration = self.transcription.waitFor(self.transcription.getDuration)
        purpose  = self.transcription.getPurpose()

        permit: EntryPermit | AccessPermit = self.documentStack.get(permitType)

        purposeDiscrepancy  = permit.purpose  != purpose
        durationDiscrepancy = permit.duration != duration

        if purposeDiscrepancy or durationDiscrepancy:
            purposePos  = self.transcription.getPurposePos()
            durationPos = self.transcription.getDurationPos()

            permitPos = self.documentStack.getSlot(permitType)

            self.moveTo(SLOTS[permitPos])
            self.dragTo(RIGHT_SCAN_SLOT)

            self.moveTo(TRANSCRIPTION_POS)
            self.dragTo(LEFT_SCAN_SLOT)

            self.click(INSPECT_BUTTON)

            if purposeDiscrepancy:
                self.click(onTable(textFieldOffset(leftSlot(purposePos[:2]))))
                self.click(onTable(rightSlot(alignFn(permitType.LAYOUT["purpose"]))))
            else:
                self.click(onTable(textFieldOffset(leftSlot(durationPos[:2]))))
                self.click(onTable(rightSlot(alignFn(permitType.LAYOUT["duration"]))))

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
                self.click(onTable(rightSlot(textFieldOffset(GrantOfAsylum.LAYOUT["first-name"]))))
                self.click(onTable(textFieldOffset(leftSlot(self.documentStack.passport.type_.layout.name[:2]))))
            elif numberDiscrepancy:
                self.click(onTable(rightSlot(textFieldOffset(GrantOfAsylum.LAYOUT["number"]))))
                self.click(onTable(leftSlot(self.documentStack.passport.type_.getNumberClick())))
            elif nationDiscrepancy:
                self.click(onTable(textFieldOffset(rightSlot(GrantOfAsylum.LAYOUT["nation"][:2]))))
                self.click(onTable(leftSlot(centerOf(self.documentStack.passport.type_.layout.label))))
            else:
                self.click(onTable(textFieldOffset(rightSlot(GrantOfAsylum.LAYOUT["birth"][:2]))))
                self.click(onTable(leftSlot(textFieldOffset(self.documentStack.passport.type_.layout.birth))))

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
                self.click(onTable(rightSlot(centerOf(VaxCert.LAYOUT["name"]))))
                self.click(onTable(textFieldOffset(leftSlot(self.documentStack.passport.type_.layout.name[:2]))))
            else:
                self.click(onTable(rightSlot(centerOf(VaxCert.LAYOUT["number"]))))
                self.click(onTable(leftSlot(self.documentStack.passport.type_.getNumberClick())))

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
                self.click(onTable(rightSlot(centerOf(AccessPermit.LAYOUT["name"]))))
                self.click(onTable(textFieldOffset(leftSlot(self.documentStack.passport.type_.layout.name[:2]))))
            elif numberDiscrepancy:
                self.click(onTable(rightSlot(textFieldOffset(AccessPermit.LAYOUT["number"]))))
                self.click(onTable(leftSlot(self.documentStack.passport.type_.getNumberClick())))
            else:
                self.click(onTable(rightSlot(textFieldOffset(AccessPermit.LAYOUT["nation"]))))
                self.click(onTable(leftSlot(centerOf(self.documentStack.passport.type_.layout.label))))

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
            nation = self.docScan()
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

        cond = passport.checkDiscrepancies(self)

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

    @staticmethod
    def select(msg: str, options: list) -> int:
        while True:
            print(msg)
            for i, opt in enumerate(options):
                print(f"{i + 1}) {opt}")

            res = input()
            try:
                _ = int(res)
            except ValueError: pass
            else:
                res = int(res) - 1
                if 0 <= res < len(options):
                    return res
                
            print("Invalid input.")

    def run(self) -> None:
        while True:
            i   = TAS.select("Select run:", [run.__class__.__name__ for run in TAS.RUNS])
            act = TAS.select("Select action:", ["Run", "Test", "View credits"])
            
            if act in (0, 1):
                self.hwnd = self.getWinHWDN()
                shell = win32com.client.Dispatch("WScript.Shell")
                shell.SendKeys('%')
                win32gui.SetForegroundWindow(self.hwnd)

            match act:
                case 0:
                    TAS.RUNS[i].run()
                case 1:
                    TAS.RUNS[i].test()
                case 2:
                    print(TAS.RUNS[i].credits())

if __name__ == "__main__": TAS().run()