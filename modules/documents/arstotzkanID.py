from PIL      import Image
from enum     import Enum
from datetime import date
import os, numpy as np

from modules.constants.screen   import *
from modules.constants.delays   import *
from modules.constants.other    import *
from modules.textRecognition    import parseDate, parseText
from modules.faceRecognition    import Face, FaceType
from modules.documents.document import Document
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

    DISTRICT_TEXT_COLOR = (217, 189, 247)
    TEXT_COLOR          = ( 61,  57,  77)
    LAYOUT = {
        'label': (10, 0, 240, 22),
        'district': (6, 22, 244, 34),
        'last-name': (100, 40, 244, 52),
        'first-name': (100, 56, 244, 66),
        'birth': (144, 80, 212, 90),
        'height': (130, 100, 182, 110),
        'weight': (130, 120, 182, 132),
        'picture': (10, 34, 90, 130)
    }

    @staticmethod
    def load():
        ArstotzkanID.BACKGROUNDS = Document.getBgs(
            ArstotzkanID.LAYOUT, doubleImage(Image.open(
                os.path.join(ArstotzkanID.TAS.ASSETS, "papers", "arstotzkanID.png")
            ).convert("RGB"))
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
    
    # picture face recognition is not yet implemented
    @Document.field
    def face(self) -> Face:
        return Face.parse(self.docImg.crop(ArstotzkanID.LAYOUT["picture"]), FaceType.ID_PICTURE)

    def __repr__(self):
        return f"""==- Arstotzkan ID -==
name:     {self.name}
birth:    {self.birth}
district: {self.district}
height:   {self.height}
weight:   {self.weight}
face:     {self.face}"""