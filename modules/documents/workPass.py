from PIL      import Image
from enum     import Enum
from typing   import Self
from datetime import date
import os, numpy as np

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
    
    @Document.field
    def name(self) -> Name:
        return Name.fromPermitOrPass(parseText(
            self.docImg.crop(WorkPass.LAYOUT["name"]), WorkPass.BACKGROUNDS["name"],
            WorkPass.TAS.FONTS["bm-mini"], WorkPass.TEXT_COLOR, PERMIT_PASS_NAME_CHARS,
            misalignFix = True
        ))
    
    @Document.field
    def field(self) -> Field:
        return Field(parseText(
            self.docImg.crop(WorkPass.LAYOUT["field"]), WorkPass.BACKGROUNDS["field"],
            WorkPass.TAS.FONTS["bm-mini"], WorkPass.TEXT_COLOR, WORK_PASS_FIELD_CHARS,
            misalignFix = True
        ))
    
    @Document.field
    def until(self) -> date:
        return parseDate(
            self.docImg.crop(WorkPass.LAYOUT["until"]), WorkPass.BACKGROUNDS["until"],
            WorkPass.TAS.FONTS["bm-mini"], WorkPass.TEXT_COLOR
        )
    
    @Document.field
    def sealArea(self) -> Image.Image:
        return self.docImg.crop(WorkPass.LAYOUT["seal-area"])

    def checkForgery(self, date: date) -> bool:
        if date < WorkPass.TAS.DAY_11: return False

        return all(Document.checkNoSeal(
            np.asarray(self.sealArea), WorkPass.BACKGROUNDS["seal-area"],
            seal, WorkPass.BACKGROUNDS["seal-white"]
        ) for seal in WorkPass.SEALS)
    
    def __repr__(self) -> str:
        return f"""==- Work Pass -==
name:  {self.name}
field: {self.field}
until: {self.until}"""