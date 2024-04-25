from PIL    import Image
from typing import Self
import os, datetime, pyautogui as pg, numpy as np

from modules.documents.document import Document, getBox, convertBox
from modules.textRecognition    import parseDate
from modules.utils              import doubleImage

class EntryTicket(Document):
    LABEL: np.ndarray          = None
    TRACK_IMAGE: Image.Image   = None
    INNER_TEXTURE: Image.Image = None

    TABLE_OFFSET = (245, 159)
    TEXT_COLOR   = (119, 103, 137)
    LAYOUT = {
        "date" : getBox(  0,   0,  66,  11), 
        "label": getBox(347, 179, 498, 202)
    }

    @staticmethod
    def load():
        EntryTicket.TRACK_IMAGE = Image.open(
            os.path.join(EntryTicket.TAS.ASSETS, "papers", "entryTicket", "trackImage.png")
        ).convert("RGB")

        EntryTicket.INNER_TEXTURE = doubleImage(Image.open(os.path.join(EntryTicket.TAS.ASSETS, "papers", "entryTicket", "inner.png")).convert("RGB"))
        EntryTicket.LABEL = np.asarray(EntryTicket.INNER_TEXTURE.crop(convertBox(EntryTicket.LAYOUT["label"], EntryTicket.TABLE_OFFSET)))

    @staticmethod
    def checkMatch(docImg: Image.Image) -> bool:
        return np.array_equal(np.asarray(docImg.crop(EntryTicket.LAYOUT["label"])), EntryTicket.LABEL)
    
    @staticmethod
    def parse(docImg: Image.Image) -> Self:
        trackBox  = pg.locate(EntryTicket.TRACK_IMAGE, docImg)
        trackBox  = (trackBox[0] + trackBox[2], trackBox[1])
        trackBox += (trackBox[0] + EntryTicket.LAYOUT["date"][2], trackBox[1] + EntryTicket.LAYOUT["date"][3])
        
        return EntryTicket(parseDate(
            docImg.crop(trackBox), 
            EntryTicket.INNER_TEXTURE.crop(convertBox(trackBox, EntryTicket.TABLE_OFFSET)),
            EntryTicket.TAS.FONTS["bm-mini"], EntryTicket.TEXT_COLOR
        ))

    def __init__(self, date):
        self.date: datetime.date = date

    def __repr__(self):
        return f"EntryTicket({self.date})"