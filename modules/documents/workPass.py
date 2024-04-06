from PIL      import Image
from enum     import Enum
from typing   import Self
from datetime import date
import os, time, numpy as np

from modules.constants.other    import *
from modules.constants.screen   import *
from modules.constants.delays   import *
from modules.textRecognition    import parseDate, parseText
from modules.documents.document import Document, getBox
from modules.utils              import *

# not really necessary, but whatever
class Field(Enum):
    (
        ACCOUNTING, AGRICULTURE, ARCHITECTURE, AVIATION,
        CONSTRUCTION, DENTISTRY, DRAFTING, ENGINEERING,
        FINE_ARTS, FISHING, FOOD_SERVICE, GENERAL_LABOR,
        HEALTHCARE, MANUFACTURING, RESEARCH, SPORTS,
        STATISTICS, SURVEYING
    ) = (
        "ACCOUNTING", "AGRICULTURE", "ARCHITECTURE", "AVIATION",
        "CONSTRUCTION", "DENTISTRY", "DRAFTING", "ENGINEERING",
        "FINE-ARTS", "FISHING", "FOOD-SERVICE", "GENERAL-LABOR",
        "HEALTH-CARE", "MANUFACTURING", "RESEARCH", "SPORTS",
        "STATISTICS", "SURVEYING"
    )

class WorkPass(Document):
    BACKGROUNDS = None

    SEALS = None

    TABLE_OFFSET = (239, 75)
    TEXT_COLOR   = (137, 106, 103)
    LAYOUT = {
        "name":      getBox(313, 209, 516, 220),
        "field":     getBox(313, 239, 516, 250),
        "until":     getBox(389, 269, 455, 280),
        "label":     getBox(239, 281, 532, 344),
        "seal-area": getBox(251,  89, 518, 208)
    }

    @staticmethod
    def load():
        sealsPath = os.path.join(WorkPass.TAS.ASSETS, "papers", "workPass", "seals")
        WorkPass.SEALS = tuple(
            Image.open(os.path.join(sealsPath, file)).convert("RGB") 
            for file in os.listdir(sealsPath)
        )

        WorkPass.BACKGROUNDS = Document.getBgs(
            WorkPass.LAYOUT, WorkPass.TABLE_OFFSET, Image.open(
                os.path.join(WorkPass.TAS.ASSETS, "papers", "workPass", "inner.png")
            ).convert("RGB")
        )

        WorkPass.BACKGROUNDS["label"] = np.asarray(WorkPass.BACKGROUNDS["label"])
        
        sealWhiteBg = WorkPass.BACKGROUNDS["seal-area"].copy()
        sealWhiteBg.paste((255, 255, 255), (0, 0) + sealWhiteBg.size)
        WorkPass.BACKGROUNDS["seal-white"] = sealWhiteBg

    @staticmethod
    def checkMatch(docImg: Image.Image) -> bool:
        return np.array_equal(np.asarray(docImg.crop(WorkPass.LAYOUT["label"])), WorkPass.BACKGROUNDS["label"])
    
    @staticmethod
    def parse(docImg: Image.Image) -> Self:
        return WorkPass(
            name = Name.fromPermitOrPass(parseText(
                docImg.crop(WorkPass.LAYOUT["name"]), WorkPass.BACKGROUNDS["name"],
                WorkPass.TAS.FONTS["bm-mini"], WorkPass.TEXT_COLOR, PERMIT_PASS_NAME_CHARS,
                misalignFix = True
            )),
            field = Field(parseText(
                docImg.crop(WorkPass.LAYOUT["field"]), WorkPass.BACKGROUNDS["field"],
                WorkPass.TAS.FONTS["bm-mini"], WorkPass.TEXT_COLOR, WORK_PASS_FIELD_CHARS,
                misalignFix = True
            )),
            until = parseDate(
                docImg.crop(WorkPass.LAYOUT["until"]), WorkPass.BACKGROUNDS["until"],
                WorkPass.TAS.FONTS["bm-mini"], WorkPass.TEXT_COLOR
            ),
            sealArea = docImg.crop(WorkPass.LAYOUT["seal-area"])
        )
    
    def __init__(self, name, field, until, sealArea):
        self.name: Name            = name
        self.field: Field          = field
        self.until: date           = until
        self.sealArea: Image.Image = sealArea

    def __checkForgery(self, date: date) -> bool:
        if date < WorkPass.TAS.DAY_11: return False

        return all(Document.checkNoSeal(
            np.asarray(self.sealArea), WorkPass.BACKGROUNDS["seal-area"],
            seal, WorkPass.BACKGROUNDS["seal-white"]
        ) for seal in WorkPass.SEALS)
    
    def checkDiscrepancies(self, tas) -> bool:
        # just an optimization, not really necessary
        if self.until < tas.date + PERMIT_DURATIONS["1 MONTH"]: return True
        return self.__checkForgery(tas.date)
    
    def checkDiscrepanciesWithReason(self, tas) -> bool:
        if self.until < tas.date + PERMIT_DURATIONS["1 MONTH"]: 
            tas.click(INSPECT_BUTTON)
            tas.click(centerOf(WorkPass.LAYOUT["until"]))
            tas.click(CLOCK_POS)
            time.sleep(INSPECT_INTERROGATE_TIME)
            tas.interrogate()
            tas.moveTo(PAPER_SCAN_POS)
            return True

        if self.__checkForgery(tas.date):
            tas.moveTo(PAPER_SCAN_POS)
            tas.dragTo(RIGHT_SCAN_SLOT)

            tas.moveTo(RULEBOOK_POS)
            tas.dragTo(PAPER_SCAN_POS)
            tas.click(tas.getRulebook()["documents"]["pos"])
            tas.click(tas.getRulebook()["documents"]["work-pass"]["pos"])

            tas.moveTo(PAPER_SCAN_POS)
            tas.dragTo(LEFT_SCAN_SLOT)

            tas.click(INSPECT_BUTTON)

            # if there's no seal
            if not bgFilter(np.asarray(self.sealArea), np.asarray(WorkPass.BACKGROUNDS["seal-area"])).any():
                tas.click(onTable(rightSlot(centerOf(WorkPass.LAYOUT["seal-area"]))))
                tas.click(leftSlot(tas.getRulebook()["documents"]["work-pass"]["document-must-have-seal"]))
            else:
                try:
                    pos = Document.sealPos(
                        np.asarray(self.sealArea), WorkPass.BACKGROUNDS["seal-area"],
                        WorkPass.BACKGROUNDS["seal-white"]
                    )
                except:
                    tas.click(onTable(rightSlot(centerOf(WorkPass.LAYOUT["seal-area"]))))
                    tas.click(leftSlot(tas.getRulebook()["documents"]["work-pass"]["document-must-have-seal"]))
                else:
                    tas.click(onTable(rightSlot(offsetPoint(textFieldOffset(pos), WorkPass.LAYOUT["seal-area"][:2]))))
                    tas.click(leftSlot(tas.getRulebook()["documents"]["work-pass"]["seals"]))

            time.sleep(INSPECT_INTERROGATE_TIME)
            tas.interrogate()

            tas.moveTo(RIGHT_SCAN_SLOT)
            tas.dragTo(PAPER_SCAN_POS)

            tas.moveTo(LEFT_SCAN_SLOT)
            tas.dragTo(PAPER_SCAN_POS)

            tas.putRulebookBack()
            tas.moveTo(PAPER_SCAN_POS)
            return True

        return False
    
    def __repr__(self) -> str:
        return f"""==- Work Pass -==
name:  {self.name}
field: {self.field}
until: {self.until}"""