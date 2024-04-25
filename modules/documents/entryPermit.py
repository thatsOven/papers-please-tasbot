from PIL      import Image
from datetime import date
import os, numpy as np

from modules.constants.screen   import *
from modules.constants.delays   import *
from modules.constants.other    import *
from modules.documents.document import Document, getBox
from modules.textRecognition    import parseText, parseDate
from modules.utils              import *

class EntryPermit(Document):
    BACKGROUNDS = None
    
    TABLE_OFFSET = (235, 9) 
    TEXT_COLOR   = (119, 103, 137)
    LAYOUT = {
        "name":       getBox(265, 191, 502, 202),
        "number":     getBox(265, 257, 502, 268),
        "purpose":    getBox(337, 289, 502, 300),
        "duration":   getBox(337, 319, 502, 330),
        "expiration": getBox(393, 349, 458, 360),
        "seal-area":  getBox(255,  31, 514, 190),
        "label":      getBox(241, 365, 528, 400)
    }

    @staticmethod
    def load():
        EntryPermit.BACKGROUNDS = Document.getBgs(
            EntryPermit.LAYOUT, EntryPermit.TABLE_OFFSET, Image.open(
                os.path.join(EntryPermit.TAS.ASSETS, "papers", "entryPermit.png")
            ).convert("RGB")
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