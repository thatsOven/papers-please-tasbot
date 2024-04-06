from PIL      import Image
from typing   import Self
from datetime import date
import os, time, numpy as np, pyautogui as pg

from modules.constants.screen   import *
from modules.constants.delays   import *
from modules.constants.other    import *
from modules.documents.passport import Nation
from modules.documents.document import Document, getBox
from modules.textRecognition    import parseText, parseDate
from modules.utils              import *

class AccessPermit(Document):
    BACKGROUNDS = None

    TABLE_OFFSET = (239, 15) 
    TEXT_COLOR   = (105, 103, 137)
    LAYOUT = {
        "seal-area":   getBox(259,  35, 512, 122),
        "name":        getBox(269, 123, 502, 134),
        "nation":      getBox(271, 167, 380, 178),
        "number":      getBox(397, 167, 512, 178),
        "purpose":     getBox(271, 211, 380, 222),
        "duration":    getBox(397, 211, 512, 222),
        "height":      getBox(271, 255, 320, 266),
        "weight":      getBox(397, 255, 445, 270),
        "description": getBox(271, 299, 502, 310),
        "expiration":  getBox(417, 343, 482, 354),
        "label":       getBox(245, 355, 526, 400)
    }

    @staticmethod
    def load():
        AccessPermit.BACKGROUNDS = Document.getBgs(
            AccessPermit.LAYOUT, AccessPermit.TABLE_OFFSET, Image.open(
                os.path.join(AccessPermit.TAS.ASSETS, "papers", "accessPermit.png")
            ).convert("RGB")
        )

        AccessPermit.BACKGROUNDS["label"] = np.asarray(AccessPermit.BACKGROUNDS["label"])

        sealWhiteBg = AccessPermit.BACKGROUNDS["seal-area"].copy()
        sealWhiteBg.paste((255, 255, 255), (0, 0) + sealWhiteBg.size)
        AccessPermit.BACKGROUNDS["seal-white"] = sealWhiteBg

    @staticmethod
    def checkMatch(docImg: Image.Image) -> bool:
        return np.array_equal(np.asarray(docImg.crop(AccessPermit.LAYOUT["label"])), AccessPermit.BACKGROUNDS["label"])
    
    @staticmethod
    def parse(docImg: Image.Image) -> Self:
        return AccessPermit(
            name = Name.fromPermitOrPass(parseText(
                docImg.crop(AccessPermit.LAYOUT["name"]), AccessPermit.BACKGROUNDS["name"],
                AccessPermit.TAS.FONTS["bm-mini"], AccessPermit.TEXT_COLOR, PERMIT_PASS_NAME_CHARS,
                misalignFix = True
            )),
            nation = Nation(parseText(
                docImg.crop(AccessPermit.LAYOUT["nation"]), AccessPermit.BACKGROUNDS["nation"],
                AccessPermit.TAS.FONTS["bm-mini"], AccessPermit.TEXT_COLOR, PERMIT_PASS_CHARS,
                endAt = "  "
            )),
            number = parseText(
                docImg.crop(AccessPermit.LAYOUT["number"]), AccessPermit.BACKGROUNDS["number"],
                AccessPermit.TAS.FONTS["bm-mini"], AccessPermit.TEXT_COLOR, PASSPORT_NUM_CHARS,
                endAt = "  "
            ),
            purpose = Purpose(parseText(
                docImg.crop(AccessPermit.LAYOUT["purpose"]), AccessPermit.BACKGROUNDS["purpose"],
                AccessPermit.TAS.FONTS["bm-mini"], AccessPermit.TEXT_COLOR, PERMIT_PASS_CHARS,
                endAt = "  "
            )),
            duration = PERMIT_DURATIONS[parseText(
                docImg.crop(AccessPermit.LAYOUT["duration"]), AccessPermit.BACKGROUNDS["duration"],
                AccessPermit.TAS.FONTS["bm-mini"], AccessPermit.TEXT_COLOR, PERMIT_PASS_CHARS_NUM,
                endAt = "  "
            )],
            height = int(parseText(
                docImg.crop(AccessPermit.LAYOUT["height"]), AccessPermit.BACKGROUNDS["height"],
                AccessPermit.TAS.FONTS["bm-mini"], AccessPermit.TEXT_COLOR, HEIGHT_CHARS,
                endAt = "cm"
            )[:-2]),
            weight = int(parseText(
                docImg.crop(AccessPermit.LAYOUT["weight"]), AccessPermit.BACKGROUNDS["weight"],
                AccessPermit.TAS.FONTS["bm-mini"], AccessPermit.TEXT_COLOR, WEIGHT_CHARS,
                endAt = "kg"
            )[:-2]),
            expiration = parseDate(
                docImg.crop(AccessPermit.LAYOUT["expiration"]), AccessPermit.BACKGROUNDS["expiration"],
                AccessPermit.TAS.FONTS["bm-mini"], AccessPermit.TEXT_COLOR
            ),
            description = docImg.crop(AccessPermit.LAYOUT["description"]),
            sealArea    = docImg.crop(AccessPermit.LAYOUT["seal-area"])
        )
    
    def __init__(self, name, nation, number, purpose, duration, height, weight, description, expiration, sealArea):
        self.name: Name            = name
        self.nation: Nation        = nation
        self.number                = number
        self.purpose: Purpose      = purpose
        self.duration: date        = duration
        self.height                = height
        self.weight                = weight
        self.description           = description
        self.expiration: date      = expiration
        self.sealArea: Image.Image = sealArea

    def __checkForgery(self) -> bool:        
        return all(Document.checkNoSeal(
            np.asarray(self.sealArea), AccessPermit.BACKGROUNDS["seal-area"],
            seal, AccessPermit.BACKGROUNDS["seal-white"]
        ) for seal in AccessPermit.TAS.MOA_SEALS)
    
    def checkDiscrepancies(self, _) -> bool:
        return True # this is never called
    
    def checkDiscrepanciesWithReason(self, tas) -> bool:    
        if tas.allowWrongWeight and tas.weight != self.weight:
            tas.wrongWeight = True
            return False
        
        if self.expiration <= tas.date:
            tas.click(INSPECT_BUTTON)
            tas.click(onTable(centerOf(AccessPermit.LAYOUT["expiration"])))
            tas.click(CLOCK_POS)
            time.sleep(INSPECT_INTERROGATE_TIME)
            tas.interrogate()
            tas.moveTo(PAPER_SCAN_POS)
            return True
        
        if tas.weight != self.weight:
            tas.click(INSPECT_BUTTON)
            tas.click(onTable(centerOf(AccessPermit.LAYOUT["weight"])))
            tas.click(centerOf(WEIGHT_AREA))
            time.sleep(INSPECT_INTERROGATE_TIME)
            tas.interrogate()
            tas.moveTo(PAPER_SCAN_POS)
            return True
        
        if self.__checkForgery():
            tas.moveTo(PAPER_SCAN_POS)
            tas.dragTo(RIGHT_SCAN_SLOT)

            tas.moveTo(RULEBOOK_POS)
            tas.dragTo(PAPER_SCAN_POS)
            tas.click(tas.getRulebook()["documents"]["pos"])
            tas.click(tas.getRulebook()["documents"]["access-permit"]["pos"])

            tas.moveTo(PAPER_SCAN_POS)
            tas.dragTo(LEFT_SCAN_SLOT)

            tas.click(INSPECT_BUTTON)

            # if there's no seal
            if not bgFilter(np.asarray(self.sealArea), np.asarray(AccessPermit.BACKGROUNDS["seal-area"])).any():
                tas.click(onTable(rightSlot(centerOf(AccessPermit.LAYOUT["seal-area"]))))
                tas.click(leftSlot(tas.getRulebook()["documents"]["access-permit"]["document-must-have-seal"]))
            else:
                try:
                    pos = Document.sealPos(
                        np.asarray(self.sealArea), AccessPermit.BACKGROUNDS["seal-area"],
                        AccessPermit.BACKGROUNDS["seal-white"]
                    )
                except:
                    tas.click(onTable(rightSlot(centerOf(AccessPermit.LAYOUT["seal-area"]))))
                    tas.click(leftSlot(tas.getRulebook()["documents"]["access-permit"]["document-must-have-seal"]))
                else:
                    tas.click(onTable(rightSlot(offsetPoint(textFieldOffset(pos), AccessPermit.LAYOUT["seal-area"][:2]))))
                    tas.click(leftSlot(tas.getRulebook()["documents"]["access-permit"]["seals"]))

            time.sleep(INSPECT_INTERROGATE_TIME)
            tas.interrogate()

            tas.moveTo(RIGHT_SCAN_SLOT)
            tas.dragTo(PAPER_SCAN_POS)

            tas.moveTo(LEFT_SCAN_SLOT)
            tas.dragTo(PAPER_SCAN_POS)

            tas.putRulebookBack()
            tas.moveTo(PAPER_SCAN_POS)
            return True
        
        if AccessPermit.TAS.APPEARANCE_HEIGHT_CHECK:
            tas.click(INSPECT_BUTTON)
            tas.click(onTable(centerOf(AccessPermit.LAYOUT["height"])))
            tas.click(PERSON_POS)
            time.sleep(INSPECT_ALPHACHANGE_TIME)
            before = np.asarray(tas.getScreen().crop(TABLE_AREA))
            time.sleep(INSPECT_TIME - INSPECT_ALPHACHANGE_TIME)
            msg = bgFilter(before, np.asarray(tas.getScreen().crop(TABLE_AREA)))

            if pg.locate(AccessPermit.TAS.MATCHING_DATA, msg) is None:
                time.sleep(INSPECT_INTERROGATE_TIME - INSPECT_TIME)
                tas.interrogate()
                tas.moveTo(PAPER_SCAN_POS)
                return True
            
            tas.click(onTable(textFieldOffset(AccessPermit.LAYOUT["description"])))
            before = np.asarray(tas.getScreen().crop(TABLE_AREA))
            time.sleep(INSPECT_TIME)
            msg = bgFilter(before, np.asarray(tas.getScreen().crop(TABLE_AREA)))

            if pg.locate(AccessPermit.TAS.MATCHING_DATA_LINES, msg, confidence = 0.8) is None:
                time.sleep(INSPECT_INTERROGATE_TIME - INSPECT_TIME)
                tas.interrogate()
                tas.moveTo(PAPER_SCAN_POS)
                return True

            tas.click(INSPECT_BUTTON)
            time.sleep(INSPECT_ALPHACHANGE_TIME)
            tas.moveTo(PAPER_SCAN_POS)

        return False
    
    def __repr__(self) -> str:
        return f"""==- Access Permit -==
name:       {self.name}
nation:     {self.nation}
number:     {self.number}
purpose:    {self.purpose}
duration:   {'FOREVER' if self.duration == PERMIT_DURATIONS['FOREVER'] else self.duration}
height:     {self.height}
weight:     {self.weight}
expiration: {self.expiration}"""