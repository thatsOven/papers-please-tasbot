from abc    import ABC, abstractmethod
from typing import TYPE_CHECKING
import time, pyautogui as pg, numpy as np

from modules.constants.delays import *
from modules.constants.screen import *
from modules.constants.other  import *
from modules.utils            import *

from modules.documents.document       import Document
from modules.documents.entryTicket    import EntryTicket
from modules.documents.entryPermit    import EntryPermit
from modules.documents.workPass       import WorkPass
from modules.documents.diplomaticAuth import DiplomaticAuth
from modules.documents.arstotzkanID   import ArstotzkanID, District
from modules.documents.idSupplement   import IDSupplement
from modules.documents.grantOfAsylum  import GrantOfAsylum
from modules.documents.accessPermit   import AccessPermit
from modules.documents.vaxCert        import Disease, Vaccine, VaxCert
from modules.documents.passport       import Nation, Passport

if TYPE_CHECKING:
    from tas import TAS

class Run(ABC):
    tas: "TAS"

    @abstractmethod
    def run(self) -> None:
        ...

    @staticmethod
    def description() -> str:
        return "No description given"

    def test(self) -> None:
        ...

    def arstotzkanIDConfiscateCheck(self, doc: ArstotzkanID) -> bool:
        return self.tas.DAY_24 <= self.tas.date < self.tas.DAY_28 and doc.district == District.ALTAN

    def confiscatePassportWhen(self, doc: Document | Passport) -> bool:
        if type(doc) is ArstotzkanID and self.arstotzkanIDConfiscateCheck(doc): return True
        if type(doc) is not Passport: return False

        if self.tas.DAY_24 <= self.tas.date < self.tas.DAY_28 and doc.type_.nation == Nation.ARSTOTZKA:            
            self.tas.needId = True
        
        if (
            self.tas.date >= self.tas.DAY_29 and 
            self.tas.needObri > 0 and 
            doc.type_.nation == Nation.OBRISTAN
        ):
            self.tas.needObri -= 1
            return True
        
        return self.tas.date >= self.tas.DAY_28 and doc.type_.nation == Nation.ARSTOTZKA

    def checkAccessPermitDiscrepancies(self, doc: AccessPermit) -> bool:
        if self.tas.allowWrongWeight and self.tas.weight != doc.weight:
            self.tas.wrongWeight = True
            return False
        
        if doc.expiration <= self.tas.date:
            self.tas.click(INSPECT_BUTTON)
            self.tas.click(onTable(centerOf(AccessPermit.LAYOUT["expiration"])))
            self.tas.click(CLOCK_POS)
            time.sleep(INSPECT_INTERROGATE_TIME)
            self.tas.interrogate()
            self.tas.moveTo(PAPER_SCAN_POS)
            return True
        
        if self.tas.weight != doc.weight:
            self.tas.click(INSPECT_BUTTON)
            self.tas.click(onTable(centerOf(AccessPermit.LAYOUT["weight"])))
            self.tas.click(centerOf(WEIGHT_AREA))
            time.sleep(INSPECT_INTERROGATE_TIME)
            self.tas.interrogate()
            self.tas.moveTo(PAPER_SCAN_POS)
            return True
        
        if doc.checkForgery():
            self.tas.moveTo(PAPER_SCAN_POS)
            self.tas.dragTo(RIGHT_SCAN_SLOT)

            self.tas.moveTo(RULEBOOK_POS)
            self.tas.dragTo(PAPER_SCAN_POS)
            self.tas.click(self.tas.getRulebook()["documents"]["pos"])
            self.tas.click(self.tas.getRulebook()["documents"]["access-permit"]["pos"])

            self.tas.moveTo(PAPER_SCAN_POS)
            self.tas.dragTo(LEFT_SCAN_SLOT)

            self.tas.click(INSPECT_BUTTON)

            # if there's no seal
            if not bgFilter(np.asarray(doc.sealArea), np.asarray(AccessPermit.BACKGROUNDS["seal-area"])).any():
                self.tas.click(onTable(rightSlot(centerOf(AccessPermit.LAYOUT["seal-area"]))))
                self.tas.click(leftSlot(self.tas.getRulebook()["documents"]["access-permit"]["document-must-have-seal"]))
            else:
                try:
                    pos = Document.sealPos(
                        np.asarray(doc.sealArea), AccessPermit.BACKGROUNDS["seal-area"],
                        AccessPermit.BACKGROUNDS["seal-white"]
                    )
                except:
                    self.tas.click(onTable(rightSlot(centerOf(AccessPermit.LAYOUT["seal-area"]))))
                    self.tas.click(leftSlot(self.tas.getRulebook()["documents"]["access-permit"]["document-must-have-seal"]))
                else:
                    self.tas.click(onTable(rightSlot(offsetPoint(textFieldOffset(pos), AccessPermit.LAYOUT["seal-area"][:2]))))
                    self.tas.click(leftSlot(self.tas.getRulebook()["documents"]["access-permit"]["seals"]))

            time.sleep(INSPECT_INTERROGATE_TIME)
            self.tas.interrogate()

            self.tas.moveTo(RIGHT_SCAN_SLOT)
            self.tas.dragTo(PAPER_SCAN_POS)

            self.tas.moveTo(LEFT_SCAN_SLOT)
            self.tas.dragTo(PAPER_SCAN_POS)

            self.tas.putRulebookBack()
            self.tas.moveTo(PAPER_SCAN_POS)
            return True
        
        if self.tas.APPEARANCE_HEIGHT_CHECK:
            self.tas.click(INSPECT_BUTTON)
            self.tas.click(onTable(centerOf(AccessPermit.LAYOUT["height"])))
            self.tas.click(PERSON_POS)
            time.sleep(INSPECT_ALPHACHANGE_TIME)
            before = np.asarray(self.tas.getScreen().crop(TABLE_AREA))
            time.sleep(INSPECT_TIME - INSPECT_ALPHACHANGE_TIME)
            msg = bgFilter(before, np.asarray(self.tas.getScreen().crop(TABLE_AREA)))

            if pg.locate(self.tas.MATCHING_DATA, msg) is None:
                time.sleep(INSPECT_INTERROGATE_TIME - INSPECT_TIME)
                self.tas.interrogate()
                self.tas.moveTo(PAPER_SCAN_POS)
                return True
            
            self.tas.click(onTable(textFieldOffset(AccessPermit.LAYOUT["description"])))
            before = np.asarray(self.tas.getScreen().crop(TABLE_AREA))
            time.sleep(INSPECT_TIME)
            msg = bgFilter(before, np.asarray(self.tas.getScreen().crop(TABLE_AREA)))

            if pg.locate(self.tas.MATCHING_DATA_LINES, msg, confidence = 0.8) is None:
                time.sleep(INSPECT_INTERROGATE_TIME - INSPECT_TIME)
                self.tas.interrogate()
                self.tas.moveTo(PAPER_SCAN_POS)
                return True

            self.tas.click(INSPECT_BUTTON)
            time.sleep(INSPECT_ALPHACHANGE_TIME)
            self.tas.moveTo(PAPER_SCAN_POS)

        return False
    
    def checkArstotzkanIDDiscrepancies(self, doc: ArstotzkanID) -> bool:
        if self.tas.allowWrongWeight and self.tas.weight != doc.weight:
            self.tas.wrongWeight = True
            return False
        
        if self.tas.date < self.tas.DAY_18:
            if doc.district == District.UNKNOWN or self.tas.weight != doc.weight:
                return True
            
            if self.tas.ID_CHECK:
                self.tas.click(INSPECT_BUTTON)
                self.tas.click(onTable(centerOf(ArstotzkanID.LAYOUT["picture"])))
                self.tas.click(PERSON_POS)
                time.sleep(INSPECT_ALPHACHANGE_TIME)
                before = np.asarray(self.tas.getScreen().crop(TABLE_AREA))
                time.sleep(INSPECT_TIME - INSPECT_ALPHACHANGE_TIME)
                msg = bgFilter(before, np.asarray(self.tas.getScreen().crop(TABLE_AREA)))
                
                if pg.locate(self.tas.MATCHING_DATA, msg) is None:
                    self.tas.click(INSPECT_BUTTON)
                    time.sleep(INSPECT_ALPHACHANGE_TIME)
                    self.tas.moveTo(PAPER_SCAN_POS)
                    return True
                
                self.tas.click(onTable(centerOf(ArstotzkanID.LAYOUT["height"])))
                before = np.asarray(self.tas.getScreen().crop(TABLE_AREA))
                time.sleep(INSPECT_TIME)
                msg = bgFilter(before, np.asarray(self.tas.getScreen().crop(TABLE_AREA)))

                self.tas.click(INSPECT_BUTTON)
                time.sleep(INSPECT_ALPHACHANGE_TIME)
                self.tas.moveTo(PAPER_SCAN_POS)
                return pg.locate(self.tas.MATCHING_DATA_LINES, msg, confidence = 0.8) is None

            return False
        
        if self.arstotzkanIDConfiscateCheck() and not self.tas.doConfiscate:
            self.tas.skipReason = True
            return True
        
        if self.tas.weight != doc.weight:
            self.tas.click(INSPECT_BUTTON)
            self.tas.click(onTable(centerOf(ArstotzkanID.LAYOUT["weight"])))
            self.tas.click(centerOf(WEIGHT_AREA))
            time.sleep(INSPECT_INTERROGATE_TIME)
            self.tas.interrogate()
            self.tas.moveTo(PAPER_SCAN_POS)
            return True

        if doc.district == District.UNKNOWN:
            self.tas.moveTo(PAPER_SCAN_POS)
            self.tas.dragTo(RIGHT_SCAN_SLOT)

            self.tas.moveTo(RULEBOOK_POS)
            self.tas.dragTo(PAPER_SCAN_POS)
            self.tas.click(self.tas.getRulebook()["documents"]["pos"])
            self.tas.click(self.tas.getRulebook()["documents"]["id-card"]["pos"])

            self.tas.moveTo(PAPER_SCAN_POS)
            self.tas.dragTo(LEFT_SCAN_SLOT)

            self.tas.click(INSPECT_BUTTON)
            self.tas.click(onTable(offsetPoint(rightSlot(
                ArstotzkanID.LAYOUT["district"][:2]
            ), (10, 4))))
            self.tas.click(leftSlot(self.tas.getRulebook()["documents"]["id-card"]["districts"]))

            ok = not self.tas.interrogateFailsafe()
            if ok:
                time.sleep(INSPECT_INTERROGATE_TIME - INSPECT_TIME)
                self.tas.interrogate()

            self.tas.moveTo(RIGHT_SCAN_SLOT)
            self.tas.dragTo(PAPER_SCAN_POS)

            self.tas.moveTo(LEFT_SCAN_SLOT)
            self.tas.dragTo(PAPER_SCAN_POS)
            self.tas.putRulebookBack()

            self.tas.moveTo(PAPER_SCAN_POS)

            if ok: return True
        
        if self.tas.ID_CHECK:
            self.tas.click(INSPECT_BUTTON)
            self.tas.click(onTable(centerOf(ArstotzkanID.LAYOUT["picture"])))
            self.tas.click(PERSON_POS)
            time.sleep(INSPECT_ALPHACHANGE_TIME)
            before = np.asarray(self.tas.getScreen().crop(TABLE_AREA))
            time.sleep(INSPECT_TIME - INSPECT_ALPHACHANGE_TIME)
            msg = bgFilter(before, np.asarray(self.tas.getScreen().crop(TABLE_AREA)))
            
            if pg.locate(self.tas.MATCHING_DATA, msg) is None:
                time.sleep(INSPECT_INTERROGATE_TIME - INSPECT_TIME)
                self.tas.interrogate()
                self.tas.moveTo(PAPER_SCAN_POS)
                return True
            
            self.tas.click(onTable(centerOf(ArstotzkanID.LAYOUT["height"])))
            before = np.asarray(self.tas.getScreen().crop(TABLE_AREA))
            time.sleep(INSPECT_TIME)
            msg = bgFilter(before, np.asarray(self.tas.getScreen().crop(TABLE_AREA)))

            if pg.locate(self.tas.MATCHING_DATA_LINES, msg, confidence = 0.8) is None:
                time.sleep(INSPECT_INTERROGATE_TIME - INSPECT_TIME)
                self.tas.interrogate()
                self.tas.moveTo(PAPER_SCAN_POS)
                return True

            self.tas.click(INSPECT_BUTTON)
            time.sleep(INSPECT_ALPHACHANGE_TIME)
            self.tas.moveTo(PAPER_SCAN_POS)

        return False
        
    def checkDiplomaticAuthDiscrepancies(self, doc: DiplomaticAuth) -> bool:
        if self.tas.date < self.tas.DAY_18:
            if Nation.ARSTOTZKA not in doc.accessTo: return True
            return doc.checkForgery()
        
        if Nation.ARSTOTZKA not in doc.accessTo:
            self.tas.moveTo(PAPER_SCAN_POS)
            self.tas.dragTo(RIGHT_SCAN_SLOT)

            self.tas.moveTo(RULEBOOK_POS)
            self.tas.dragTo(PAPER_SCAN_POS)
            self.tas.click(self.tas.getRulebook()["documents"]["pos"])
            self.tas.click(self.tas.getRulebook()["documents"]["diplomatic-auth"]["pos"])

            self.tas.moveTo(PAPER_SCAN_POS)
            self.tas.dragTo(LEFT_SCAN_SLOT)

            self.tas.click(INSPECT_BUTTON)
            self.tas.click(onTable(textFieldOffset(rightSlot(DiplomaticAuth.LAYOUT["access-to-0"][:2]))))
            self.tas.click(leftSlot(self.tas.getRulebook()["documents"]["diplomatic-auth"]["auth-arstotzka"]))

            time.sleep(INSPECT_INTERROGATE_TIME)
            self.tas.interrogate()

            self.tas.moveTo(RIGHT_SCAN_SLOT)
            self.tas.dragTo(PAPER_SCAN_POS)

            self.tas.moveTo(LEFT_SCAN_SLOT)
            self.tas.dragTo(PAPER_SCAN_POS)
            self.tas.putRulebookBack()

            self.tas.moveTo(PAPER_SCAN_POS)
            return True
        
        if doc.checkForgery():
            self.tas.moveTo(PAPER_SCAN_POS)

            # if there's no seal
            if not bgFilter(np.asarray(doc.sealArea), np.asarray(DiplomaticAuth.BACKGROUNDS["seal-area"])).any():
                self.tas.dragTo(RIGHT_SCAN_SLOT)

                self.tas.moveTo(RULEBOOK_POS)
                self.tas.dragTo(PAPER_SCAN_POS)
                self.tas.click(self.tas.getRulebook()["documents"]["pos"])
                self.tas.click(self.tas.getRulebook()["documents"]["diplomatic-auth"]["pos"])

                self.tas.moveTo(PAPER_SCAN_POS)
                self.tas.dragTo(LEFT_SCAN_SLOT)

                self.tas.click(INSPECT_BUTTON)
                self.tas.click(onTable(rightSlot(centerOf(DiplomaticAuth.LAYOUT["seal-area"]))))
                self.tas.click(leftSlot(self.tas.getRulebook()["documents"]["diplomatic-auth"]["document-must-have-seal"]))

                time.sleep(INSPECT_INTERROGATE_TIME)
                self.tas.interrogate()

                self.tas.moveTo(RIGHT_SCAN_SLOT)
                self.tas.dragTo(PAPER_SCAN_POS)

                self.tas.moveTo(LEFT_SCAN_SLOT)
                self.tas.dragTo(PAPER_SCAN_POS)
            else:
                self.tas.dragTo(LEFT_SCAN_SLOT)

                self.tas.moveTo(RULEBOOK_POS)
                self.tas.dragTo(PAPER_SCAN_POS)

                self.tas.click(self.tas.getRulebook()["region-map"]["pos"])
                self.tas.click(self.tas.getRulebook()["region-map"][doc.nation.value.lower()])

                self.tas.moveTo(PAPER_SCAN_POS)
                self.tas.dragTo(RIGHT_SCAN_SLOT)

                self.tas.click(INSPECT_BUTTON)
                self.tas.click(onTable(leftSlot(centerOf(DiplomaticAuth.LAYOUT["seal-area"]))))
                self.tas.click(rightSlot(self.tas.getRulebook()["region-map"]["diplomatic-seal"]))

                time.sleep(INSPECT_INTERROGATE_TIME)
                self.tas.interrogate()

                self.tas.moveTo(LEFT_SCAN_SLOT)
                self.tas.dragTo(PAPER_SCAN_POS)

                self.tas.moveTo(RIGHT_SCAN_SLOT)
                self.tas.dragTo(PAPER_SCAN_POS)
            
            self.tas.putRulebookBack()
            self.tas.moveTo(PAPER_SCAN_POS)
            return True

        return False
    
    def checkEntryPermitDiscrepancies(self, doc: EntryPermit) -> bool:
        if self.tas.date < self.tas.DAY_18:
            if doc.expiration <= self.tas.date: return True
            return doc.checkForgery(self.tas.date)
        
        if doc.expiration <= self.tas.date:
            self.tas.click(INSPECT_BUTTON)
            self.tas.click(onTable(centerOf(EntryPermit.LAYOUT["expiration"])))
            self.tas.click(CLOCK_POS)
            time.sleep(INSPECT_INTERROGATE_TIME)
            self.tas.interrogate()
            self.tas.moveTo(PAPER_SCAN_POS)
            return True
        
        if doc.checkForgery(self.tas.date):
            self.tas.moveTo(PAPER_SCAN_POS)
            self.tas.dragTo(RIGHT_SCAN_SLOT)

            self.tas.moveTo(RULEBOOK_POS)
            self.tas.dragTo(PAPER_SCAN_POS)
            self.tas.click(self.tas.getRulebook()["documents"]["pos"])
            self.tas.click(self.tas.getRulebook()["documents"]["entry-permit"]["pos"])

            self.tas.moveTo(PAPER_SCAN_POS)
            self.tas.dragTo(LEFT_SCAN_SLOT)

            self.tas.click(INSPECT_BUTTON)

            # if there's no seal
            if not bgFilter(np.asarray(doc.sealArea), np.asarray(EntryPermit.BACKGROUNDS["seal-area"])).any():
                self.tas.click(onTable(rightSlot(centerOf(EntryPermit.LAYOUT["seal-area"]))))
                self.tas.click(leftSlot(self.tas.getRulebook()["documents"]["entry-permit"]["document-must-have-seal"]))
            else:
                try:
                    pos = Document.sealPos(
                        np.asarray(doc.sealArea), EntryPermit.BACKGROUNDS["seal-area"],
                        EntryPermit.BACKGROUNDS["seal-white"]
                    )
                except:
                    self.tas.click(onTable(rightSlot(centerOf(EntryPermit.LAYOUT["seal-area"]))))
                    self.tas.click(leftSlot(self.tas.getRulebook()["documents"]["entry-permit"]["document-must-have-seal"]))
                else:
                    self.tas.click(onTable(rightSlot(offsetPoint(textFieldOffset(pos), EntryPermit.LAYOUT["seal-area"][:2]))))
                    self.tas.click(leftSlot(self.tas.getRulebook()["documents"]["entry-permit"]["seals"]))

            time.sleep(INSPECT_INTERROGATE_TIME)
            self.tas.interrogate()

            self.tas.moveTo(RIGHT_SCAN_SLOT)
            self.tas.dragTo(PAPER_SCAN_POS)

            self.tas.moveTo(LEFT_SCAN_SLOT)
            self.tas.dragTo(PAPER_SCAN_POS)

            self.tas.putRulebookBack()
            self.tas.moveTo(PAPER_SCAN_POS)
            return True
        
        return False
    
    def checkEntryTicketDiscrepancies(self, doc: EntryTicket) -> bool:
        return doc.date != self.tas.date
    
    def checkGrantOfAsylumDiscrepancies(self, doc: GrantOfAsylum) -> bool:
        if self.tas.allowWrongWeight and self.tas.weight != doc.weight:
            self.tas.wrongWeight = True
            return False
        
        if doc.expiration <= self.tas.date:
            self.tas.click(INSPECT_BUTTON)
            self.tas.click(onTable(centerOf(GrantOfAsylum.LAYOUT["expiration"])))
            self.tas.click(CLOCK_POS)
            time.sleep(INSPECT_INTERROGATE_TIME)
            self.tas.interrogate()
            self.tas.moveTo(PAPER_SCAN_POS)
            return True
        
        if self.tas.weight != doc.weight:
            self.tas.click(INSPECT_BUTTON)
            self.tas.click(onTable(textFieldOffset(GrantOfAsylum.LAYOUT["weight"][:2])))
            self.tas.click(centerOf(WEIGHT_AREA))
            time.sleep(INSPECT_INTERROGATE_TIME)
            self.tas.interrogate()
            self.tas.moveTo(PAPER_SCAN_POS)
            return True
        
        if doc.checkForgery():
            self.tas.moveTo(PAPER_SCAN_POS)
            self.tas.dragTo(RIGHT_SCAN_SLOT)

            self.tas.moveTo(RULEBOOK_POS)
            self.tas.dragTo(PAPER_SCAN_POS)
            self.tas.click(self.tas.getRulebook()["documents"]["pos"])
            self.tas.click(self.tas.getRulebook()["documents"]["grant-asylum"]["pos"])

            self.tas.moveTo(PAPER_SCAN_POS)
            self.tas.dragTo(LEFT_SCAN_SLOT)

            self.tas.click(INSPECT_BUTTON)

            # if there's no seal
            if not bgFilter(np.asarray(doc.sealArea), np.asarray(GrantOfAsylum.BACKGROUNDS["seal-area"])).any():
                self.tas.click(onTable(rightSlot(centerOf(GrantOfAsylum.LAYOUT["seal-area"]))))
                self.tas.click(leftSlot(self.tas.getRulebook()["documents"]["grant-asylum"]["document-must-have-seal"]))
            else:
                try:
                    pos = Document.sealPos(
                        np.asarray(doc.sealArea), GrantOfAsylum.BACKGROUNDS["seal-area"],
                        GrantOfAsylum.BACKGROUNDS["seal-white"]
                    )
                except:
                    self.tas.click(onTable(rightSlot(centerOf(GrantOfAsylum.LAYOUT["seal-area"]))))
                    self.tas.click(leftSlot(self.tas.getRulebook()["documents"]["grant-asylum"]["document-must-have-seal"]))
                else:
                    self.tas.click(onTable(rightSlot(offsetPoint(textFieldOffset(pos), GrantOfAsylum.LAYOUT["seal-area"][:2]))))
                    self.tas.click(leftSlot(self.tas.getRulebook()["documents"]["grant-asylum"]["seals"]))

            time.sleep(INSPECT_INTERROGATE_TIME)
            self.tas.interrogate()

            self.tas.moveTo(RIGHT_SCAN_SLOT)
            self.tas.dragTo(PAPER_SCAN_POS)

            self.tas.moveTo(LEFT_SCAN_SLOT)
            self.tas.dragTo(PAPER_SCAN_POS)

            self.tas.putRulebookBack()
            self.tas.moveTo(PAPER_SCAN_POS)
            return True
        
        if self.tas.APPEARANCE_HEIGHT_CHECK:
            self.tas.click(INSPECT_BUTTON)
            self.tas.click(onTable(centerOf(GrantOfAsylum.LAYOUT["picture"])))
            self.tas.click(PERSON_POS)
            time.sleep(INSPECT_ALPHACHANGE_TIME)
            before = np.asarray(self.tas.getScreen().crop(TABLE_AREA))
            time.sleep(INSPECT_TIME - INSPECT_ALPHACHANGE_TIME)
            msg = bgFilter(before, np.asarray(self.tas.getScreen().crop(TABLE_AREA)))

            if pg.locate(self.tas.MATCHING_DATA, msg) is None:
                time.sleep(INSPECT_INTERROGATE_TIME - INSPECT_TIME)
                self.tas.interrogate()
                self.tas.moveTo(PAPER_SCAN_POS)
                return True
            
            self.tas.click(onTable(textFieldOffset(GrantOfAsylum.LAYOUT["height"])))
            before = np.asarray(self.tas.getScreen().crop(TABLE_AREA))
            time.sleep(INSPECT_TIME)
            msg = bgFilter(before, np.asarray(self.tas.getScreen().crop(TABLE_AREA)))

            if pg.locate(self.tas.MATCHING_DATA_LINES, msg, confidence = 0.8) is None:
                time.sleep(INSPECT_INTERROGATE_TIME - INSPECT_TIME)
                self.tas.interrogate()
                self.tas.moveTo(PAPER_SCAN_POS)
                return True

            self.tas.click(INSPECT_BUTTON)
            time.sleep(INSPECT_ALPHACHANGE_TIME)
            self.tas.moveTo(PAPER_SCAN_POS)

        return False
    
    def checkIDSupplementDiscrepancies(self, doc: IDSupplement) -> bool:
        if self.tas.allowWrongWeight and self.tas.weight != doc.weight:
            self.tas.wrongWeight = True
            return False
        
        if self.tas.date < self.tas.DAY_18:
            if (
                doc.expiration <= self.tas.date or
                self.tas.weight != doc.weight
            ): return True

            if self.tas.APPEARANCE_HEIGHT_CHECK:
                self.tas.click(INSPECT_BUTTON)
                self.tas.click(onTable(centerOf(IDSupplement.LAYOUT["height"])))
                self.tas.click(PERSON_POS)
                time.sleep(INSPECT_ALPHACHANGE_TIME)
                before = np.asarray(self.tas.getScreen().crop(TABLE_AREA))
                time.sleep(INSPECT_TIME - INSPECT_ALPHACHANGE_TIME)
                msg = bgFilter(before, np.asarray(self.tas.getScreen().crop(TABLE_AREA)))

                if pg.locate(self.tas.MATCHING_DATA, msg) is None:
                    self.tas.click(INSPECT_BUTTON)
                    time.sleep(INSPECT_ALPHACHANGE_TIME)
                    self.tas.moveTo(PAPER_SCAN_POS)
                    return True
                
                self.tas.click(onTable(textFieldOffset(IDSupplement.LAYOUT["description"])))
                before = np.asarray(self.tas.getScreen().crop(TABLE_AREA))
                time.sleep(INSPECT_TIME)
                msg = bgFilter(before, np.asarray(self.tas.getScreen().crop(TABLE_AREA)))

                self.tas.click(INSPECT_BUTTON)
                time.sleep(INSPECT_ALPHACHANGE_TIME)
                self.tas.moveTo(PAPER_SCAN_POS)
                return pg.locate(self.tas.MATCHING_DATA_LINES, msg, confidence = 0.8) is None
            
            return False
    
        if doc.expiration <= self.tas.date:
            self.tas.click(INSPECT_BUTTON)
            self.tas.click(onTable(centerOf(IDSupplement.LAYOUT["expiration"])))
            self.tas.click(CLOCK_POS)
            time.sleep(INSPECT_INTERROGATE_TIME)
            self.tas.interrogate()
            self.tas.moveTo(PAPER_SCAN_POS)
            return True
        
        if self.tas.weight != doc.weight:
            self.tas.click(INSPECT_BUTTON)
            self.tas.click(onTable(centerOf(IDSupplement.LAYOUT["weight"])))
            self.tas.click(centerOf(WEIGHT_AREA))
            time.sleep(INSPECT_INTERROGATE_TIME)
            self.tas.interrogate()
            self.tas.moveTo(PAPER_SCAN_POS)
            return True
        
        if self.tas.APPEARANCE_HEIGHT_CHECK:
            self.tas.click(INSPECT_BUTTON)
            self.tas.click(onTable(centerOf(IDSupplement.LAYOUT["height"])))
            self.tas.click(PERSON_POS)
            time.sleep(INSPECT_ALPHACHANGE_TIME)
            before = np.asarray(self.tas.getScreen().crop(TABLE_AREA))
            time.sleep(INSPECT_TIME - INSPECT_ALPHACHANGE_TIME)
            msg = bgFilter(before, np.asarray(self.tas.getScreen().crop(TABLE_AREA)))

            if pg.locate(self.tas.MATCHING_DATA, msg) is None:
                time.sleep(INSPECT_INTERROGATE_TIME - INSPECT_TIME)
                self.tas.interrogate()
                self.tas.moveTo(PAPER_SCAN_POS)
                return True
            
            self.tas.click(onTable(textFieldOffset(IDSupplement.LAYOUT["description"])))
            before = np.asarray(self.tas.getScreen().crop(TABLE_AREA))
            time.sleep(INSPECT_TIME)
            msg = bgFilter(before, np.asarray(self.tas.getScreen().crop(TABLE_AREA)))

            if pg.locate(self.tas.MATCHING_DATA_LINES, msg, confidence = 0.8) is None:
                time.sleep(INSPECT_INTERROGATE_TIME - INSPECT_TIME)
                self.tas.interrogate()
                self.tas.moveTo(PAPER_SCAN_POS)
                return True

            self.tas.click(INSPECT_BUTTON)
            time.sleep(INSPECT_ALPHACHANGE_TIME)
            self.tas.moveTo(PAPER_SCAN_POS)

        return False
    
    def checkPassportDiscrepancies(self, doc: Passport) -> bool:
        if self.tas.date < self.tas.DAY_18:
            if (
                doc.expiration <= self.tas.date  or
                doc.city not in doc.type_.cities or
                doc.isSexWrong()
            ): return True

            # check self.tas.DAY_7 for an explanation about this
            if self.tas.date == self.tas.DAY_7 and doc.type_.nation == Nation.KOLECHIA: 
                return True

            if (
                (self.tas.date == self.tas.DAY_2) or
                (self.tas.DAY3_PICTURE_CHECK and self.tas.date == self.tas.DAY_3) or
                (self.tas.DAY4_PICTURE_CHECK and self.tas.date >  self.tas.DAY_3)
            ):
                self.tas.click(INSPECT_BUTTON)
                self.tas.click(onTable(centerOf(doc.type_.layout.picture)))
                self.tas.click(PERSON_POS)
                time.sleep(INSPECT_ALPHACHANGE_TIME)
                before = np.asarray(self.tas.getScreen().crop(TABLE_AREA))
                time.sleep(INSPECT_TIME - INSPECT_ALPHACHANGE_TIME)
                msg = bgFilter(before, np.asarray(self.tas.getScreen().crop(TABLE_AREA)))
                self.tas.click(INSPECT_BUTTON)
                time.sleep(INSPECT_ALPHACHANGE_TIME)
                self.tas.moveTo(PAPER_SCAN_POS)

                if pg.locate(self.tas.MATCHING_DATA, msg) is None:
                    return True
            
            if self.tas.WANTED_CHECK and self.tas.date >= self.tas.DAY_14 and len(self.tas.wanted) != 0:
                self.tas.click(INSPECT_BUTTON)
                self.tas.click(self.tas.wanted[0])
                self.tas.click(onTable(centerOf(doc.type_.layout.picture)))
                time.sleep(INSPECT_ALPHACHANGE_TIME)
                before = np.asarray(self.tas.getScreen().crop(TABLE_AREA))
                time.sleep(INSPECT_TIME - INSPECT_ALPHACHANGE_TIME)
                msg = bgFilter(before, np.asarray(self.tas.getScreen().crop(TABLE_AREA)))

                if pg.locate(self.tas.NO_CORRELATION, msg, confidence = 0.6) is None:
                    self.tas.wanted.pop(0)
                    self.tas.click(INSPECT_BUTTON)
                    time.sleep(INSPECT_ALPHACHANGE_TIME)
                    self.tas.moveTo(PAPER_SCAN_POS)
                    return True
                
                if len(self.tas.wanted) == 1: 
                    self.tas.click(INSPECT_BUTTON)
                    time.sleep(INSPECT_ALPHACHANGE_TIME)
                    self.tas.moveTo(PAPER_SCAN_POS)
                    return False

                self.tas.click(self.tas.wanted[1])
                before = np.asarray(self.tas.getScreen().crop(TABLE_AREA))
                time.sleep(INSPECT_TIME)
                msg = bgFilter(before, np.asarray(self.tas.getScreen().crop(TABLE_AREA)))

                if pg.locate(self.tas.NO_CORRELATION, msg, confidence = 0.6) is None:
                    self.tas.wanted.pop(1)
                    self.tas.click(INSPECT_BUTTON)
                    time.sleep(INSPECT_ALPHACHANGE_TIME)
                    self.tas.moveTo(PAPER_SCAN_POS)
                    return True

                if len(self.tas.wanted) == 2:
                    self.tas.click(INSPECT_BUTTON)
                    time.sleep(INSPECT_ALPHACHANGE_TIME)
                    self.tas.moveTo(PAPER_SCAN_POS)
                    return False
                
                self.tas.click(self.tas.wanted[2])
                self.tas.click(onTable(centerOf(doc.type_.layout.picture)))
                time.sleep(INSPECT_TIME)
                msg = bgFilter(before, np.asarray(self.tas.getScreen().crop(TABLE_AREA)))
                self.tas.click(INSPECT_BUTTON)
                time.sleep(INSPECT_ALPHACHANGE_TIME)
                self.tas.moveTo(PAPER_SCAN_POS)

                if pg.locate(self.tas.NO_CORRELATION, msg, confidence = 0.6) is None:
                    self.tas.wanted.pop(2)
                    return True
            
            return False
        
        # check self.tas.DAY_19 and self.tas.DAY_25 for an explanation about this
        if (
            (self.tas.date == self.tas.DAY_19 and doc.type_.nation == Nation.IMPOR) or
            (self.tas.date == self.tas.DAY_25 and doc.type_.nation == Nation.UNITEDFED)
        ): 
            self.tas.moveTo(PAPER_SCAN_POS)
            self.tas.dragTo(RIGHT_SCAN_SLOT)

            self.tas.moveTo(RULEBOOK_POS)
            self.tas.dragTo(PAPER_SCAN_POS)
            self.tas.click(self.tas.getRulebook()["basic-rules"]["pos"])

            self.tas.moveTo(PAPER_SCAN_POS)
            self.tas.dragTo(LEFT_SCAN_SLOT)

            self.tas.click(INSPECT_BUTTON)
            self.tas.click(onTable(rightSlot(centerOf(doc.type_.layout.label))))

            if doc.type_.nation == Nation.IMPOR:
                self.tas.click(leftSlot(self.tas.getRulebook()["basic-rules"]["no-entry-from-impor"]))
            else:
                self.tas.click(leftSlot(self.tas.getRulebook()["basic-rules"]["no-entry-from-unitedfed"]))

            time.sleep(INSPECT_INTERROGATE_TIME)
            self.tas.interrogate()

            self.tas.moveTo(RIGHT_SCAN_SLOT)
            self.tas.dragTo(PAPER_SCAN_POS)

            self.tas.moveTo(LEFT_SCAN_SLOT)
            self.tas.dragTo(PAPER_SCAN_POS)
            self.tas.putRulebookBack()

            self.tas.moveTo(PAPER_SCAN_POS)
            return True
        
        if doc.expiration <= self.tas.date:
            self.tas.click(INSPECT_BUTTON)
            self.tas.click(onTable(centerOf(doc.type_.layout.expiration)))
            self.tas.click(CLOCK_POS)
            time.sleep(INSPECT_INTERROGATE_TIME)
            self.tas.interrogate()
            self.tas.moveTo(PAPER_SCAN_POS)
            return True
        
        if doc.isSexWrong():
            self.tas.click(INSPECT_BUTTON)
            self.tas.click(onTable(centerOf(doc.type_.layout.sex)))
            self.tas.click(PERSON_POS)

            if self.tas.interrogateFailsafe():
                self.tas.moveTo(PAPER_SCAN_POS)
            else:
                time.sleep(INSPECT_INTERROGATE_TIME - INSPECT_TIME)
                self.tas.interrogate()
                self.tas.moveTo(PAPER_SCAN_POS)
                return True
        
        if doc.city not in doc.type_.cities:
            self.tas.moveTo(PAPER_SCAN_POS)
            self.tas.dragTo(RIGHT_SCAN_SLOT)

            self.tas.moveTo(RULEBOOK_POS)
            self.tas.dragTo(PAPER_SCAN_POS)
            self.tas.click(self.tas.getRulebook()["region-map"]["pos"])
            self.tas.click(self.tas.getRulebook()["region-map"][doc.type_.nation.value.lower()])

            self.tas.moveTo(PAPER_SCAN_POS)
            self.tas.dragTo(LEFT_SCAN_SLOT)

            self.tas.click(INSPECT_BUTTON)
            self.tas.click(onTable(textFieldOffset(rightSlot(doc.type_.layout.city[:2]))))
            self.tas.click(leftSlot(self.tas.getRulebook()["region-map"]["issuing-cities"]))

            time.sleep(INSPECT_INTERROGATE_TIME)
            self.tas.interrogate()

            self.tas.moveTo(RIGHT_SCAN_SLOT)
            self.tas.dragTo(PAPER_SCAN_POS)

            self.tas.moveTo(LEFT_SCAN_SLOT)
            self.tas.dragTo(PAPER_SCAN_POS)
            self.tas.putRulebookBack()

            self.tas.moveTo(PAPER_SCAN_POS)
            return True

        if self.tas.DAY4_PICTURE_CHECK:
            self.tas.click(INSPECT_BUTTON)
            self.tas.click(onTable(centerOf(doc.type_.layout.picture)))
            self.tas.click(PERSON_POS)
            time.sleep(INSPECT_ALPHACHANGE_TIME)
            before = np.asarray(self.tas.getScreen().crop(TABLE_AREA))
            time.sleep(INSPECT_TIME - INSPECT_ALPHACHANGE_TIME)
            msg = bgFilter(before, np.asarray(self.tas.getScreen().crop(TABLE_AREA)))
            
            if pg.locate(self.tas.MATCHING_DATA, msg) is None:
                time.sleep(INSPECT_INTERROGATE_TIME - INSPECT_TIME)
                self.tas.interrogate()
                return True
            
            self.tas.click(INSPECT_BUTTON)
            time.sleep(INSPECT_ALPHACHANGE_TIME)
            self.tas.moveTo(PAPER_SCAN_POS)
        
        if self.tas.WANTED_CHECK and len(self.tas.wanted) != 0:
            self.tas.click(INSPECT_BUTTON)
            self.tas.click(self.tas.wanted[0])
            self.tas.click(onTable(centerOf(doc.type_.layout.picture)))
            time.sleep(INSPECT_ALPHACHANGE_TIME)
            before = np.asarray(self.tas.getScreen().crop(TABLE_AREA))
            time.sleep(INSPECT_TIME - INSPECT_ALPHACHANGE_TIME)
            msg = bgFilter(before, np.asarray(self.tas.getScreen().crop(TABLE_AREA)))

            if pg.locate(self.tas.NO_CORRELATION, msg, confidence = 0.6) is None:
                self.tas.wanted.pop(0)
                time.sleep(INSPECT_INTERROGATE_TIME - INSPECT_TIME)
                self.tas.interrogate()
                self.tas.moveTo(PAPER_SCAN_POS)
                return True
            
            if len(self.tas.wanted) == 1: 
                self.tas.click(INSPECT_BUTTON)
                time.sleep(INSPECT_ALPHACHANGE_TIME)
                self.tas.moveTo(PAPER_SCAN_POS)
                return False

            self.tas.click(self.tas.wanted[1])
            before = np.asarray(self.tas.getScreen().crop(TABLE_AREA))
            time.sleep(INSPECT_TIME)
            msg = bgFilter(before, np.asarray(self.tas.getScreen().crop(TABLE_AREA)))

            if pg.locate(self.tas.NO_CORRELATION, msg, confidence = 0.6) is None:
                self.tas.wanted.pop(1)
                time.sleep(INSPECT_INTERROGATE_TIME - INSPECT_TIME)
                self.tas.interrogate()
                self.tas.moveTo(PAPER_SCAN_POS)
                return True

            if len(self.tas.wanted) == 2:
                self.tas.click(INSPECT_BUTTON)
                time.sleep(INSPECT_ALPHACHANGE_TIME)
                self.tas.moveTo(PAPER_SCAN_POS)
                return False
            
            self.tas.click(self.tas.wanted[2])
            self.tas.click(onTable(centerOf(doc.type_.layout.picture)))
            time.sleep(INSPECT_TIME)
            msg = bgFilter(before, np.asarray(self.tas.getScreen().crop(TABLE_AREA)))
            
            if pg.locate(self.tas.NO_CORRELATION, msg, confidence = 0.6) is None:
                self.tas.wanted.pop(2)
                time.sleep(INSPECT_INTERROGATE_TIME - INSPECT_TIME)
                self.tas.interrogate()
                self.tas.moveTo(PAPER_SCAN_POS)
                return True
            
            self.tas.click(INSPECT_BUTTON)
            time.sleep(INSPECT_ALPHACHANGE_TIME)
            self.tas.moveTo(PAPER_SCAN_POS)
        
        return False
    
    def checkVaxCertDiscrepancies(self, doc: VaxCert) -> bool:
        for vax in doc.vaccines:
            if vax.disease == Disease.POLIO:
                if vax.date + relativedelta(years = 3) <= self.tas.date:
                    self.tas.click(INSPECT_BUTTON)
                    self.tas.click(onTable(centerOf(
                        VaxCert.LAYOUT["vax-0"][:2] + offsetPoint(
                            VaxCert.LAYOUT["vax-0"][:2], 
                            Vaccine.LAYOUT["date"][2:]
                        )
                    )))
                    self.tas.click(CLOCK_POS)
                    time.sleep(INSPECT_INTERROGATE_TIME)
                    self.tas.interrogate()
                    self.tas.moveTo(PAPER_SCAN_POS)
                    return True

                return False
            
        # point out there's no polio vax
        self.tas.moveTo(PAPER_SCAN_POS)
        self.tas.dragTo(RIGHT_SCAN_SLOT)

        self.tas.moveTo(RULEBOOK_POS)
        self.tas.dragTo(PAPER_SCAN_POS)
        self.tas.click(self.tas.getRulebook()["documents"]["pos"])
        self.tas.click(self.tas.getRulebook()["documents"]["vax-cert"]["pos"])

        self.tas.moveTo(PAPER_SCAN_POS)
        self.tas.dragTo(LEFT_SCAN_SLOT)

        self.tas.click(INSPECT_BUTTON)
        self.tas.click(onTable(rightSlot(textFieldOffset(offsetPoint(VaxCert.LAYOUT["vax-0"][:2], Vaccine.LAYOUT["disease"][:2])))))
        self.tas.click(leftSlot(self.tas.getRulebook()["documents"]["vax-cert"]["polio-vax-required"]))
        time.sleep(INSPECT_INTERROGATE_TIME)
        self.tas.interrogate()

        self.tas.moveTo(RIGHT_SCAN_SLOT)
        self.tas.dragTo(PAPER_SCAN_POS)
        
        self.tas.moveTo(LEFT_SCAN_SLOT)
        self.tas.dragTo(PAPER_SCAN_POS)

        self.tas.putRulebookBack()
        self.tas.moveTo(PAPER_SCAN_POS)
        return True
    
    def checkWorkPassDiscrepancies(self, doc: WorkPass) -> bool:
        if self.tas.date < self.tas.DAY_18:
            if doc.until < self.tas.date + PERMIT_DURATIONS["1 MONTH"]: return True
            return doc.checkForgery(self.tas.date)
        
        if doc.until < self.tas.date + PERMIT_DURATIONS["1 MONTH"]: 
            self.tas.click(INSPECT_BUTTON)
            self.tas.click(centerOf(WorkPass.LAYOUT["until"]))
            self.tas.click(CLOCK_POS)
            time.sleep(INSPECT_INTERROGATE_TIME)
            self.tas.interrogate()
            self.tas.moveTo(PAPER_SCAN_POS)
            return True

        if doc.checkForgery(self.tas.date):
            self.tas.moveTo(PAPER_SCAN_POS)
            self.tas.dragTo(RIGHT_SCAN_SLOT)

            self.tas.moveTo(RULEBOOK_POS)
            self.tas.dragTo(PAPER_SCAN_POS)
            self.tas.click(self.tas.getRulebook()["documents"]["pos"])
            self.tas.click(self.tas.getRulebook()["documents"]["work-pass"]["pos"])

            self.tas.moveTo(PAPER_SCAN_POS)
            self.tas.dragTo(LEFT_SCAN_SLOT)

            self.tas.click(INSPECT_BUTTON)

            # if there's no seal
            if not bgFilter(np.asarray(doc.sealArea), np.asarray(WorkPass.BACKGROUNDS["seal-area"])).any():
                self.tas.click(onTable(rightSlot(centerOf(WorkPass.LAYOUT["seal-area"]))))
                self.tas.click(leftSlot(self.tas.getRulebook()["documents"]["work-pass"]["document-must-have-seal"]))
            else:
                try:
                    pos = Document.sealPos(
                        np.asarray(doc.sealArea), WorkPass.BACKGROUNDS["seal-area"],
                        WorkPass.BACKGROUNDS["seal-white"]
                    )
                except:
                    self.tas.click(onTable(rightSlot(centerOf(WorkPass.LAYOUT["seal-area"]))))
                    self.tas.click(leftSlot(self.tas.getRulebook()["documents"]["work-pass"]["document-must-have-seal"]))
                else:
                    self.tas.click(onTable(rightSlot(offsetPoint(textFieldOffset(pos), WorkPass.LAYOUT["seal-area"][:2]))))
                    self.tas.click(leftSlot(self.tas.getRulebook()["documents"]["work-pass"]["seals"]))

            time.sleep(INSPECT_INTERROGATE_TIME)
            self.tas.interrogate()

            self.tas.moveTo(RIGHT_SCAN_SLOT)
            self.tas.dragTo(PAPER_SCAN_POS)

            self.tas.moveTo(LEFT_SCAN_SLOT)
            self.tas.dragTo(PAPER_SCAN_POS)

            self.tas.putRulebookBack()
            self.tas.moveTo(PAPER_SCAN_POS)
            return True

        return False