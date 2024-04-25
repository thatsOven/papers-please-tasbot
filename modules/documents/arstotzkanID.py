from PIL      import Image
from enum     import Enum
from datetime import date
import os, numpy as np

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

    @Document.field
    def name(self) -> Name:
        return Name.fromPassportOrID(
            parseText(
                self.docImg.crop(ArstotzkanID.LAYOUT["last-name"]), ArstotzkanID.BACKGROUNDS["last-name"],
                ArstotzkanID.TAS.FONTS["mini-kylie"], ArstotzkanID.TEXT_COLOR, ID_LAST_NAME_CHARS,
                endAt = ","
            ) + parseText(
                self.docImg.crop(ArstotzkanID.LAYOUT["first-name"]), ArstotzkanID.BACKGROUNDS["first-name"],
                ArstotzkanID.TAS.FONTS["mini-kylie"], ArstotzkanID.TEXT_COLOR, PERMIT_PASS_NAME_CHARS,
                endAt = "  "
            )
        )
    
    @Document.field
    def district(self) -> District:
        return getDistrict(parseText(
            self.docImg.crop(ArstotzkanID.LAYOUT["district"]), ArstotzkanID.BACKGROUNDS["district"],
            ArstotzkanID.TAS.FONTS["mini-kylie"], ArstotzkanID.DISTRICT_TEXT_COLOR, PERMIT_PASS_CHARS,
            endAt = " DISTRICT", misalignFix = True
        ).split(" ")[0])
    
    @Document.field
    def birth(self) -> date:
        return parseDate(
            self.docImg.crop(ArstotzkanID.LAYOUT["birth"]), ArstotzkanID.BACKGROUNDS["birth"],
            ArstotzkanID.TAS.FONTS["mini-kylie"], ArstotzkanID.TEXT_COLOR,
            endAt = "  "
        )
    
    @Document.field
    def height(self) -> int:
        return int(parseText(
            self.docImg.crop(ArstotzkanID.LAYOUT["height"]), ArstotzkanID.BACKGROUNDS["height"],
            ArstotzkanID.TAS.FONTS["mini-kylie"], ArstotzkanID.TEXT_COLOR, HEIGHT_CHARS,
            endAt = "cm"
        )[:-2])
    
    @Document.field
    def weight(self) -> int:
        return int(parseText(
            self.docImg.crop(ArstotzkanID.LAYOUT["weight"]), ArstotzkanID.BACKGROUNDS["weight"],
            ArstotzkanID.TAS.FONTS["mini-kylie"], ArstotzkanID.TEXT_COLOR, WEIGHT_CHARS,
            endAt = "kg"
        )[:-2])

    def __repr__(self):
        return f"""==- Arstotzkan ID -==
name:     {self.name}
birth:    {self.birth}
district: {self.district}
height:   {self.height}
weight:   {self.weight}"""