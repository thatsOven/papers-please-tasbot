from PIL      import Image
from typing   import Self
import os, numpy as np

from modules.constants.screen   import *
from modules.constants.delays   import *
from modules.constants.other    import *
from modules.documents.passport import Nation
from modules.documents.document import Document
from modules.textRecognition    import parseText
from modules.utils              import *

class DiplomaticAuth(Document):
    BACKGROUNDS = None

    ACCESS_TO_ROWS = 3
    SEALS = {}
    
    TEXT_COLOR = (122, 128, 141)
    LAYOUT = {
        'nation': (68, 8, 210, 20),
        'label': (32, 42, 192, 98),
        'name': (74, 182, 288, 194),
        'number': (98, 206, 288, 218),
        'access-to-0': (42, 304, 282, 318),
        'access-to-1': (42, 322, 282, 336),
        'access-to-2': (42, 340, 282, 354),
        'seal-area': (192, 28, 298, 124)
    }

    @staticmethod
    def load():
        for nation in Nation:
            if nation.value == "ARSTOTZKA": continue

            nationPath = os.path.join(
                DiplomaticAuth.TAS.ASSETS, "papers", "diplomaticAuth", 
                "seals", nation.value.lower()
            )

            DiplomaticAuth.SEALS[Nation(nation.value)] = tuple(
                Image.open(os.path.join(nationPath, file)).convert("RGB")
                for file in os.listdir(nationPath)
            )

        DiplomaticAuth.BACKGROUNDS = Document.getBgs(
            DiplomaticAuth.LAYOUT, doubleImage(Image.open(
                os.path.join(DiplomaticAuth.TAS.ASSETS, "papers", "diplomaticAuth", "inner.png")
            ).convert("RGB"))
        )

        DiplomaticAuth.BACKGROUNDS["label"] = np.asarray(DiplomaticAuth.BACKGROUNDS["label"])
        
        sealWhiteBg = DiplomaticAuth.BACKGROUNDS["seal-area"].copy()
        sealWhiteBg.paste((255, 255, 255), (0, 0) + sealWhiteBg.size)
        DiplomaticAuth.BACKGROUNDS["seal-white"] = sealWhiteBg

    @staticmethod
    def checkMatch(docImg: Image.Image) -> bool:
        return np.array_equal(np.asarray(docImg.crop(DiplomaticAuth.LAYOUT["label"])), DiplomaticAuth.BACKGROUNDS["label"])
    
    @Document.field
    def name(self) -> Name:
        return Name.fromPermitOrPass(parseText(
            self.docImg.crop(DiplomaticAuth.LAYOUT["name"]), DiplomaticAuth.BACKGROUNDS["name"],
            DiplomaticAuth.TAS.FONTS["bm-mini"], DiplomaticAuth.TEXT_COLOR, PERMIT_PASS_NAME_CHARS,
            misalignFix = True
        ))
    
    @Document.field
    def number(self) -> str:
        return parseText(
            self.docImg.crop(DiplomaticAuth.LAYOUT["number"]), DiplomaticAuth.BACKGROUNDS["number"],
            DiplomaticAuth.TAS.FONTS["bm-mini"], DiplomaticAuth.TEXT_COLOR, PASSPORT_NUM_CHARS,
            misalignFix = True
        )
    
    @Document.field
    def nation(self) -> Nation:
        return Nation(parseText(
            self.docImg.crop(DiplomaticAuth.LAYOUT["nation"]), DiplomaticAuth.BACKGROUNDS["nation"],
            DiplomaticAuth.TAS.FONTS["bm-mini"], DiplomaticAuth.TEXT_COLOR, PERMIT_PASS_CHARS,
            endAt = "  "
        ))
    
    @Document.field
    def accessTo(self) -> list[Nation]:
        return [Nation(x.strip()) for x in "".join(
            parseText(
                self.docImg.crop(DiplomaticAuth.LAYOUT[f"access-to-{i}"]), DiplomaticAuth.BACKGROUNDS[f"access-to-{i}"],
                DiplomaticAuth.TAS.FONTS["bm-mini"], DiplomaticAuth.TEXT_COLOR, DIPLOMATIC_AUTH_ACCESS_TO_CHARS,
                endAt = "  "
            ) for i in range(DiplomaticAuth.ACCESS_TO_ROWS)
        ).split(",")]
    
    @Document.field
    def sealArea(self) -> Image.Image:
        return self.docImg.crop(DiplomaticAuth.LAYOUT["seal-area"])

    def checkForgery(self) -> bool:        
        return all(Document.checkNoSeal(
            np.asarray(self.sealArea), DiplomaticAuth.BACKGROUNDS["seal-area"],
            seal, DiplomaticAuth.BACKGROUNDS["seal-white"]
        ) for seal in DiplomaticAuth.SEALS[self.nation])
    
    def __repr__(self) -> str:
        return f"""==- Diplomatic Authorization -==
name:      {self.name}
number:    {self.number}
nation:    {self.nation}
access to: {self.accessTo}"""