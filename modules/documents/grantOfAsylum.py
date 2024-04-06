from PIL      import Image
from typing   import Self
from datetime import date
import os, time, numpy as np, pyautogui as pg

from modules.constants.screen   import *
from modules.constants.delays   import *
from modules.constants.other    import *
from modules.documents.document import Document, getBox
from modules.documents.passport import Nation
from modules.textRecognition    import parseText, parseDate
from modules.utils              import *

class GrantOfAsylum(Document):
    BACKGROUNDS = None

    TABLE_OFFSET = (225, 23)
    TEXT_COLOR   = (125, 109, 121)
    LAYOUT = {
        "seal-area":    getBox(235,  43, 534, 122),
        "first-name":   getBox(371, 131, 524, 142),
        "last-name":    getBox(371, 149, 524, 160),
        "nation":       getBox(407, 179, 524, 190),
        "number":       getBox(407, 197, 524, 208),
        "birth":        getBox(427, 215, 492, 226),
        "height":       getBox(407, 233, 456, 244),
        "weight":       getBox(407, 251, 524, 266),
        "fingerprints": getBox(247, 273, 524, 338),
        "expiration":   getBox(407, 349, 472, 360),
        "label":        getBox(225, 361, 544, 390),
        "picture":      getBox(245, 123, 364, 266) 
    }

    @staticmethod
    def load():
        GrantOfAsylum.BACKGROUNDS = Document.getBgs(
            GrantOfAsylum.LAYOUT, GrantOfAsylum.TABLE_OFFSET, Image.open(
                os.path.join(GrantOfAsylum.TAS.ASSETS, "papers", "grantOfAsylum.png")
            ).convert("RGB")
        )

        GrantOfAsylum.BACKGROUNDS["label"] = np.asarray(GrantOfAsylum.BACKGROUNDS["label"])
        
        sealWhiteBg = GrantOfAsylum.BACKGROUNDS["seal-area"].copy()
        sealWhiteBg.paste((255, 255, 255), (0, 0) + sealWhiteBg.size)
        GrantOfAsylum.BACKGROUNDS["seal-white"] = sealWhiteBg

    @staticmethod
    def checkMatch(docImg: Image.Image) -> bool:
        return np.array_equal(np.asarray(docImg.crop(GrantOfAsylum.LAYOUT["label"])), GrantOfAsylum.BACKGROUNDS["label"])
    
    @staticmethod
    def parse(docImg: Image.Image) -> Self:
        return GrantOfAsylum(
            name = Name(
                parseText(
                    docImg.crop(GrantOfAsylum.LAYOUT["first-name"]), GrantOfAsylum.BACKGROUNDS["first-name"],
                    GrantOfAsylum.TAS.FONTS["bm-mini"], GrantOfAsylum.TEXT_COLOR, PERMIT_PASS_NAME_CHARS,
                    endAt = "  "
                ),
                parseText(
                    docImg.crop(GrantOfAsylum.LAYOUT["last-name"]), GrantOfAsylum.BACKGROUNDS["last-name"],
                    GrantOfAsylum.TAS.FONTS["bm-mini"], GrantOfAsylum.TEXT_COLOR, PERMIT_PASS_NAME_CHARS,
                    endAt = "  "
                ),
            ),
            nation = Nation(parseText(
                docImg.crop(GrantOfAsylum.LAYOUT["nation"]), GrantOfAsylum.BACKGROUNDS["nation"],
                GrantOfAsylum.TAS.FONTS["bm-mini"], GrantOfAsylum.TEXT_COLOR, PERMIT_PASS_CHARS,
                endAt = "  "
            )),
            number = parseText(
                docImg.crop(GrantOfAsylum.LAYOUT["number"]), GrantOfAsylum.BACKGROUNDS["number"],
                GrantOfAsylum.TAS.FONTS["bm-mini"], GrantOfAsylum.TEXT_COLOR, PASSPORT_NUM_CHARS,
                endAt = "  "
            ),
            birth = parseDate(
                docImg.crop(GrantOfAsylum.LAYOUT["birth"]), GrantOfAsylum.BACKGROUNDS["birth"],
                GrantOfAsylum.TAS.FONTS["bm-mini"], GrantOfAsylum.TEXT_COLOR
            ),
            height = int(parseText(
                docImg.crop(GrantOfAsylum.LAYOUT["height"]), GrantOfAsylum.BACKGROUNDS["height"],
                GrantOfAsylum.TAS.FONTS["bm-mini"], GrantOfAsylum.TEXT_COLOR, HEIGHT_CHARS,
                endAt = "cm"
            )[:-2]),
            weight = int(parseText(
                docImg.crop(GrantOfAsylum.LAYOUT["weight"]), GrantOfAsylum.BACKGROUNDS["weight"],
                GrantOfAsylum.TAS.FONTS["bm-mini"], GrantOfAsylum.TEXT_COLOR, WEIGHT_CHARS,
                endAt = "kg"
            )[:-2]),
            expiration = parseDate(
                docImg.crop(GrantOfAsylum.LAYOUT["expiration"]), GrantOfAsylum.BACKGROUNDS["expiration"],
                GrantOfAsylum.TAS.FONTS["bm-mini"], GrantOfAsylum.TEXT_COLOR
            ),
            sealArea     = docImg.crop(GrantOfAsylum.LAYOUT["seal-area"]),
            picture      = docImg.crop(GrantOfAsylum.LAYOUT["picture"]),
            fingerprints = docImg.crop(GrantOfAsylum.LAYOUT["fingerprints"])
        )
    
    def __init__(self, name, nation, number, birth, height, weight, expiration, sealArea, picture, fingerprints):
        self.name: Name       = name
        self.nation: Nation   = nation
        self.number           = number
        self.birth: date      = birth
        self.height           = height
        self.weight           = weight
        self.expiration: date = expiration
        self.sealArea:     Image.Image = sealArea
        self.picture:      Image.Image = picture
        self.fingerprints: Image.Image = fingerprints
    
    def __checkForgery(self) -> bool:        
        return all(Document.checkNoSeal(
            np.asarray(self.sealArea), GrantOfAsylum.BACKGROUNDS["seal-area"],
            seal, GrantOfAsylum.BACKGROUNDS["seal-white"]
        ) for seal in GrantOfAsylum.TAS.MOA_SEALS)
    
    def checkDiscrepancies(self, _) -> bool:
        return True # this is never called
    
    def checkDiscrepanciesWithReason(self, tas) -> bool:
        if tas.allowWrongWeight and tas.weight != self.weight:
            tas.wrongWeight = True
            return False
        
        if self.expiration <= tas.date:
            tas.click(INSPECT_BUTTON)
            tas.click(onTable(centerOf(GrantOfAsylum.LAYOUT["expiration"])))
            tas.click(CLOCK_POS)
            time.sleep(INSPECT_INTERROGATE_TIME)
            tas.interrogate()
            tas.moveTo(PAPER_SCAN_POS)
            return True
        
        if tas.weight != self.weight:
            tas.click(INSPECT_BUTTON)
            tas.click(onTable(textFieldOffset(GrantOfAsylum.LAYOUT["weight"][:2])))
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
            tas.click(tas.getRulebook()["documents"]["grant-asylum"]["pos"])

            tas.moveTo(PAPER_SCAN_POS)
            tas.dragTo(LEFT_SCAN_SLOT)

            tas.click(INSPECT_BUTTON)

            # if there's no seal
            if not bgFilter(np.asarray(self.sealArea), np.asarray(GrantOfAsylum.BACKGROUNDS["seal-area"])).any():
                tas.click(onTable(rightSlot(centerOf(GrantOfAsylum.LAYOUT["seal-area"]))))
                tas.click(leftSlot(tas.getRulebook()["documents"]["grant-asylum"]["document-must-have-seal"]))
            else:
                try:
                    pos = Document.sealPos(
                        np.asarray(self.sealArea), GrantOfAsylum.BACKGROUNDS["seal-area"],
                        GrantOfAsylum.BACKGROUNDS["seal-white"]
                    )
                except:
                    tas.click(onTable(rightSlot(centerOf(GrantOfAsylum.LAYOUT["seal-area"]))))
                    tas.click(leftSlot(tas.getRulebook()["documents"]["grant-asylum"]["document-must-have-seal"]))
                else:
                    tas.click(onTable(rightSlot(offsetPoint(textFieldOffset(pos), GrantOfAsylum.LAYOUT["seal-area"][:2]))))
                    tas.click(leftSlot(tas.getRulebook()["documents"]["grant-asylum"]["seals"]))

            time.sleep(INSPECT_INTERROGATE_TIME)
            tas.interrogate()

            tas.moveTo(RIGHT_SCAN_SLOT)
            tas.dragTo(PAPER_SCAN_POS)

            tas.moveTo(LEFT_SCAN_SLOT)
            tas.dragTo(PAPER_SCAN_POS)

            tas.putRulebookBack()
            tas.moveTo(PAPER_SCAN_POS)
            return True
        
        if GrantOfAsylum.TAS.APPEARANCE_HEIGHT_CHECK:
            tas.click(INSPECT_BUTTON)
            tas.click(onTable(centerOf(GrantOfAsylum.LAYOUT["picture"])))
            tas.click(PERSON_POS)
            time.sleep(INSPECT_ALPHACHANGE_TIME)
            before = np.asarray(tas.getScreen().crop(TABLE_AREA))
            time.sleep(INSPECT_TIME - INSPECT_ALPHACHANGE_TIME)
            msg = bgFilter(before, np.asarray(tas.getScreen().crop(TABLE_AREA)))

            if pg.locate(GrantOfAsylum.TAS.MATCHING_DATA, msg) is None:
                time.sleep(INSPECT_INTERROGATE_TIME - INSPECT_TIME)
                tas.interrogate()
                tas.moveTo(PAPER_SCAN_POS)
                return True
            
            tas.click(onTable(textFieldOffset(GrantOfAsylum.LAYOUT["height"])))
            before = np.asarray(tas.getScreen().crop(TABLE_AREA))
            time.sleep(INSPECT_TIME)
            msg = bgFilter(before, np.asarray(tas.getScreen().crop(TABLE_AREA)))

            if pg.locate(GrantOfAsylum.TAS.MATCHING_DATA_LINES, msg, confidence = 0.8) is None:
                time.sleep(INSPECT_INTERROGATE_TIME - INSPECT_TIME)
                tas.interrogate()
                tas.moveTo(PAPER_SCAN_POS)
                return True

            tas.click(INSPECT_BUTTON)
            time.sleep(INSPECT_ALPHACHANGE_TIME)
            tas.moveTo(PAPER_SCAN_POS)

        return False
    
    def __repr__(self) -> str:
        return f"""==- Grant Of Asylum -==
name:       {self.name}
nation:     {self.nation}
number:     {self.number}
birth:      {self.birth}
height:     {self.height}
weight:     {self.weight}
expiration: {self.expiration}
"""