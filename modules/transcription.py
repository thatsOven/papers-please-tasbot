from PIL   import Image
from enum  import Enum
import os, pyautogui as pg, numpy as np

from modules.constants.screen   import *
from modules.constants.other    import *
from modules.utils              import *

from modules.textRecognition import parseText

import logging
logger = logging.getLogger(__name__)

class Who(Enum):
    INSPECTOR, ENTRANT = "INSPECTOR", "ENTRANT"

class MessageLoc:
    def __init__(self, page, box):
        self.page: int                      = page
        self.box: tuple[int, int, int, int] = box

class Message:
    def __init__(self, who, message, at):
        self.who: Who       = who
        self.message        = message
        self.at: MessageLoc = at

    def __repr__(self):
        return f"{self.who.value}: {self.message}"
    
class AnalyzeData:
    def __init__(self):
        self.status           = None
        self.message: Message = None

    def reset(self):
        self.status  = None
        self.message = None
    
class Transcription:
    TAS = None

    NEXT = None
    BACK = None

    @staticmethod
    def load():
        Transcription.NEXT = Image.open(
            os.path.join(Transcription.TAS.ASSETS, "transcription", "next.png")
        ).convert("RGB")
        Transcription.BACK = Image.open(
            os.path.join(Transcription.TAS.ASSETS, "transcription", "back.png")
        ).convert("RGB")

    def __init__(self, tas):
        self.conversation: list[Message] = []
        self.__purpose    = AnalyzeData()
        self.__duration   = AnalyzeData()
        self.__detainable = AnalyzeData()

        self.__missingDocs = {
            "EntryTicket":   AnalyzeData(),
            "EntryPermit":   AnalyzeData(),
            "WorkPass":      AnalyzeData(),
            "ArstotzkanID":  AnalyzeData(), 
            "IDSupplement":  AnalyzeData(),
            "GrantOfAsylum": AnalyzeData(),
            "AccessPermit":  AnalyzeData(),
            "VaxCert":       AnalyzeData()
        }

        self.__tas = tas
        self.__currPage  = 0

    def reset(self):
        self.conversation.clear()
        self.__purpose.reset()
        self.__duration.reset()
        self.__detainable.reset()
        self.__currPage  = 0

        for value in self.__missingDocs.values():
            value.reset()

    def __reducePage(self, page: Image.Image):
        a = 0
        b = page.size[1]

        while a < b:
            m = a + (b - a) // 2
            if a == m: break

            box = (0, m, page.size[0], b)
            orig = page.crop(box)
            test = orig.copy()
            test.paste(TRANSCRIPTION_BG_COLOR, (0, 0, page.size[0], b - a))
            if np.array_equal(np.asarray(orig), np.asarray(test)):
                  b = m
            else: a = m + 1
        
        return page.crop((0, 0, page.size[0], min(a + 10, page.size[1])))
    
    def __get(self):
        before = np.asarray(self.__tas.getScreen().crop(TABLE_AREA))
        self.__tas.moveTo(TRANSCRIPTION_POS)
        self.__tas.dragTo(PAPER_SCAN_POS)
        self.__tas.moveTo(TRANSCRIPTION_POS) # move cursor out of the way
        return before
    
    def __putBack(self):
        self.__tas.moveTo(PAPER_SCAN_POS)
        self.__tas.dragTo(TRANSCRIPTION_POS)
        self.__tas.moveTo(PAPER_SCAN_POS)

    def __getPages(self) -> list[Image.Image]:
        before = self.__get()
        
        pages = []
        while True:
            fullPage = Image.fromarray(
                bgFilter(before, np.asarray(self.__tas.getScreen().crop(TABLE_AREA)))
            )

            pages.append(self.__reducePage(fullPage.crop(TRANSCRIPTION_PAGE_TEXT_AREA)))

            box = pg.locate(Transcription.NEXT, fullPage)
            if box is None: break

            self.__currPage  += 1
            self.__tas.click(onTable(pg.center(box)))
            self.__tas.moveTo(TRANSCRIPTION_POS)

        self.__putBack()
        return pages

    def __getTextBoxes(self, pages: list[Image.Image]) -> list[Message]:
        boxes = []
        for pageN, page in enumerate(pages):
            yStart = TRANSCRIPTION_TEXTBOX_TEXT_OFFSET[1]
            yEnd   = yStart + TRANSCRIPTION_TEXT_Y_SIZE
        
            while True:
                yTest = yEnd + TRANSCRIPTION_TEXTBOXES_Y_OFFSET
                
                if yTest + 3 >= page.size[1]: break

                orig = page.crop((0, yTest + 1, page.size[0], yTest + 3))
                test0 = orig.copy()
                test1 = orig.copy()
                test0.paste(  TRANSCRIPTION_BG_COLOR, (0, 0) + test0.size)
                test1.paste(TRANSCRIPTION_TEXT_COLOR, (0, 0) + test1.size)

                orig = np.asarray(orig)

                if (
                    arrayEQWithTol(orig, np.asarray(test0), TEXT_RECOGNITION_TOLERANCE) or
                    arrayEQWithTol(orig, np.asarray(test1), TEXT_RECOGNITION_TOLERANCE)
                ):
                    cropBox = (0, yStart, page.size[0], yEnd)
                    textBox = page.crop(cropBox)

                    if arrayEQWithTol(
                        np.asarray(textBox)[0, 0], np.asarray(TRANSCRIPTION_BG_COLOR, dtype = np.uint8), 
                        TEXT_RECOGNITION_TOLERANCE
                    ):    who = Who.ENTRANT
                    else: who = Who.INSPECTOR

                    boxes.append(Message(
                        who, 
                        textBox.crop((TRANSCRIPTION_TEXTBOX_TEXT_OFFSET[0], 0) + textBox.size), # removes little left border
                        MessageLoc(pageN, offsetBox(cropBox, TRANSCRIPTION_PAGE_TEXT_AREA[:2]))
                    ))

                    yStart = yTest  + TRANSCRIPTION_TEXTBOX_TEXT_OFFSET[1]
                    yEnd   = yStart + TRANSCRIPTION_TEXT_Y_SIZE
                else:
                    yEnd = yTest + TRANSCRIPTION_TEXT_Y_SIZE

        return boxes
    
    def __parseTextbox(self, textBox: Message) -> Message:
        if textBox.who == Who.ENTRANT:
            textColor = TRANSCRIPTION_TEXT_COLOR
            bgColor   = TRANSCRIPTION_BG_COLOR
        else:
            textColor = TRANSCRIPTION_BG_COLOR
            bgColor   = TRANSCRIPTION_TEXT_COLOR

        y   = 0
        res = ""
        while y + TRANSCRIPTION_TEXT_Y_SIZE <= textBox.message.size[1]:
            textImg = textBox.message.crop((0, y, textBox.message.size[0], y + TRANSCRIPTION_TEXT_Y_SIZE))
            bg = textImg.copy()
            bg.paste(bgColor, (0, 0) + bg.size)

            res += parseText(
                textImg, bg, Transcription.TAS.FONTS["04b03"], textColor, TRANSCRIPTION_CHARS, 
                endAt = "  " 
            )

            y   += TRANSCRIPTION_TEXT_Y_SIZE + TRANSCRIPTION_LINE_OFFSET
            res += " "

        return Message(textBox.who, res.strip(), textBox.at)
    
    def __analyze(self, conversation: list[Message]):
        getPurpose  = False
        getDuration = False
        missingDoc  = None

        for message in conversation:
            if message.who == Who.INSPECTOR:
                if self.__purpose.status is None and message.message == ASK_PURPOSE:
                    getPurpose = True
                    continue

                if self.__duration.status is None and message.message == ASK_DURATION:
                    getDuration = True
                    continue

                if missingDoc is None and message.message in ASK_MISSING_DOC:
                    missingDoc = ASK_MISSING_DOC[message.message]
                    continue

                detainable = message.message in DETAIN_PHRASES
                if detainable or message.message in OTHER_DISCREPANCY_PHRASES:
                    self.__detainable.status = detainable
                    continue
            else:
                if message.message in NO_PURPOSE_SCRIPTED_ENTRANT_PHRASES:
                    getPurpose  = False
                    getDuration = False

                    self.__purpose.status  = NO_PURPOSE_SCRIPTED_ENTRANT_PHRASES[message.message][0]
                    self.__duration.status = NO_PURPOSE_SCRIPTED_ENTRANT_PHRASES[message.message][1]
                    continue

                if getPurpose:
                    getPurpose = False
                    if message.message in PURPOSES:
                          self.__purpose.status = PURPOSES[message.message]
                    else: self.__purpose.status = message.message
                    self.__purpose.message = message

                    if self.__purpose.status in (Purpose.ASYLUM, Purpose.DIPLOMAT, Purpose.IMMIGRATION):
                        getDuration = False
                        
                        self.__duration.status  = PERMIT_DURATIONS["FOREVER"]
                        self.__duration.message = message
                    continue

                if getDuration:
                    getDuration = False
                    self.__duration.message = message

                    if message.message == I_DONT_PLAN_TO_LEAVE:
                        self.__duration.status = PERMIT_DURATIONS["FOREVER"]
                        continue

                    for stay in RANDOM_STAY:
                        if message.message.startswith(stay):
                            shifted = message.message[len(stay) + 1:]
                            if shifted in STAY_DURATIONS:
                                self.__duration.status = STAY_DURATIONS[shifted]
                                break
                    else: 
                        self.__duration.status = message.message
                    continue

                if missingDoc is not None:
                    hasDoc = message.message in MISSING_DOC_GIVEN 
                    self.__missingDocs[missingDoc].status = hasDoc

                    if self.__detainable.status is None and not hasDoc:
                        self.__detainable.status = False

                    missingDoc = None
                    continue

    def update(self):
        pages = self.__getPages()
        if pages is None: return

        self.conversation = [self.__parseTextbox(box) for box in self.__getTextBoxes(pages)]
        self.__analyze(self.conversation)

        if Transcription.TAS.DEBUG:
            for line in self.conversation:
                logger.info(line)

    def __getPos(self, field: AnalyzeData) -> tuple[int, int, int, int] | None:
        if field.message is None:
            self.update()

        if field.message is None:
            return None
        
        if field.message.at.page != self.__currPage:
            before = self.__get()

            if self.__currPage < field.message.at.page:    
                while self.__currPage < field.message.at.page:
                    self.__tas.click(onTable(pg.center(pg.locate(Transcription.NEXT, Image.fromarray(
                        bgFilter(before, np.asarray(self.__tas.getScreen().crop(TABLE_AREA)))
                    )))))
                    self.__currPage += 1
            else:
                while self.__currPage > field.message.at.page:
                    self.__tas.click(onTable(pg.center(pg.locate(Transcription.BACK, Image.fromarray(
                        bgFilter(before, np.asarray(self.__tas.getScreen().crop(TABLE_AREA)))
                    )))))
                    self.__currPage -= 1

            self.__putBack()

        return field.message.at.box
    
    def __getField(self, field: AnalyzeData):
        if field.status is None:
            self.update()
        return field.status

    def getPurpose(self) -> str | None:
        return self.__getField(self.__purpose)
    
    def getPurposePos(self) -> tuple[int, int, int, int] | None:
        return self.__getPos(self.__purpose)
    
    def getDuration(self) -> str | None:
        return self.__getField(self.__duration)
    
    def getDurationPos(self) -> tuple[int, int, int, int] | None:
        return self.__getPos(self.__duration)
    
    def getMissingDocGiven(self, type_) -> bool | None:
        return self.__getField(self.__missingDocs[type_])

    def getDetainable(self) -> bool | None:
        return self.__getField(self.__detainable)
    
    def waitFor(self, fn):
        while True:
            res = fn()
            if res is not None: return res