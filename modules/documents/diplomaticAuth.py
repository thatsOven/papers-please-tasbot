from PIL      import Image
from typing   import Self
import os, time, numpy as np

from modules.constants.screen   import *
from modules.constants.delays   import *
from modules.constants.other    import *
from modules.documents.passport import Nation
from modules.documents.document import Document, getBox
from modules.textRecognition    import parseText
from modules.utils              import *

class DiplomaticAuth(Document):
    BACKGROUNDS = None

    ACCESS_TO_ROWS = 3
    SEALS = {}
    
    TABLE_OFFSET = (235, 11)
    TEXT_COLOR   = (122, 128, 141)
    LAYOUT = {
        "nation":      getBox(303,  19, 444,  30),
        "label":       getBox(267,  53, 426, 108),
        "name":        getBox(309, 193, 522, 204),
        "number":      getBox(333, 217, 522, 228),
        "access-to-0": getBox(277, 315, 516, 328),
        "access-to-1": getBox(277, 333, 516, 346),
        "access-to-2": getBox(277, 351, 516, 364),
        "seal-area":   getBox(427,  39, 532, 134)
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
            DiplomaticAuth.LAYOUT, DiplomaticAuth.TABLE_OFFSET, Image.open(
                os.path.join(DiplomaticAuth.TAS.ASSETS, "papers", "diplomaticAuth", "inner.png")
            ).convert("RGB")
        )

        DiplomaticAuth.BACKGROUNDS["label"] = np.asarray(DiplomaticAuth.BACKGROUNDS["label"])
        
        sealWhiteBg = DiplomaticAuth.BACKGROUNDS["seal-area"].copy()
        sealWhiteBg.paste((255, 255, 255), (0, 0) + sealWhiteBg.size)
        DiplomaticAuth.BACKGROUNDS["seal-white"] = sealWhiteBg

    @staticmethod
    def checkMatch(docImg: Image.Image) -> bool:
        return np.array_equal(np.asarray(docImg.crop(DiplomaticAuth.LAYOUT["label"])), DiplomaticAuth.BACKGROUNDS["label"])
    
    @staticmethod
    def parse(docImg: Image.Image) -> Self:
        return DiplomaticAuth(
            name = Name.fromPermitOrPass(parseText(
                docImg.crop(DiplomaticAuth.LAYOUT["name"]), DiplomaticAuth.BACKGROUNDS["name"],
                DiplomaticAuth.TAS.FONTS["bm-mini"], DiplomaticAuth.TEXT_COLOR, PERMIT_PASS_NAME_CHARS,
                misalignFix = True
            )),
            number = parseText(
                docImg.crop(DiplomaticAuth.LAYOUT["number"]), DiplomaticAuth.BACKGROUNDS["number"],
                DiplomaticAuth.TAS.FONTS["bm-mini"], DiplomaticAuth.TEXT_COLOR, PASSPORT_NUM_CHARS,
                misalignFix = True
            ),
            nation = Nation(parseText(
                docImg.crop(DiplomaticAuth.LAYOUT["nation"]), DiplomaticAuth.BACKGROUNDS["nation"],
                DiplomaticAuth.TAS.FONTS["bm-mini"], DiplomaticAuth.TEXT_COLOR, PERMIT_PASS_CHARS,
                endAt = "  "
            )),
            accessTo = [Nation(x.strip()) for x in "".join(
                parseText(
                    docImg.crop(DiplomaticAuth.LAYOUT[f"access-to-{i}"]), DiplomaticAuth.BACKGROUNDS[f"access-to-{i}"],
                    DiplomaticAuth.TAS.FONTS["bm-mini"], DiplomaticAuth.TEXT_COLOR, DIPLOMATIC_AUTH_ACCESS_TO_CHARS,
                    endAt = "  "
                ) for i in range(DiplomaticAuth.ACCESS_TO_ROWS)
            ).split(",")],
            sealArea = docImg.crop(DiplomaticAuth.LAYOUT["seal-area"])
        )

    def __init__(self, name, number, nation, accessTo, sealArea):
        self.name: Name             = name
        self.number                 = number
        self.nation: Nation         = nation
        self.accessTo: list[Nation] = accessTo
        self.sealArea: Image.Image  = sealArea

    def __checkForgery(self) -> bool:        
        return all(Document.checkNoSeal(
            np.asarray(self.sealArea), DiplomaticAuth.BACKGROUNDS["seal-area"],
            seal, DiplomaticAuth.BACKGROUNDS["seal-white"]
        ) for seal in DiplomaticAuth.SEALS[self.nation])
    
    def checkDiscrepancies(self, _) -> bool:
        if Nation.ARSTOTZKA not in self.accessTo: return True
        return self.__checkForgery()

    def checkDiscrepanciesWithReason(self, tas) -> bool:
        if Nation.ARSTOTZKA not in self.accessTo:
            tas.moveTo(PAPER_SCAN_POS)
            tas.dragTo(RIGHT_SCAN_SLOT)

            tas.moveTo(RULEBOOK_POS)
            tas.dragTo(PAPER_SCAN_POS)
            tas.click(tas.getRulebook()["documents"]["pos"])
            tas.click(tas.getRulebook()["documents"]["diplomatic-auth"]["pos"])

            tas.moveTo(PAPER_SCAN_POS)
            tas.dragTo(LEFT_SCAN_SLOT)

            tas.click(INSPECT_BUTTON)
            tas.click(onTable(textFieldOffset(rightSlot(DiplomaticAuth.LAYOUT["access-to-0"][:2]))))
            tas.click(leftSlot(tas.getRulebook()["documents"]["diplomatic-auth"]["auth-arstotzka"]))

            time.sleep(INSPECT_INTERROGATE_TIME)
            tas.interrogate()

            tas.moveTo(RIGHT_SCAN_SLOT)
            tas.dragTo(PAPER_SCAN_POS)

            tas.moveTo(LEFT_SCAN_SLOT)
            tas.dragTo(PAPER_SCAN_POS)
            tas.putRulebookBack()

            tas.moveTo(PAPER_SCAN_POS)
            return True
        
        if self.__checkForgery():
            tas.moveTo(PAPER_SCAN_POS)

            # if there's no seal
            if not bgFilter(np.asarray(self.sealArea), np.asarray(DiplomaticAuth.BACKGROUNDS["seal-area"])).any():
                tas.dragTo(RIGHT_SCAN_SLOT)

                tas.moveTo(RULEBOOK_POS)
                tas.dragTo(PAPER_SCAN_POS)
                tas.click(tas.getRulebook()["documents"]["pos"])
                tas.click(tas.getRulebook()["documents"]["diplomatic-auth"]["pos"])

                tas.moveTo(PAPER_SCAN_POS)
                tas.dragTo(LEFT_SCAN_SLOT)

                tas.click(INSPECT_BUTTON)
                tas.click(onTable(rightSlot(centerOf(DiplomaticAuth.LAYOUT["seal-area"]))))
                tas.click(leftSlot(tas.getRulebook()["documents"]["diplomatic-auth"]["document-must-have-seal"]))

                time.sleep(INSPECT_INTERROGATE_TIME)
                tas.interrogate()

                tas.moveTo(RIGHT_SCAN_SLOT)
                tas.dragTo(PAPER_SCAN_POS)

                tas.moveTo(LEFT_SCAN_SLOT)
                tas.dragTo(PAPER_SCAN_POS)
            else:
                tas.dragTo(LEFT_SCAN_SLOT)

                tas.moveTo(RULEBOOK_POS)
                tas.dragTo(PAPER_SCAN_POS)

                tas.click(tas.getRulebook()["region-map"]["pos"])
                tas.click(tas.getRulebook()["region-map"][self.nation.value.lower()])

                tas.moveTo(PAPER_SCAN_POS)
                tas.dragTo(RIGHT_SCAN_SLOT)

                tas.click(INSPECT_BUTTON)
                tas.click(onTable(leftSlot(centerOf(DiplomaticAuth.LAYOUT["seal-area"]))))
                tas.click(rightSlot(tas.getRulebook()["region-map"]["diplomatic-seal"]))

                time.sleep(INSPECT_INTERROGATE_TIME)
                tas.interrogate()

                tas.moveTo(LEFT_SCAN_SLOT)
                tas.dragTo(PAPER_SCAN_POS)

                tas.moveTo(RIGHT_SCAN_SLOT)
                tas.dragTo(PAPER_SCAN_POS)
            
            tas.putRulebookBack()
            tas.moveTo(PAPER_SCAN_POS)
            return True

        return False
    
    def __repr__(self) -> str:
        return f"""==- Diplomatic Authorization -==
name:      {self.name}
number:    {self.number}
nation:    {self.nation}
access to: {self.accessTo}"""