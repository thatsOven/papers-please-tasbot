from PIL      import Image
from datetime import date
import os, numpy as np

from modules.constants.screen   import *
from modules.constants.delays   import *
from modules.constants.other    import *
from modules.documents.document import Document
from modules.documents.passport import Nation
from modules.textRecognition    import parseText, parseDate
from modules.faceRecognition    import Face, FaceType
from modules.utils              import *

class GrantOfAsylum(Document):
    BACKGROUNDS = None

    TEXT_COLOR = (125, 109, 121)
    LAYOUT = {
        'seal-area': (10, 20, 310, 100),
        'first-name': (146, 108, 300, 120),
        'last-name': (146, 126, 300, 138),
        'nation': (182, 156, 300, 168),
        'number': (182, 174, 300, 186),
        'birth': (202, 192, 268, 204),
        'height': (182, 210, 232, 222),
        'weight': (182, 228, 300, 244),
        'fingerprints': (22, 250, 300, 316),
        'expiration': (182, 326, 248, 338),
        'label': (0, 338, 320, 368),
        'picture': (20, 100, 140, 244)
    }

    @staticmethod
    def load():
        GrantOfAsylum.BACKGROUNDS = Document.getBgs(
            GrantOfAsylum.LAYOUT, doubleImage(Image.open(
                os.path.join(GrantOfAsylum.TAS.ASSETS, "papers", "grantOfAsylum.png")
            ).convert("RGB"))
        )

        GrantOfAsylum.BACKGROUNDS["label"] = np.asarray(GrantOfAsylum.BACKGROUNDS["label"])
        
        sealWhiteBg = GrantOfAsylum.BACKGROUNDS["seal-area"].copy()
        sealWhiteBg.paste((255, 255, 255), (0, 0) + sealWhiteBg.size)
        GrantOfAsylum.BACKGROUNDS["seal-white"] = sealWhiteBg

    @staticmethod
    def checkMatch(docImg: Image.Image) -> bool:
        return np.array_equal(np.asarray(docImg.crop(GrantOfAsylum.LAYOUT["label"])), GrantOfAsylum.BACKGROUNDS["label"])
    
    @Document.field
    def name(self) -> Name:
        return Name(
            parseText(
                self.docImg.crop(GrantOfAsylum.LAYOUT["first-name"]), GrantOfAsylum.BACKGROUNDS["first-name"],
                GrantOfAsylum.TAS.FONTS["bm-mini"], GrantOfAsylum.TEXT_COLOR, PERMIT_PASS_NAME_CHARS,
                endAt = "  "
            ),
            parseText(
                self.docImg.crop(GrantOfAsylum.LAYOUT["last-name"]), GrantOfAsylum.BACKGROUNDS["last-name"],
                GrantOfAsylum.TAS.FONTS["bm-mini"], GrantOfAsylum.TEXT_COLOR, PERMIT_PASS_NAME_CHARS,
                endAt = "  "
            ),
        )
    
    @Document.field
    def nation(self) -> Nation:
        return Nation(parseText(
            self.docImg.crop(GrantOfAsylum.LAYOUT["nation"]), GrantOfAsylum.BACKGROUNDS["nation"],
            GrantOfAsylum.TAS.FONTS["bm-mini"], GrantOfAsylum.TEXT_COLOR, PERMIT_PASS_CHARS,
            endAt = "  "
        ))
    
    @Document.field
    def number(self) -> str:
        return parseText(
            self.docImg.crop(GrantOfAsylum.LAYOUT["number"]), GrantOfAsylum.BACKGROUNDS["number"],
            GrantOfAsylum.TAS.FONTS["bm-mini"], GrantOfAsylum.TEXT_COLOR, PASSPORT_NUM_CHARS,
            endAt = "  "
        )
    
    @Document.field
    def birth(self) -> date:
        return parseDate(
            self.docImg.crop(GrantOfAsylum.LAYOUT["birth"]), GrantOfAsylum.BACKGROUNDS["birth"],
            GrantOfAsylum.TAS.FONTS["bm-mini"], GrantOfAsylum.TEXT_COLOR
        )
    
    @Document.field
    def height(self) -> int:
        return int(parseText(
            self.docImg.crop(GrantOfAsylum.LAYOUT["height"]), GrantOfAsylum.BACKGROUNDS["height"],
            GrantOfAsylum.TAS.FONTS["bm-mini"], GrantOfAsylum.TEXT_COLOR, HEIGHT_CHARS,
            endAt = "cm"
        )[:-2])
    
    @Document.field
    def weight(self) -> int:
        return int(parseText(
            self.docImg.crop(GrantOfAsylum.LAYOUT["weight"]), GrantOfAsylum.BACKGROUNDS["weight"],
            GrantOfAsylum.TAS.FONTS["bm-mini"], GrantOfAsylum.TEXT_COLOR, WEIGHT_CHARS,
            endAt = "kg"
        )[:-2])
    
    @Document.field
    def expiration(self) -> date:
        return parseDate(
            self.docImg.crop(GrantOfAsylum.LAYOUT["expiration"]), GrantOfAsylum.BACKGROUNDS["expiration"],
            GrantOfAsylum.TAS.FONTS["bm-mini"], GrantOfAsylum.TEXT_COLOR
        )
    
    @Document.field
    def sealArea(self) -> Image.Image:
        return self.docImg.crop(GrantOfAsylum.LAYOUT["seal-area"])
    
    # picture face recognition is not yet implemented
    @Document.field
    def face(self) -> Face:
        return Face.parse(self.docImg.crop(GrantOfAsylum.LAYOUT["picture"]), FaceType.GRANT_PICTURE)
    
    # unused for now
    @Document.field
    def fingerprints(self) -> Image.Image:
        return self.docImg.crop(GrantOfAsylum.LAYOUT["fingerprints"])
    
    def checkForgery(self) -> bool:        
        return all(Document.checkNoSeal(
            np.asarray(self.sealArea), GrantOfAsylum.BACKGROUNDS["seal-area"],
            seal, GrantOfAsylum.BACKGROUNDS["seal-white"]
        ) for seal in GrantOfAsylum.TAS.MOA_SEALS)
    
    def __repr__(self) -> str:
        return f"""==- Grant Of Asylum -==
name:       {self.name}
nation:     {self.nation}
number:     {self.number}
birth:      {self.birth}
height:     {self.height}
weight:     {self.weight}
expiration: {self.expiration}
face:       {self.face}"""