from PIL       import Image
from typing    import Self
from functools import total_ordering
from datetime  import date, timedelta
import numpy as np

from modules.constants.screen import *

def bgFilter(before: np.ndarray, after: np.ndarray) -> np.ndarray:
    res = after.copy()
    res[np.all(after == before, axis = -1)] = [0, 0, 0]
    return res

def isolateNew(before: np.ndarray, after: np.ndarray) -> tuple[Image.Image, tuple[int, int]]:
    ys, xs = np.where((before != after).all(axis = -1))
    offs = (min(xs), min(ys))
    return Image.fromarray(after).crop(offs + (max(xs) + 1, max(ys) + 1)), offs

def centerOf(box: tuple[int, int, int, int]) -> tuple[int, int]:
    return (box[0] + (box[2] - box[0]) // 2, box[1] + (box[3] - box[1]) // 2)

def offsetBox(box: tuple[int, int, int, int], offs: tuple[int, int]) -> tuple[int, int, int, int]:
    return (box[0] + offs[0], box[1] + offs[1], box[2] + offs[0], box[3] + offs[1])

def offsetPoint(pt: tuple[int, int], offs: tuple[int, int]) -> tuple[int, int]:
    return (pt[0] + offs[0], pt[1] + offs[1])

def textFieldOffset(pt: tuple[int, int]) -> tuple[int, int]:
    return (pt[0] + 4, pt[1] + 4)

def rightSlot(pt: tuple[int, int]) -> tuple[int, int]:
    return (pt[0] + RIGHT_SCAN_SLOT[0] - PAPER_SCAN_POS[0], pt[1])

def leftSlot(pt: tuple[int, int]) -> tuple[int, int]:
    return (pt[0] - (PAPER_SCAN_POS[0] - LEFT_SCAN_SLOT[0]), pt[1])

def onTable(pt: tuple[int, int]) -> tuple[int, int]:
    return offsetPoint(pt, TABLE_AREA[:2])

def findDoc(documents, type_):
    for document in documents:
        if type(document) is type_:
            return document
    return None

def dateToDay(date: date) -> int:
    return (date + timedelta(days = 8)).day

def arrayEQWithTol(a: np.ndarray, b: np.ndarray, tol: int) -> bool:
    assert a.dtype == np.uint8
    assert b.dtype == np.uint8

    diff = a - b
    diff[diff >= 255 - tol] = 0
    return (diff <= tol).all()

def replaceColor(img: np.ndarray, srcColor: tuple[int, int, int], dstColor: tuple[int, int, int]) -> None:
    img[(img == srcColor).all(axis = -1)] = dstColor

def halfImage(img: Image.Image) -> Image.Image:
    return img.resize((img.size[0] // 2, img.size[1] // 2), Image.Resampling.NEAREST)

def doubleImage(img: Image.Image) -> Image.Image:
    return img.resize((img.size[0] * 2, img.size[1] * 2), Image.Resampling.NEAREST)

def cropCenter(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    base = (img.size[0] // 2 - size[0] // 2, img.size[1] // 2 - size[1] // 2)
    return img.crop(base + offsetPoint(base, size))

@total_ordering
class Name:
    def __init__(self, first: str, last: str):
        self.first = first.strip().lower()
        self.last  = last.strip().lower()

    @staticmethod
    def fromPassportOrID(parsed: str) -> Self:
        parsed = parsed.split(",")
        return Name(parsed[1], parsed[0])
    
    @staticmethod
    def fromPermitOrPass(parsed: str) -> Self:
        return Name(*parsed.split(" "))
    
    def __repr__(self) -> str:
        return f"Name({self.first.capitalize()}, {self.last.capitalize()})"
    
    def __str__(self) -> str:
        return f"{self.first.capitalize()} {self.last.capitalize()}"
    
    def __eq__(self, other) -> bool:
        if type(other) is not Name: return False
        return self.first == other.first and self.last == other.last
    
    def __le__(self, other) -> bool:
        if type(other) is not Name: return False
        return self.first + self.last < other.first + other.last