from PIL      import Image
from enum     import Enum
from typing   import Self
from datetime import date
import os, numpy as np

from modules.constants.screen   import *
from modules.constants.delays   import *
from modules.constants.other    import *
from modules.documents.document import Document, getBox
from modules.textRecognition    import parseText, parseDate
from modules.utils              import *

# not really necessary, but whatever
class Disease(Enum):
    (
        CHOLERA, COWPOX, HEP_B, HPV, MEASLES, POLIO, 
        RUBELLA, TETANUS, TUBERC, TYPHUS, YEL_FEV
    ) = (
        "CHOLERA", "COWPOX", "HEP-B", "HPV", "MEASLES", "POLIO", 
        "RUBELLA", "TETANUS", "TUBERC.", "TYPHUS", "YEL.FEV."
    )

class Vaccine:
    BACKGROUNDS = None
    LAYOUT = {
        "date":    getBox( 6, 6,  71, 17),
        "disease": getBox(94, 6, 201, 17)
    }

    @staticmethod
    def load(fullBg: Image.Image):
        Vaccine.BACKGROUNDS = Document.getBgs(Vaccine.LAYOUT, (0, 0), fullBg)
        Vaccine.BACKGROUNDS["full"] = np.asarray(fullBg)

    @staticmethod
    def parse(vaccineImg: Image.Image) -> Self | None:
        if np.array_equal(np.asarray(vaccineImg), Vaccine.BACKGROUNDS["full"]):
            return None
        
        return Vaccine(
            disease = Disease(parseText(
                vaccineImg.crop(Vaccine.LAYOUT["disease"]), Vaccine.BACKGROUNDS["disease"],
                VaxCert.TAS.FONTS["bm-mini"], VaxCert.TEXT_COLOR, DISEASE_CHARS,
                endAt = "  "
            )),
            date_ = parseDate(
                vaccineImg.crop(Vaccine.LAYOUT["date"]), Vaccine.BACKGROUNDS["date"],
                VaxCert.TAS.FONTS["bm-mini"], VaxCert.TEXT_COLOR
            )
        )

    def __init__(self, disease, date_):
        self.disease: Disease = disease
        self.date: date       = date_

    def __repr__(self):
        return f"Vaccine({self.disease}, {self.date})"
    
class VaxCert(Document):
    BACKGROUNDS = None

    N_VACCINES = 3

    TABLE_OFFSET = (251, 55) 
    TEXT_COLOR   = (101, 88, 114)
    LAYOUT = {
        "label":  getBox(253,  57, 518, 156),
        "name":   getBox(265, 157, 506, 168),
        "number": getBox(305, 183, 506, 194),
        "vax-0":  getBox(285, 239, 486, 260),
        "vax-1":  getBox(285, 263, 486, 284),
        "vax-2":  getBox(285, 287, 486, 308),
    }

    @staticmethod
    def load():
        VaxCert.BACKGROUNDS = Document.getBgs(
            VaxCert.LAYOUT, VaxCert.TABLE_OFFSET, Image.open(
                os.path.join(VaxCert.TAS.ASSETS, "papers", "vaxCert.png")
            ).convert("RGB")
        )

        VaxCert.BACKGROUNDS["label"] = np.asarray(VaxCert.BACKGROUNDS["label"])
        Vaccine.load(VaxCert.BACKGROUNDS["vax-0"])

    @staticmethod
    def checkMatch(docImg: Image.Image) -> bool:
        return np.array_equal(np.asarray(docImg.crop(VaxCert.LAYOUT["label"])), VaxCert.BACKGROUNDS["label"])
    
    @staticmethod
    def parse(docImg: Image.Image) -> Self:
        vaxCert = VaxCert(
            name = Name.fromPermitOrPass(parseText(
                docImg.crop(VaxCert.LAYOUT["name"]), VaxCert.BACKGROUNDS["name"],
                VaxCert.TAS.FONTS["bm-mini"], VaxCert.TEXT_COLOR, PERMIT_PASS_NAME_CHARS,
                misalignFix = True
            )),
            number = parseText(
                docImg.crop(VaxCert.LAYOUT["number"]), VaxCert.BACKGROUNDS["number"],
                VaxCert.TAS.FONTS["bm-mini"], VaxCert.TEXT_COLOR, PASSPORT_NUM_CHARS,
                misalignFix = True
            ),
            vaccines = []
        )

        for i in range(VaxCert.N_VACCINES):
            vax = Vaccine.parse(docImg.crop(VaxCert.LAYOUT[f"vax-{i}"]))
            if vax is None: break
            vaxCert.vaccines.append(vax)

        return vaxCert

    def __init__(self, name, number, vaccines):
        self.name: Name              = name
        self.number                  = number
        self.vaccines: list[Vaccine] = vaccines
    
    def __repr__(self) -> str:
        return f"""==- Certificate Of Vaccination -==
name:     {self.name}
number:   {self.number}
vaccines: {self.vaccines}"""