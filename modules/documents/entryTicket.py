from PIL import Image
import os, datetime, pyautogui as pg, numpy as np

from modules.documents.document import Document
from modules.textRecognition    import parseDate
from modules.utils              import doubleImage

class EntryTicket(Document):
    LABEL: np.ndarray          = None
    TRACK_IMAGE: Image.Image   = None
    INNER_TEXTURE: Image.Image = None

    TEXT_COLOR = (119, 103, 137)
    LAYOUT = {
        "date" : (  0,   0,  67,  12), 
        "label": (347, 179, 499, 203)
    }

    @staticmethod
    def load():
        EntryTicket.TRACK_IMAGE = Image.open(
            os.path.join(EntryTicket.TAS.ASSETS, "papers", "entryTicket", "trackImage.png")
        ).convert("RGB")

        EntryTicket.INNER_TEXTURE = doubleImage(Image.open(os.path.join(EntryTicket.TAS.ASSETS, "papers", "entryTicket", "inner.png")).convert("RGB"))
        EntryTicket.LABEL = np.asarray(EntryTicket.INNER_TEXTURE.crop(EntryTicket.LAYOUT["label"]))

    @staticmethod
    def checkMatch(docImg: Image.Image) -> bool:
        return np.array_equal(np.asarray(docImg.crop(EntryTicket.LAYOUT["label"])), EntryTicket.LABEL)
    
    @Document.field
    def date(self) -> datetime.date:
        trackBox  = pg.locate(EntryTicket.TRACK_IMAGE, self.docImg)
        trackBox  = (trackBox[0] + trackBox[2], trackBox[1])
        trackBox += (trackBox[0] + EntryTicket.LAYOUT["date"][2], trackBox[1] + EntryTicket.LAYOUT["date"][3])
        
        return parseDate(
            self.docImg.crop(trackBox), 
            EntryTicket.INNER_TEXTURE.crop(trackBox),
            EntryTicket.TAS.FONTS["bm-mini"], EntryTicket.TEXT_COLOR
        )

    def __repr__(self):
        return f"EntryTicket({self.date})"