from PIL      import Image
from datetime import date
import os, numpy as np

from modules.constants.screen   import *
from modules.constants.delays   import *
from modules.constants.other    import *
from modules.documents.passport import Nation
from modules.documents.document import Document
from modules.textRecognition    import parseText, parseDate
from modules.utils              import *

class AccessPermit(Document):
    BACKGROUNDS = None

    TEXT_COLOR = (105, 103, 137)
    LAYOUT = {
        'seal-area': (20, 20, 274, 108),
        'name': (30, 108, 264, 120),
        'nation': (32, 152, 142, 164),
        'number': (158, 152, 274, 164),
        'purpose': (32, 196, 142, 208),
        'duration': (158, 196, 274, 208),
        'height': (32, 240, 82, 252),
        'weight': (158, 240, 207, 256),
        'description': (32, 284, 264, 296),
        'expiration': (178, 328, 244, 340),
        'label': (6, 340, 288, 386)
    }

    @staticmethod
    def load():
        AccessPermit.BACKGROUNDS = Document.getBgs(
            AccessPermit.LAYOUT, doubleImage(Image.open(
                os.path.join(AccessPermit.TAS.ASSETS, "papers", "accessPermit.png")
            ).convert("RGB"))
        )

        AccessPermit.BACKGROUNDS["label"] = np.asarray(AccessPermit.BACKGROUNDS["label"])

        sealWhiteBg = AccessPermit.BACKGROUNDS["seal-area"].copy()
        sealWhiteBg.paste((255, 255, 255), (0, 0) + sealWhiteBg.size)
        AccessPermit.BACKGROUNDS["seal-white"] = sealWhiteBg

    @staticmethod
    def checkMatch(docImg: Image.Image) -> bool:
        return np.array_equal(np.asarray(docImg.crop(AccessPermit.LAYOUT["label"])), AccessPermit.BACKGROUNDS["label"])
    
    @Document.field
    def name(self) -> Name:
        return Name.fromPermitOrPass(parseText(
            self.docImg.crop(AccessPermit.LAYOUT["name"]), AccessPermit.BACKGROUNDS["name"],
            AccessPermit.TAS.FONTS["bm-mini"], AccessPermit.TEXT_COLOR, PERMIT_PASS_NAME_CHARS,
            misalignFix = True
        ))
    
    @Document.field
    def nation(self) -> Nation:
        return Nation(parseText(
            self.docImg.crop(AccessPermit.LAYOUT["nation"]), AccessPermit.BACKGROUNDS["nation"],
            AccessPermit.TAS.FONTS["bm-mini"], AccessPermit.TEXT_COLOR, PERMIT_PASS_CHARS,
            endAt = "  "
        ))
    
    @Document.field
    def number(self) -> str:
        return parseText(
            self.docImg.crop(AccessPermit.LAYOUT["number"]), AccessPermit.BACKGROUNDS["number"],
            AccessPermit.TAS.FONTS["bm-mini"], AccessPermit.TEXT_COLOR, PASSPORT_NUM_CHARS,
            endAt = "  "
        )
    
    @Document.field
    def purpose(self) -> Purpose:
        return Purpose(parseText(
            self.docImg.crop(AccessPermit.LAYOUT["purpose"]), AccessPermit.BACKGROUNDS["purpose"],
            AccessPermit.TAS.FONTS["bm-mini"], AccessPermit.TEXT_COLOR, PERMIT_PASS_CHARS,
            endAt = "  "
        ))
    
    @Document.field
    def duration(self) -> relativedelta:
        return PERMIT_DURATIONS[parseText(
            self.docImg.crop(AccessPermit.LAYOUT["duration"]), AccessPermit.BACKGROUNDS["duration"],
            AccessPermit.TAS.FONTS["bm-mini"], AccessPermit.TEXT_COLOR, PERMIT_PASS_CHARS_NUM,
            endAt = "  "
        )]
    
    @Document.field
    def height(self) -> int:
        return int(parseText(
            self.docImg.crop(AccessPermit.LAYOUT["height"]), AccessPermit.BACKGROUNDS["height"],
            AccessPermit.TAS.FONTS["bm-mini"], AccessPermit.TEXT_COLOR, HEIGHT_CHARS,
            endAt = "cm"
        )[:-2])
    
    @Document.field
    def weight(self) -> int:
        return int(parseText(
            self.docImg.crop(AccessPermit.LAYOUT["weight"]), AccessPermit.BACKGROUNDS["weight"],
            AccessPermit.TAS.FONTS["bm-mini"], AccessPermit.TEXT_COLOR, WEIGHT_CHARS,
            endAt = "kg"
        )[:-2])
    
    @Document.field
    def expiration(self) -> date:
        return parseDate(
            self.docImg.crop(AccessPermit.LAYOUT["expiration"]), AccessPermit.BACKGROUNDS["expiration"],
            AccessPermit.TAS.FONTS["bm-mini"], AccessPermit.TEXT_COLOR
        )
    
    @Document.field
    def description(self) -> Description:
        return Description(parseText(
            self.docImg.crop(AccessPermit.LAYOUT["description"]), AccessPermit.BACKGROUNDS["description"],
            AccessPermit.TAS.FONTS["bm-mini"], AccessPermit.TEXT_COLOR, DESCRIPTION_CHARS,
            endAt = "  "
        ))
    
    @Document.field
    def sealArea(self) -> Image.Image:
        return self.docImg.crop(AccessPermit.LAYOUT["seal-area"])

    def checkForgery(self) -> bool:        
        return all(Document.checkNoSeal(
            np.asarray(self.sealArea), AccessPermit.BACKGROUNDS["seal-area"],
            seal, AccessPermit.BACKGROUNDS["seal-white"]
        ) for seal in AccessPermit.TAS.MOA_SEALS)
    
    def __repr__(self) -> str:
        return f"""==- Access Permit -==
name:        {self.name}
nation:      {self.nation}
number:      {self.number}
purpose:     {self.purpose}
duration:    {'FOREVER' if self.duration == PERMIT_DURATIONS['FOREVER'] else self.duration}
height:      {self.height}
weight:      {self.weight}
description: {self.description}
expiration:  {self.expiration}"""