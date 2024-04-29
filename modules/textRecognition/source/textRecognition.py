from PIL      import Image, ImageDraw, ImageFont
from datetime import date
import numpy as np

from modules.utils            import arrayEQWithTol
from modules.constants.other  import DATE_CHARS, TEXT_RECOGNITION_TOLERANCE
from modules.constants.screen import DIGITS_LENGTH, DIGITS_HEIGHT

def STATIC_OBJ(): ...

def getCharLength(font: ImageFont.FreeTypeFont, c: str, space: bool = False) -> int:
    # i've never worked with truetype, but wtf?
    if font is STATIC_OBJ._04B03:
        if c == " ": return 3 if space else 2
        return int(font.getlength(c)) - (0 if space else 3)
    
    return int(font.getlength(c)) - (1 if space else 3)

def charCheck(
    img: Image.Image, bg: Image.Image, font: ImageFont.FreeTypeFont, 
    textColor: tuple[int, int, int], c: str, x: int, y: int, l: int
) -> bool:  
    # draw character on right position in background
    testImg = bg.copy()
    draw = ImageDraw.Draw(testImg, mode = "RGB")
    draw.fontmode = "1" # disable antialiasing

    draw.text((x - 1, y), c, textColor, font)

    # workaround for slightly wrong fonts
    if font is STATIC_OBJ.BM_MINI:
        # covers wrong pixels
        if c == "6":
            corrBox = (x + 6, 2, x + 8, 4)
            testImg.paste(bg.crop(corrBox), corrBox[:2])
        elif c == "9":
            corrBox = (x, 8, x + 2, 10)
            testImg.paste(bg.crop(corrBox), corrBox[:2])
    elif font is STATIC_OBJ._04B03:
        if c == "A":
            corrBox = (x + 2, 6, x + 6, 8)
            corrBg = bg.crop(corrBox)
            corrFg = corrBg.copy()
            corrFg.paste(textColor, (0, 0) + corrFg.size)
            testImg.paste(corrBg, corrBox[:2]) # cover wrong pixels
            testImg.paste(corrFg, (x + 2, 4))  # replace bg with correct pixels

    box = (x, 0, l + x + 2, img.size[1])
    return arrayEQWithTol(np.asarray(img.crop(box)), np.asarray(testImg.crop(box)), TEXT_RECOGNITION_TOLERANCE)

def digitLength(_, _a, space) -> int:
    return DIGITS_LENGTH - (0 if space else 2)

def digitCheck(
    img: Image.Image, _, font: dict[str, np.ndarray], 
    _a, c: str, x: int, _b, _c
) -> bool:
    return np.array_equal(np.asarray(img.crop((x, 0, x + DIGITS_LENGTH, DIGITS_HEIGHT))), font[c])

def getAlign(img: Image.Image, bg: Image.Image) -> int:
    # this function performs a binarysearch-like algorithm to find the start of text

    a = 0
    b = img.size[0]

    while a < b:
        m = a + (b - a) // 2
        if a == m: break

        box = (a, 0, m, img.size[1])
        if np.array_equal(np.asarray(img.crop(box)), np.asarray(bg.crop(box))):
              a = m
        else: b = m - 1

    return b

# 04b03 has the same character for zero and capital "O"
# so we make some assumptions to try to parse the right character
def _04b03Fix(text: str) -> str:
    return (
        text
        .replace("1O", "10")
        .replace("2O", "20")
        .replace("3O", "30")
        .replace("4O", "40")
        .replace("5O", "50")
        .replace("6O", "60")
        .replace("7O", "70")
        .replace("8O", "80")
        .replace("9O", "90")
    )

def parseText(
    img: Image.Image, bg: Image.Image, font: ImageFont.FreeTypeFont, 
    textColor: tuple[int, int, int], chars: str, *, 
    endAt = None, misalignFix = False, checkFn = charCheck, lenFn = getCharLength
):
    if np.array_equal(np.asarray(img), np.asarray(bg)): return "" # if fg == bg there's no text

    # again... truetype, wtf?
    if   font is STATIC_OBJ.MINI_KYLIE: y = -8
    elif font is STATIC_OBJ._04B03:     y = -2
    else:                               y = 0
    
    if misalignFix: x = max(getAlign(img, bg) - 10, 0) # helps with characters that have blank spaces at beginning
    else:           x = 0
    
    result = ""
    begin = misalignFix
    while x < img.size[0]:
        added = None
        for c in chars:
            if begin and c == " ": continue

            # avoids out of bound accesses that read wrong image data
            l = lenFn(font, c, False)
            if x + l >= img.size[0]: 
                x += l
                break
            
            if checkFn(img, bg, font, textColor, c, x, y, l):
                added = c
                break

        if added is None: x += 1
        else:
            begin   = False
            result += added         
            x      += lenFn(font, added, True)

        if endAt is not None and result.endswith(endAt): break

    if font is STATIC_OBJ._04B03: return _04b03Fix(result.strip())
    return result.strip()
    
def parseDate(img: Image.Image, bg: Image.Image, font: ImageFont.FreeTypeFont, textColor: tuple[int, int, int], *, endAt = None):
    data = parseText(img, bg, font, textColor, DATE_CHARS, endAt = endAt).split(".")
    return date(1900 + int(data[0]), int(data[1]), int(data[2]))