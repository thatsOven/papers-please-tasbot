from PIL      import Image
from datetime import date
import os, numpy as np

from modules.constants.screen   import *
from modules.constants.delays   import *
from modules.constants.other    import *
from modules.documents.document import Document
from modules.textRecognition    import parseText, parseDate
from modules.utils              import *

class EntryPermit(Document):
    BACKGROUNDS = None
    
    TEXT_COLOR = (119, 103, 137)
    LAYOUT = {
        'name': (30, 182, 268, 194),
        'number': (30, 248, 268, 260),
        'purpose': (102, 280, 268, 292),
        'duration': (102, 310, 268, 322),
        'expiration': (158, 340, 224, 352),
        'seal-area': (20, 22, 280, 182),
        'label': (6, 356, 294, 392)
    }

    @staticmethod
    def load():
        EntryPermit.BACKGROUNDS = Document.getBgs(
            EntryPermit.LAYOUT, doubleImage(Image.open(
                os.path.join(EntryPermit.TAS.ASSETS, "papers", "entryPermit.png")
            ).convert("RGB"))
        )

        EntryPermit.BACKGROUNDS["label"] = np.asarray(EntryPermit.BACKGROUNDS["label"])

        sealWhiteBg = EntryPermit.BACKGROUNDS["seal-area"].copy()
        sealWhiteBg.paste((255, 255, 255), (0, 0) + sealWhiteBg.size)
        EntryPermit.BACKGROUNDS["seal-white"] = sealWhiteBg

    @staticmethod
    def checkMatch(docImg: Image.Image) -> bool:
        return np.array_equal(np.asarray(docImg.crop(EntryPermit.LAYOUT["label"])), EntryPermit.BACKGROUNDS["label"])
    
    @Document.field
    def name(self) -> Name:
        return Name.fromPermitOrPass(parseText(
            self.docImg.crop(EntryPermit.LAYOUT["name"]), EntryPermit.BACKGROUNDS["name"],
            EntryPermit.TAS.FONTS["bm-mini"], EntryPermit.TEXT_COLOR, PERMIT_PASS_NAME_CHARS,
            misalignFix = True
        ))
    
    @Document.field
    def number(self) -> str:
        return parseText(
            self.docImg.crop(EntryPermit.LAYOUT["number"]), EntryPermit.BACKGROUNDS["number"],
            EntryPermit.TAS.FONTS["bm-mini"], EntryPermit.TEXT_COLOR, PASSPORT_NUM_CHARS,
            misalignFix = True
        )
    
    @Document.field
    def purpose(self) -> Purpose:
        return Purpose(parseText(
            self.docImg.crop(EntryPermit.LAYOUT["purpose"]), EntryPermit.BACKGROUNDS["purpose"],
            EntryPermit.TAS.FONTS["bm-mini"], EntryPermit.TEXT_COLOR, PERMIT_PASS_CHARS,
            misalignFix = True
        ))
    
    @Document.field
    def duration(self) -> relativedelta:
        return PERMIT_DURATIONS[parseText(
            self.docImg.crop(EntryPermit.LAYOUT["duration"]), EntryPermit.BACKGROUNDS["duration"],
            EntryPermit.TAS.FONTS["bm-mini"], EntryPermit.TEXT_COLOR, PERMIT_PASS_CHARS_NUM,
            misalignFix = True
        )]
    
    @Document.field
    def expiration(self) -> date:
        return parseDate(
            self.docImg.crop(EntryPermit.LAYOUT["expiration"]), EntryPermit.BACKGROUNDS["expiration"],
            EntryPermit.TAS.FONTS["bm-mini"], EntryPermit.TEXT_COLOR
        )
    
    @Document.field
    def sealArea(self) -> Image.Image:
        return self.docImg.crop(EntryPermit.LAYOUT["seal-area"])

    def checkForgery(self, date: date) -> bool:
        if date < EntryPermit.TAS.DAY_11: return False
        
        return all(Document.checkNoSeal(
            np.asarray(self.sealArea), EntryPermit.BACKGROUNDS["seal-area"],
            seal, EntryPermit.BACKGROUNDS["seal-white"]
        ) for seal in EntryPermit.TAS.MOA_SEALS)
    
    def __repr__(self) -> str:
        return f"""==- Entry Permit -==
name:       {self.name}
number:     {self.number}
purpose:    {self.purpose}
duration:   {'FOREVER' if self.duration == PERMIT_DURATIONS['FOREVER'] else self.duration}
expiration: {self.expiration}"""