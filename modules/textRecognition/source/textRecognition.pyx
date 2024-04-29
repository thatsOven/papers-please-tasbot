from PIL      import Image, ImageDraw, ImageFont
from datetime import date
import numpy as np
cimport cython

from modules.utils            import arrayEQWithTol
from modules.constants.other  import DATE_CHARS, TEXT_RECOGNITION_TOLERANCE
from modules.constants.screen import DIGITS_LENGTH, DIGITS_HEIGHT

class _Fonts:
    def __init__(self):
        self.MINI_KYLIE = None
        self.BM_MINI    = None
        self._04B03     = None

STATIC_OBJ = _Fonts()

cpdef int getCharLength(object font, str c, bint space):
    # i've never worked with truetype, but wtf?
    if font is STATIC_OBJ._04B03:
        if c == " ": return 3 if space else 2
        return int(font.getlength(c)) - (0 if space else 3)
    
    return int(font.getlength(c)) - (1 if space else 3)

@cython.boundscheck(False)
cpdef bint charCheck(
    object img, object bg, object font, 
    tuple textColor, str c, int x, int y, int l
):  
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

cpdef int digitLength(object _, object _a, bint space):
    return DIGITS_LENGTH - (0 if space else 2)

cpdef bint digitCheck(
    object img, object _, dict font, 
    tuple _a, str c, int x, int _b, int _c
):
    return np.array_equal(np.asarray(img.crop((x, 0, x + DIGITS_LENGTH, DIGITS_HEIGHT))), font[c])

@cython.cdivision(True)
@cython.boundscheck(False)
cdef int getAlign(object img, object bg):
    # this function performs a binarysearch-like algorithm to find the start of text

    cdef int a = 0
    cdef int b = img.size[0]
    cdef int m

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
cdef inline str _04b03Fix(str text):
    cdef str result = ""
    cdef int i = 0

    while i < len(text):
        if text[i] in "123456789" and i + 1 < len(text) and text[i + 1] == "O":
            result += text[i] + "0"
            i += 1
        else:
            result += text[i]
        i += 1

    return result

cpdef inline str parseText(
    object img, object bg, object font, 
    tuple textColor, str chars, 
    object endAt = None, bint misalignFix = False, object checkFn = charCheck, object lenFn = getCharLength
):
    if np.array_equal(np.asarray(img), np.asarray(bg)): return "" # if fg == bg there's no text
    
    # again... truetype, wtf?
    cdef int y
    if   font is STATIC_OBJ.MINI_KYLIE: y = -8
    elif font is STATIC_OBJ._04B03:     y = -2
    else:                               y = 0
    
    cdef int x, l
    if misalignFix: x = max(getAlign(img, bg) - 10, 0) # helps with characters that have blank spaces at beginning
    else:           x = 0
    
    cdef str  result = ""
    cdef str  c
    cdef bint begin = misalignFix
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
    
cpdef object parseDate(object img, object bg, object font, tuple textColor, object endAt = None):
    cdef list data = parseText(img, bg, font, textColor, DATE_CHARS, endAt = endAt).split(".")
    return date(1900 + int(data[0]), int(data[1]), int(data[2]))