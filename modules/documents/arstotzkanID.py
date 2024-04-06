from PIL      import Image
from enum     import Enum
from typing   import Self
from datetime import date
import time, os, numpy as np, pyautogui as pg

from modules.constants.screen   import *
from modules.constants.delays   import *
from modules.constants.other    import *
from modules.textRecognition    import parseDate, parseText
from modules.documents.document import Document, getBox
from modules.utils              import *

class District(Enum):
    (
        ALTAN, VESCILLO, BURNTON, OCTOVALIS,
        GENNISTORA, LENDIFORMA, WOZENFIELD, FARDESTO,
        UNKNOWN
    ) = (
        "ALTAN", "VESCILLO", "BURNTON", "OCTOVALIS",
        "GENNISTORA", "LENDIFORMA", "WOZENFIELD", "FARDESTO",
        ""
    )

def getDistrict(name: str) -> District:
    try:               return District(name)
    except ValueError: return District.UNKNOWN

class ArstotzkanID(Document):
    BACKGROUNDS = None

    TABLE_OFFSET        = (259, 139) 
    DISTRICT_TEXT_COLOR = (217, 189, 247)
    TEXT_COLOR          = ( 61,  57,  77)
    LAYOUT = {
        "label":      getBox(259, 139, 510, 160),
        "district":   getBox(265, 161, 502, 172),
        "last-name":  getBox(359, 179, 502, 190),
        "first-name": getBox(359, 195, 502, 204),
        "birth":      getBox(403, 219, 470, 228),
        "height":     getBox(389, 239, 440, 248),
        "weight":     getBox(389, 259, 440, 270),
        "picture":    getBox(269, 173, 348, 268)
    }

    @staticmethod
    def load():
        ArstotzkanID.BACKGROUNDS = Document.getBgs(
            ArstotzkanID.LAYOUT, ArstotzkanID.TABLE_OFFSET, Image.open(
                os.path.join(ArstotzkanID.TAS.ASSETS, "papers", "arstotzkanID.png")
            ).convert("RGB")
        )

        ArstotzkanID.BACKGROUNDS["label"] = np.asarray(ArstotzkanID.BACKGROUNDS["label"])

    @staticmethod
    def checkMatch(docImg: Image.Image) -> bool:
        return np.array_equal(np.asarray(docImg.crop(ArstotzkanID.LAYOUT["label"])), ArstotzkanID.BACKGROUNDS["label"])
    
    @staticmethod
    def parse(docImg: Image.Image) -> Self:
        return ArstotzkanID(
            district = getDistrict(parseText(
                docImg.crop(ArstotzkanID.LAYOUT["district"]), ArstotzkanID.BACKGROUNDS["district"],
                ArstotzkanID.TAS.FONTS["mini-kylie"], ArstotzkanID.DISTRICT_TEXT_COLOR, PERMIT_PASS_CHARS,
                endAt = " DISTRICT", misalignFix = True
            ).split(" ")[0]),
            name = Name.fromPassportOrID(
                parseText(
                    docImg.crop(ArstotzkanID.LAYOUT["last-name"]), ArstotzkanID.BACKGROUNDS["last-name"],
                    ArstotzkanID.TAS.FONTS["mini-kylie"], ArstotzkanID.TEXT_COLOR, ID_LAST_NAME_CHARS,
                    endAt = ","
                ) + parseText(
                    docImg.crop(ArstotzkanID.LAYOUT["first-name"]), ArstotzkanID.BACKGROUNDS["first-name"],
                    ArstotzkanID.TAS.FONTS["mini-kylie"], ArstotzkanID.TEXT_COLOR, PERMIT_PASS_NAME_CHARS,
                    endAt = "  "
                )
            ),
            birth = parseDate(
                docImg.crop(ArstotzkanID.LAYOUT["birth"]), ArstotzkanID.BACKGROUNDS["birth"],
                ArstotzkanID.TAS.FONTS["mini-kylie"], ArstotzkanID.TEXT_COLOR,
                endAt = "  "
            ),
            height = int(parseText(
                docImg.crop(ArstotzkanID.LAYOUT["height"]), ArstotzkanID.BACKGROUNDS["height"],
                ArstotzkanID.TAS.FONTS["mini-kylie"], ArstotzkanID.TEXT_COLOR, HEIGHT_CHARS,
                endAt = "cm"
            )[:-2]),
            weight = int(parseText(
                docImg.crop(ArstotzkanID.LAYOUT["weight"]), ArstotzkanID.BACKGROUNDS["weight"],
                ArstotzkanID.TAS.FONTS["mini-kylie"], ArstotzkanID.TEXT_COLOR, WEIGHT_CHARS,
                endAt = "kg"
            )[:-2])
        )

    def __init__(self, district, name, birth, height, weight):
        self.district: District = district
        self.name: Name         = name
        self.birth: date        = birth
        self.height: int        = height
        self.weight: int        = weight

    def checkDiscrepancies(self, tas) -> bool:
        if tas.allowWrongWeight and tas.weight != self.weight:
            tas.wrongWeight = True
            return False

        if self.district == District.UNKNOWN or tas.weight != self.weight:
            return True
        
        if ArstotzkanID.TAS.ID_CHECK:
            tas.click(INSPECT_BUTTON)
            tas.click(onTable(centerOf(ArstotzkanID.LAYOUT["picture"])))
            tas.click(PERSON_POS)
            time.sleep(INSPECT_ALPHACHANGE_TIME)
            before = np.asarray(tas.getScreen().crop(TABLE_AREA))
            time.sleep(INSPECT_TIME - INSPECT_ALPHACHANGE_TIME)
            msg = bgFilter(before, np.asarray(tas.getScreen().crop(TABLE_AREA)))
            
            if pg.locate(ArstotzkanID.TAS.MATCHING_DATA, msg) is None:
                tas.click(INSPECT_BUTTON)
                time.sleep(INSPECT_ALPHACHANGE_TIME)
                tas.moveTo(PAPER_SCAN_POS)
                return True
            
            tas.click(onTable(centerOf(ArstotzkanID.LAYOUT["height"])))
            before = np.asarray(tas.getScreen().crop(TABLE_AREA))
            time.sleep(INSPECT_TIME)
            msg = bgFilter(before, np.asarray(tas.getScreen().crop(TABLE_AREA)))

            tas.click(INSPECT_BUTTON)
            time.sleep(INSPECT_ALPHACHANGE_TIME)
            tas.moveTo(PAPER_SCAN_POS)
            return pg.locate(ArstotzkanID.TAS.MATCHING_DATA_LINES, msg, confidence = 0.8) is None

        return False
    
    def checkDiscrepanciesWithReason(self, tas) -> bool:
        if tas.allowWrongWeight and tas.weight != self.weight:
            tas.wrongWeight = True
            return False
        
        if self.confiscatePassportWhen(tas) and not tas.doConfiscate:
            tas.skipReason = True
            return True
        
        if tas.weight != self.weight:
            tas.click(INSPECT_BUTTON)
            tas.click(onTable(centerOf(ArstotzkanID.LAYOUT["weight"])))
            tas.click(centerOf(WEIGHT_AREA))
            time.sleep(INSPECT_INTERROGATE_TIME)
            tas.interrogate()
            tas.moveTo(PAPER_SCAN_POS)
            return True

        if self.district == District.UNKNOWN:
            tas.moveTo(PAPER_SCAN_POS)
            tas.dragTo(RIGHT_SCAN_SLOT)

            tas.moveTo(RULEBOOK_POS)
            tas.dragTo(PAPER_SCAN_POS)
            tas.click(tas.getRulebook()["documents"]["pos"])
            tas.click(tas.getRulebook()["documents"]["id-card"]["pos"])

            tas.moveTo(PAPER_SCAN_POS)
            tas.dragTo(LEFT_SCAN_SLOT)

            tas.click(INSPECT_BUTTON)
            tas.click(onTable(offsetPoint(rightSlot(
                ArstotzkanID.LAYOUT["district"][:2]
            ), (10, 4))))
            tas.click(leftSlot(tas.getRulebook()["documents"]["id-card"]["districts"]))

            ok = not tas.interrogateFailsafe()
            if ok:
                time.sleep(INSPECT_INTERROGATE_TIME - INSPECT_TIME)
                tas.interrogate()

            tas.moveTo(RIGHT_SCAN_SLOT)
            tas.dragTo(PAPER_SCAN_POS)

            tas.moveTo(LEFT_SCAN_SLOT)
            tas.dragTo(PAPER_SCAN_POS)
            tas.putRulebookBack()

            tas.moveTo(PAPER_SCAN_POS)

            if ok: return True
        
        if ArstotzkanID.TAS.ID_CHECK:
            tas.click(INSPECT_BUTTON)
            tas.click(onTable(centerOf(ArstotzkanID.LAYOUT["picture"])))
            tas.click(PERSON_POS)
            time.sleep(INSPECT_ALPHACHANGE_TIME)
            before = np.asarray(tas.getScreen().crop(TABLE_AREA))
            time.sleep(INSPECT_TIME - INSPECT_ALPHACHANGE_TIME)
            msg = bgFilter(before, np.asarray(tas.getScreen().crop(TABLE_AREA)))
            
            if pg.locate(ArstotzkanID.TAS.MATCHING_DATA, msg) is None:
                time.sleep(INSPECT_INTERROGATE_TIME - INSPECT_TIME)
                tas.interrogate()
                tas.moveTo(PAPER_SCAN_POS)
                return True
            
            tas.click(onTable(centerOf(ArstotzkanID.LAYOUT["height"])))
            before = np.asarray(tas.getScreen().crop(TABLE_AREA))
            time.sleep(INSPECT_TIME)
            msg = bgFilter(before, np.asarray(tas.getScreen().crop(TABLE_AREA)))

            if pg.locate(ArstotzkanID.TAS.MATCHING_DATA_LINES, msg, confidence = 0.8) is None:
                time.sleep(INSPECT_INTERROGATE_TIME - INSPECT_TIME)
                tas.interrogate()
                tas.moveTo(PAPER_SCAN_POS)
                return True

            tas.click(INSPECT_BUTTON)
            time.sleep(INSPECT_ALPHACHANGE_TIME)
            tas.moveTo(PAPER_SCAN_POS)

        return False
    
    def confiscatePassportWhen(self, tas) -> bool:
        return ArstotzkanID.TAS.DAY_24 <= tas.date < ArstotzkanID.TAS.DAY_28 and self.district == District.ALTAN
    
    def __repr__(self):
        return f"""==- Arstotzkan ID -==
name:     {self.name}
birth:    {self.birth}
district: {self.district}
height:   {self.height}
weight:   {self.weight}"""