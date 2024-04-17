from PIL    import Image
from enum   import Enum
from typing import Self
import time, os, numpy as np, pyautogui as pg

from modules.constants.screen   import *
from modules.constants.delays   import *
from modules.constants.other    import *
from modules.textRecognition    import parseDate, parseText
from modules.documents.document import convertBox, getBox
from modules.utils              import *

import logging

logger = logging.getLogger('tas.' + __name__)


class City(Enum):
    (
        ST_MARMERO, GLORIAN, OUTER_GROUSE, 
        ORVECH_VONOR, EAST_GRESTIN, PARADIZNA, 
        ENKYO, HAIHAN, TSUNKEIDO,
        YURKO_CITY, VEDOR, WEST_GRESTIN,
        SKAL, LORNDAZ, MERGEROUS,
        TRUE_GLORIAN, LESRENADI, BOSTAN,
        GREAT_RAPID, SHINGLETON, KORISTA_CITY,
        UNKNOWN
    ) = (
        "St. Marmero", "Glorian", "Outer Grouse",
        "Orvech Vonor", "East Grestin", "Paradizna",
        "Enkyo", "Haihan", "Tsunkeido",
        "Yurko City", "Vedor", "West Grestin",
        "Skal", "Lorndaz", "Mergerous",
        "True Glorian", "Lesrenadi", "Bostan",
        "Great Rapid", "Shingleton", "Korista City",
        ""
    )

def getCity(city: str):
    try:               return City(city)
    except ValueError: return City.UNKNOWN

class Nation(Enum):
    ANTEGRIA, ARSTOTZKA, IMPOR, KOLECHIA, OBRISTAN, REPUBLIA, UNITEDFED = (
        "ANTEGRIA", "ARSTOTZKA", "IMPOR", "KOLECHIA", "OBRISTAN", "REPUBLIA", "UNITEDFED"
    )

class Sex(Enum):
    # as much as i don't like this, the game has two of these :c
    # so i'm using booleans cause cleaner/faster code
    M, F = False, True 
    
class PassportData:
    def __init__(
        self, name = None, birth = None, sex = None, city = None, 
        expiration = None, number = None, picture = None, label = None
    ):
        self.name       = name
        self.birth      = birth
        self.sex        = sex
        self.city       = city
        self.expiration = expiration
        self.number     = number
        self.picture    = picture
        self.label      = label

    def offsets(self, *, name, birth, sex, city, expiration, number, picture, label): 
        self.name       = getBox(*name)
        self.birth      = getBox(*birth)
        self.sex        = getBox(*sex)
        self.city       = getBox(*city)
        self.expiration = getBox(*expiration)
        self.number     = getBox(*number)
        self.picture    = getBox(*picture)
        self.label      = getBox(*label)
        return self

class PassportType:
    def __init__(self, nation, baseDir, cities, layout):
        logger.info(f"Initializing passport for {nation}...")
        self.nation: Nation       = nation
        self.outerTexture         = Image.open(os.path.join(baseDir, "outer.png")).convert("RGB")
        self.cities               = cities
        self.layout: PassportData = layout
        
        innerTexture = Image.open(os.path.join(baseDir, "inner.png")).convert("RGB")
        innerTexture = innerTexture.resize((innerTexture.size[0] * 2, innerTexture.size[1] * 2), Image.Resampling.NEAREST)
        self.backgrounds = PassportData(
            name       = innerTexture.crop(convertBox(self.layout.name,       PASSPORT_TABLE_OFFSET)),
            birth      = innerTexture.crop(convertBox(self.layout.birth,      PASSPORT_TABLE_OFFSET)),
            city       = innerTexture.crop(convertBox(self.layout.city,       PASSPORT_TABLE_OFFSET)),
            expiration = innerTexture.crop(convertBox(self.layout.expiration, PASSPORT_TABLE_OFFSET)),
            number     = innerTexture.crop(convertBox(self.layout.number,     PASSPORT_TABLE_OFFSET)),
            label      = innerTexture.crop(convertBox(self.layout.label,      PASSPORT_TABLE_OFFSET))
        )

    def getNumberClick(self):
        match self.nation:
            case Nation.ANTEGRIA | Nation.IMPOR | Nation.KOLECHIA | Nation.REPUBLIA | Nation.UNITEDFED:
                return offsetPoint(self.layout.number[2:], (-40, -4))
            case Nation.ARSTOTZKA | Nation.OBRISTAN:
                return textFieldOffset(self.layout.number[:2])

class Passport:
    TAS = None

    def __init__(self, name, birth, sex, city, expiration, number, type_):
        self.name: Name          = name
        self.birth               = birth
        self.sex:  Sex           = sex
        self.city: City          = city
        self.expiration          = expiration
        self.number              = number
        self.type_: PassportType = type_

    @staticmethod
    def parse(docImg: Image.Image, type_: PassportType) -> Self:
        obristan          = type_.nation == Nation.OBRISTAN
        obri_or_arstotzka = obristan or type_.nation == Nation.ARSTOTZKA
        textColor = OBRISTAN_TEXT_COLOR if obristan else PASSPORT_TEXT_COLOR

        passport = Passport(
            name = Name.fromPassportOrID(parseText(
                docImg.crop(type_.layout.name), type_.backgrounds.name, 
                Passport.TAS.FONTS["bm-mini"], PASSPORT_TEXT_COLOR, PASSPORT_NAME_CHARS,
                endAt = "  "
            )),
            birth = parseDate(
                docImg.crop(type_.layout.birth), type_.backgrounds.birth, 
                Passport.TAS.FONTS["bm-mini"], textColor
            ),
            city = getCity(parseText(
                docImg.crop(type_.layout.city), type_.backgrounds.city, 
                Passport.TAS.FONTS["bm-mini"], textColor, PASSPORT_CITY_CHARS,
                endAt = "  "
            )),
            expiration = parseDate(
                docImg.crop(type_.layout.expiration), type_.backgrounds.expiration, 
                Passport.TAS.FONTS["bm-mini"], textColor
            ),
            number = parseText(
                docImg.crop(type_.layout.number), type_.backgrounds.number, 
                Passport.TAS.FONTS["bm-mini"], textColor, PASSPORT_NUM_CHARS,
                misalignFix = not obri_or_arstotzka,
                endAt = "  " if obri_or_arstotzka else None
            ),
            sex   = None,
            type_ = type_
        )

        if obristan:
              # i could wait around for a F marked passport from obristan but whatever, this works
              passport.sex = Sex(not np.array_equal(Passport.TAS.SEX_M_OBRISTAN, np.asarray(docImg.crop(type_.layout.sex))))
        else: passport.sex = Sex(    np.array_equal(Passport.TAS.SEX_F_GENERIC,  np.asarray(docImg.crop(type_.layout.sex))))
         
        return passport
    
    def isSexWrong(self):
        # this actually doesn't cover all cases, cause the game really wants you to assume the person's sex
        # but again, even if i wanted to do this, i have no system for face recognition.
        # for this reason, i've decided to just ignore those cases, since they don't really happen that often
        return str(self.name) not in Passport.TAS.NAMES["full"][self.sex] and (
            self.name.first.capitalize() not in Passport.TAS.NAMES["first"][self.sex] or
            self.name.last.capitalize()  not in Passport.TAS.NAMES["last"][self.sex]
        )
            
    def __repr__(self):
        return f"""==- Passport -==
name:       {self.name}
birth:      {self.birth}
sex:        {self.sex}
city:       {self.city}
expiration: {self.expiration}
number:     {self.number}
nation:     {self.type_.nation}"""