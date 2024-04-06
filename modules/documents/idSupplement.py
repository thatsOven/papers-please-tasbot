from PIL      import Image
from typing   import Self
from datetime import date
import time, os, numpy as np, pyautogui as pg

from modules.constants.screen   import *
from modules.constants.delays   import *
from modules.constants.other    import *
from modules.textRecognition    import parseDate, parseText
from modules.documents.document import Document, getBox
from modules.utils              import *

class IDSupplement(Document):
    BACKGROUNDS = None

    TABLE_OFFSET          = (295, 61) 
    EXPIRATION_TEXT_COLOR = (181, 18,  6)
    TEXT_COLOR            = ( 78, 69, 79)
    LAYOUT = {
        "label":       getBox(327,  77, 466, 124),
        "height":      getBox(395, 125, 444, 136),
        "weight":      getBox(395, 147, 444, 162),
        "description": getBox(315, 193, 456, 236),
        "thumb-area":  getBox(369, 244, 456, 312),
        "expiration":  getBox(387, 339, 452, 350)
    }

    @staticmethod
    def load():
        IDSupplement.BACKGROUNDS = Document.getBgs(
            IDSupplement.LAYOUT, IDSupplement.TABLE_OFFSET, Image.open(
                os.path.join(IDSupplement.TAS.ASSETS, "papers", "idSupplement.png")
            ).convert("RGB")
        )

        IDSupplement.BACKGROUNDS["label"] = np.asarray(IDSupplement.BACKGROUNDS["label"])

    @staticmethod
    def checkMatch(docImg: Image.Image) -> bool:
        return np.array_equal(np.asarray(docImg.crop(IDSupplement.LAYOUT["label"])), IDSupplement.BACKGROUNDS["label"])
    
    @staticmethod
    def parse(docImg: Image.Image) -> Self:
        return IDSupplement(
            height = int(parseText(
                docImg.crop(IDSupplement.LAYOUT["height"]), IDSupplement.BACKGROUNDS["height"],
                IDSupplement.TAS.FONTS["bm-mini"], IDSupplement.TEXT_COLOR, HEIGHT_CHARS,
                endAt = "cm"
            )[:-2]),
            weight = int(parseText(
                docImg.crop(IDSupplement.LAYOUT["weight"]), IDSupplement.BACKGROUNDS["weight"],
                IDSupplement.TAS.FONTS["bm-mini"], IDSupplement.TEXT_COLOR, WEIGHT_CHARS,
                endAt = "kg"
            )[:-2]),
            expiration = parseDate(
                docImg.crop(IDSupplement.LAYOUT["expiration"]), IDSupplement.BACKGROUNDS["expiration"],
                IDSupplement.TAS.FONTS["bm-mini"], IDSupplement.EXPIRATION_TEXT_COLOR
            ),
            description = docImg.crop(IDSupplement.LAYOUT["description"]),
            thumb       = docImg.crop(IDSupplement.LAYOUT["thumb-area"])
        )

    def __init__(self, height, weight, expiration, description, thumb):
        self.height           = height
        self.weight           = weight
        self.expiration: date = expiration
        self.description      = description
        self.thumb            = thumb

    def checkDiscrepancies(self, tas) -> bool:
        if tas.allowWrongWeight and tas.weight != self.weight:
            tas.wrongWeight = True
            return False

        if (
            self.expiration <= tas.date or
            tas.weight != self.weight
        ): return True

        if IDSupplement.TAS.APPEARANCE_HEIGHT_CHECK:
            tas.click(INSPECT_BUTTON)
            tas.click(onTable(centerOf(IDSupplement.LAYOUT["height"])))
            tas.click(PERSON_POS)
            time.sleep(INSPECT_ALPHACHANGE_TIME)
            before = np.asarray(tas.getScreen().crop(TABLE_AREA))
            time.sleep(INSPECT_TIME - INSPECT_ALPHACHANGE_TIME)
            msg = bgFilter(before, np.asarray(tas.getScreen().crop(TABLE_AREA)))

            if pg.locate(IDSupplement.TAS.MATCHING_DATA, msg) is None:
                tas.click(INSPECT_BUTTON)
                time.sleep(INSPECT_ALPHACHANGE_TIME)
                tas.moveTo(PAPER_SCAN_POS)
                return True
            
            tas.click(onTable(textFieldOffset(IDSupplement.LAYOUT["description"])))
            before = np.asarray(tas.getScreen().crop(TABLE_AREA))
            time.sleep(INSPECT_TIME)
            msg = bgFilter(before, np.asarray(tas.getScreen().crop(TABLE_AREA)))

            tas.click(INSPECT_BUTTON)
            time.sleep(INSPECT_ALPHACHANGE_TIME)
            tas.moveTo(PAPER_SCAN_POS)
            return pg.locate(IDSupplement.TAS.MATCHING_DATA_LINES, msg, confidence = 0.8) is None
        
        return False
    
    def checkDiscrepanciesWithReason(self, tas) -> bool:
        if tas.allowWrongWeight and tas.weight != self.weight:
            tas.wrongWeight = True
            return False
        
        if self.expiration <= tas.date:
            tas.click(INSPECT_BUTTON)
            tas.click(onTable(centerOf(IDSupplement.LAYOUT["expiration"])))
            tas.click(CLOCK_POS)
            time.sleep(INSPECT_INTERROGATE_TIME)
            tas.interrogate()
            tas.moveTo(PAPER_SCAN_POS)
            return True
        
        if tas.weight != self.weight:
            tas.click(INSPECT_BUTTON)
            tas.click(onTable(centerOf(IDSupplement.LAYOUT["weight"])))
            tas.click(centerOf(WEIGHT_AREA))
            time.sleep(INSPECT_INTERROGATE_TIME)
            tas.interrogate()
            tas.moveTo(PAPER_SCAN_POS)
            return True
        
        if IDSupplement.TAS.APPEARANCE_HEIGHT_CHECK:
            tas.click(INSPECT_BUTTON)
            tas.click(onTable(centerOf(IDSupplement.LAYOUT["height"])))
            tas.click(PERSON_POS)
            time.sleep(INSPECT_ALPHACHANGE_TIME)
            before = np.asarray(tas.getScreen().crop(TABLE_AREA))
            time.sleep(INSPECT_TIME - INSPECT_ALPHACHANGE_TIME)
            msg = bgFilter(before, np.asarray(tas.getScreen().crop(TABLE_AREA)))

            if pg.locate(IDSupplement.TAS.MATCHING_DATA, msg) is None:
                time.sleep(INSPECT_INTERROGATE_TIME - INSPECT_TIME)
                tas.interrogate()
                tas.moveTo(PAPER_SCAN_POS)
                return True
            
            tas.click(onTable(textFieldOffset(IDSupplement.LAYOUT["description"])))
            before = np.asarray(tas.getScreen().crop(TABLE_AREA))
            time.sleep(INSPECT_TIME)
            msg = bgFilter(before, np.asarray(tas.getScreen().crop(TABLE_AREA)))

            if pg.locate(IDSupplement.TAS.MATCHING_DATA_LINES, msg, confidence = 0.8) is None:
                time.sleep(INSPECT_INTERROGATE_TIME - INSPECT_TIME)
                tas.interrogate()
                tas.moveTo(PAPER_SCAN_POS)
                return True

            tas.click(INSPECT_BUTTON)
            time.sleep(INSPECT_ALPHACHANGE_TIME)
            tas.moveTo(PAPER_SCAN_POS)

        return False
    
    def __repr__(self) -> str:
        return f"""==- Identity Supplement -==
height:     {self.height}
weight:     {self.weight}
expiration: {self.expiration}"""