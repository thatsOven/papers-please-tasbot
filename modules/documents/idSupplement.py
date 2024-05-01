from PIL      import Image
from typing   import Self
from datetime import date
import os, numpy as np

from modules.constants.screen   import *
from modules.constants.delays   import *
from modules.constants.other    import *
from modules.textRecognition    import parseDate, parseText
from modules.documents.document import Document
from modules.utils              import *

class IDSupplement(Document):
    BACKGROUNDS = None

    EXPIRATION_TEXT_COLOR = (181, 18,  6)
    TEXT_COLOR            = ( 78, 69, 79)
    LAYOUT = {
        'label': (32, 16, 172, 64),
        'height': (100, 64, 150, 76),
        'weight': (100, 86, 150, 102),
        'description-0': (20, 132, 162, 144),
        'description-1': (20, 148, 162, 160),
        'thumb-area': (74, 183, 162, 252),
        'expiration': (92, 278, 158, 290)
    }

    @staticmethod
    def load():
        IDSupplement.BACKGROUNDS = Document.getBgs(
            IDSupplement.LAYOUT, Image.open(
                os.path.join(IDSupplement.TAS.ASSETS, "papers", "idSupplement.png")
            ).convert("RGB")
        )

        IDSupplement.BACKGROUNDS["label"] = np.asarray(IDSupplement.BACKGROUNDS["label"])

    @staticmethod
    def checkMatch(docImg: Image.Image) -> bool:
        return np.array_equal(np.asarray(docImg.crop(IDSupplement.LAYOUT["label"])), IDSupplement.BACKGROUNDS["label"])
    
    @Document.field
    def height(self) -> int:
        return int(parseText(
            self.docImg.crop(IDSupplement.LAYOUT["height"]), IDSupplement.BACKGROUNDS["height"],
            IDSupplement.TAS.FONTS["bm-mini"], IDSupplement.TEXT_COLOR, HEIGHT_CHARS,
            endAt = "cm"
        )[:-2])
    
    @Document.field
    def weight(self) -> int:
        return int(parseText(
            self.docImg.crop(IDSupplement.LAYOUT["weight"]), IDSupplement.BACKGROUNDS["weight"],
            IDSupplement.TAS.FONTS["bm-mini"], IDSupplement.TEXT_COLOR, WEIGHT_CHARS,
            endAt = "kg"
        )[:-2])
    
    @Document.field
    def expiration(self) -> date:
        return parseDate(
            self.docImg.crop(IDSupplement.LAYOUT["expiration"]), IDSupplement.BACKGROUNDS["expiration"],
            IDSupplement.TAS.FONTS["bm-mini"], IDSupplement.EXPIRATION_TEXT_COLOR
        )
    
    @Document.field
    def description(self) -> Description:
        return Description((
            parseText(
                self.docImg.crop(IDSupplement.LAYOUT["description-0"]), IDSupplement.BACKGROUNDS["description-0"],
                IDSupplement.TAS.FONTS["bm-mini"], IDSupplement.TEXT_COLOR, PERMIT_PASS_NAME_CHARS,
                endAt = "  "
            ) + " " + 
            parseText(
                self.docImg.crop(IDSupplement.LAYOUT["description-1"]), IDSupplement.BACKGROUNDS["description-1"],
                IDSupplement.TAS.FONTS["bm-mini"], IDSupplement.TEXT_COLOR, PERMIT_PASS_NAME_CHARS,
                endAt = "  "
            )
        ).strip())
    
    # unused
    @Document.field
    def thumb(self) -> Image.Image:
        return self.docImg.crop(IDSupplement.LAYOUT["thumb-area"])
    
    def __repr__(self) -> str:
        return f"""==- Identity Supplement -==
height:     {self.height}
weight:     {self.weight}
expiration: {self.expiration}"""