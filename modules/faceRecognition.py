# **NOTE**
# this module here does face recognition using lookup tables based on every possible face the game can generate.
# the faces in the lookup tables though are generated using a replica of the latest game version's face generation 
# algorithm, so this approach won't work on the version of the game the bot is currently compatible with. 
# this is here to keep the code functional, but it's essentially doing nothing in the current state of things

from PIL     import Image
from enum    import Enum
from hashlib import md5
from typing  import Self, Type, ClassVar, TYPE_CHECKING
import os, numpy as np

from modules.constants.other    import Description, Sex, TASException
from modules.documents.document import BaseDocument
from modules.utils              import *

import logging

logger = logging.getLogger('tas.' + __name__)

if TYPE_CHECKING:
    from tas import TAS

MD5_BYTES  = 16
DATA_BYTES = 2

HEAD_BITS      = 5
HEAD_MASK      = 0x001F
EYES_BITS      = 5
EYES_MASK      = 0x03E0
NOSEMOUTH_BITS = 5
NOSEMOUTH_MASK = 0x7B00
SEX_MASK       = 0x8000

class FaceType(Enum):
    PERSON, PASSPORT_PICTURE, ID_PICTURE, GRANT_PICTURE, WANTED_PICTURE = "people", "passport", "id", "grant", ""

class FacePiece(Enum):
    NOSE_MOUTH, EYES, HEAD = "noseMouth", "eyes", "head"

class Face:
    TAS: ClassVar[Type["TAS"]] = None

    ORIGINAL_FG_COLOR: ClassVar[tuple[int, int, int]]      = ( 87,  72,  72)
    ORIGINAL_BG_COLOR: ClassVar[tuple[int, int, int]]      = (162, 148, 144)
    ID_PICTURE_FG_COLOR: ClassVar[tuple[int, int, int]]    = ( 61,  57,  77)
    ID_PICTURE_BG_COLOR: ClassVar[tuple[int, int, int]]    = (178, 156, 204)
    GRANT_PICTURE_FG_COLOR: ClassVar[tuple[int, int, int]] = (125, 109, 121)

    PASSPORT_CROP_AMT: ClassVar[int]  = 33
    GRANT_CROP_AMT: ClassVar[int]     = 53
    ID_WANTED_CROP_AMT: ClassVar[int] = 30 

    CM_PER_PIXEL: ClassVar[float] = 0.909
    MIN_HEIGHT:   ClassVar[float] = 100.0

    PALETTES: ClassVar[tuple[tuple[tuple[int, int, int], ...], ...]] = (
        (( 85, 27, 24), (137,  44,  39), (61, 80, 67), (132, 138, 107), (222, 214, 172)),
        ((  0, 51, 67), ( 40, 116, 103), (66, 82, 98), (133, 164, 177), (170, 202, 199)),
        (( 38, 38, 38), ( 73,  73,  73), (67, 36, 36), (172, 107,  71), (216, 171, 137)),
        (( 56, 90, 64), (123, 150,  93), (58, 50, 80), (146, 137, 170), (180, 212, 223)),
        (( 82, 34, 65), (147,  61, 118), (91, 41, 24), (173, 114,  88), (221, 189, 201)),
        ((139, 65, 84), (208, 120, 143), (87, 43, 19), (186, 134,  87), (241, 213, 112)),
        (( 25, 18, 18), ( 73,  73,  73), (66, 82, 98), (133, 164, 177), (170, 202, 199)),
        (( 80, 70, 49), (160, 139,  97), (80, 70, 49), (160, 139,  97), (208, 198, 177))
    )

    BASE_PALETTE_IDX: ClassVar[int] = 0
    RECON_COLORS: ClassVar[tuple[tuple[int, int, int], ...]] = tuple(palette[-1] for palette in PALETTES)
    PALETTE_DOUBT: ClassVar[dict[int, dict[tuple[int, int, int], int]]] = {
        1: {
            ( 0, 51, 67): 1,
            (25, 18, 18): 6
        },
        6: {
            ( 0, 51, 67): 1,
            (25, 18, 18): 6
        }
    }

    PARTS_DESCRIPTIONS: ClassVar[dict[FacePiece, dict[Sex, dict[int, Description]]]] = {
        FacePiece.NOSE_MOUTH: {
            Sex.F: {},
            Sex.M: {
                3:  Description.MUSTACHE,
                4:  Description.MUSTACHE,
                11: Description.MUSTACHE,
                15: Description.MUSTACHE,
                19: Description.MUSTACHE
            }
        },
        FacePiece.EYES: {
            Sex.F: {
                1:  Description.GLASSES,
                13: Description.GLASSES
            },
            Sex.M: {
                0: Description.GOOD_VISION,
                2: Description.GLASSES,
                5: Description.PERFECT_VISION
            }
        },
        FacePiece.HEAD: {
            Sex.F: {
                0:  Description.WAVY_HAIR,
                1:  Description.SMALL_HEAD,
                2:  Description.OVERWEIGHT,
                3:  Description.BOBBED_HAIR,
                4:  Description.STRAIGHT_HAIR,
                5:  Description.BOBBED_HAIR,
                6:  Description.SHORT_HAIR,
                7:  Description.VERY_SHORT_HAIR,
                8:  Description.SHORT_HAIR,
                9:  Description.OVERWEIGHT,
                10: Description.BOBBED_HAIR,
                11: Description.SHORT_CURLY_HAIR,
                12: Description.CURLY_BOBBED_HAIR,
                13: Description.SHORT_WAVY_HAIR,
                14: Description.BOBBED_HAIR,
                15: Description.LONG_HAIR,
                16: Description.STRAIGHT_HAIR,
                17: Description.BOBBED_HAIR,
                18: Description.DARK_HAIR,
                19: Description.LONG_HAIR
            },
            Sex.M: {
                0:  Description.SHORT_HAIR,
                1:  Description.BALD,
                2:  Description.DARK_HAIR,
                3:  Description.BEARD,
                4:  Description.GOATEE,
                5:  Description.SHORT_CROPPED_HAIR,
                6:  Description.BALDING,
                7:  Description.BALDING,
                8:  Description.SHORT_STRAIGHT_HAIR,
                9:  Description.SHORT_LIGHT_HAIR,
                10: Description.WIDOWS_PEAK,
                11: Description.TALL_FOREHEAD,
                12: Description.KILLER_SIDEBURNS,
                13: Description.BOBBED_HAIR,
                14: Description.SHORT_CURLY_HAIR,
                15: Description.BALD,
                16: Description.MOHAWK,
                17: Description.SHORT_CURLY_HAIR,
                18: Description.UNKEMPT_CURLY_HAIR
            }
        }
    }

    HAIR_HEIGHT: ClassVar[dict[Sex, tuple[int, ...]]] = {
        Sex.M: (0, 5, 4, 6, 4, 4, 5, 2, 4, 2, 7, 10, 8, 12, 3, 6, 0, 18, 4, 4) + (10, ) * 8,
        Sex.F: (10, 3, -7, -6, 3, 5, 2, 0, 4, 2, 5, 13, 9, 5, 8, 14, 5, 3, 7, 23)
    }

    TABLES: ClassVar[dict[FaceType, dict[bytes, Self]]] = {}

    @staticmethod
    def loadTable(file: str) -> dict[bytes, Self]:
        result = {}
        with open(file, "rb") as f:
            while True:
                key = f.read(MD5_BYTES)
                if not key: break
                value = f.read(DATA_BYTES)
                if not value:
                    raise TASException("Invalid table file (key with no value)")
                
                value = int.from_bytes(value)
                result[key] = Face(
                    head      =  value &      HEAD_MASK,
                    eyes      = (value &      EYES_MASK) >>  HEAD_BITS,
                    noseMouth = (value & NOSEMOUTH_MASK) >> (EYES_BITS + HEAD_BITS),
                    sex       = Sex(bool(value & SEX_MASK)) 
                )

        return result

    @staticmethod
    def load() -> None:
        for type_ in FaceType:
            if type_ == FaceType.WANTED_PICTURE: continue

            if type_ != FaceType.PERSON: continue # TODO add pictures tables
            
            logger.info(f"Loading lookup table for {type_}...")
            Face.TABLES[type_] = Face.loadTable(os.path.join(Face.TAS.ASSETS, "faces", f"{type_.value}.ptbt"))

        # these are the same, so we just use the same table for both
        # Face.TABLES[FaceType.WANTED_PICTURE] = Face.TABLES[FaceType.ID_PICTURE] # TODO add pictures tables
    
    @staticmethod
    def getHeightFromY(y: float, hairHeight: int) -> float:
        return round((y - hairHeight) * Face.CM_PER_PIXEL + Face.MIN_HEIGHT, 2)
    
    @staticmethod
    def __checkMask(color: tuple[int, int, int], img: np.ndarray) -> bool:
        return len(np.where((img == np.asarray(color, dtype = np.uint8)).all(axis = -1))[0]) != 0
            
    @staticmethod
    def getPalette(img: Image.Image) -> int | None:
        imgData = np.asarray(img)

        idx = None
        for i, color in enumerate(Face.RECON_COLORS):
            if Face.__checkMask(color, imgData):
                idx = i
                break
        else: return None
        
        if idx in Face.PALETTE_DOUBT:
            for color in Face.PALETTE_DOUBT[idx].keys():
                if Face.__checkMask(color, imgData):
                    return Face.PALETTE_DOUBT[idx][color]
                
        return idx
    
    @staticmethod
    def toBasePalette(img: Image.Image, paletteIdx: int) -> Image.Image:
        if paletteIdx == Face.BASE_PALETTE_IDX:
            return img
        
        imgData = np.asarray(img).copy()
        
        currPalette = Face.PALETTES[paletteIdx]
        basePalette = Face.PALETTES[Face.BASE_PALETTE_IDX]
        for i in range(len(currPalette)):
            # this doesn't happen, but yknow if you wanna edit textures and whatever...
            # better have it and not need it
            if currPalette[i] == basePalette[i]:
                continue 
            
            replaceColor(imgData, currPalette[i], basePalette[i])

        return Image.fromarray(imgData)
    
    @staticmethod
    def replacePictureColors(img: Image.Image, fgColor: tuple[int, int, int], bgColor: tuple[int, int, int]) -> Image.Image:
        imgData = np.asarray(img).copy() 
        replaceColor(imgData, fgColor, Face.ORIGINAL_FG_COLOR) 
        replaceColor(imgData, bgColor, Face.ORIGINAL_BG_COLOR) 
        return Image.fromarray(imgData)
    
    @staticmethod
    def maskCropFace(image: Image.Image) -> tuple[Image.Image, int]:
        mask   = np.asarray(image).copy()
        masked = np.asarray(image).copy()

        # replace every face color with white to form mask
        for color in Face.PALETTES[Face.BASE_PALETTE_IDX][2:]:
            replaceColor(mask, color, (255, 255, 255))

        # replace everything that's not face with black
        masked[(mask != (255, 255, 255)).all(axis = -1)] = (0, 0, 0)
        # find ys and xs of all white pixels in picture
        ys, xs = np.where((mask == (255, 255, 255)).all(axis = -1))

        # crop (min_x, min_y, max_x, max_y) with values found earlier
        top = min(ys)
        return Image.fromarray(masked).crop((min(xs), top, max(xs) + 1, max(ys) + 1)), top
    
    @staticmethod
    def cropHighest(image: Image.Image, color: tuple[int, int, int], cropAmt: int) -> Image.Image:
        y = min(np.where((np.asarray(image) == color).all(axis = -1))[0])
        return image.crop((0, y, image.size[0], y + cropAmt))

    # this would have to be patched for different scalings (this game version uses 2x2 squares for each pixel)
    @staticmethod
    def fixImage(img: Image.Image) -> Image.Image:
        return halfImage(img)

    @staticmethod
    def parse(img: Image.Image, type_: FaceType) -> Self | None:
        img = Face.fixImage(img)
        
        heightPx = None
        match type_:
            case FaceType.PERSON:
                palette = Face.getPalette(img)
                if palette is None: return None
                fixed, topY = Face.maskCropFace(Face.toBasePalette(img, palette)) 
                heightPx = img.size[1] - topY
            case FaceType.GRANT_PICTURE:
                fixed = Face.cropHighest(img, Face.GRANT_PICTURE_FG_COLOR, Face.GRANT_CROP_AMT) 
            case FaceType.PASSPORT_PICTURE:
                fixed = Face.cropHighest(img, Face.ORIGINAL_FG_COLOR, Face.PASSPORT_CROP_AMT) 
            case FaceType.ID_PICTURE | FaceType.WANTED_PICTURE:
                if type_ == FaceType.ID_PICTURE:
                    img = Face.replacePictureColors(img, Face.ID_PICTURE_FG_COLOR, Face.ID_PICTURE_BG_COLOR)

                fixed = Face.cropHighest(img, Face.ORIGINAL_FG_COLOR, Face.ID_WANTED_CROP_AMT) 

        face = Face.TABLES[type_].get(md5(fixed.tobytes()).digest())

        if face is None:
            face = Face.TABLES[type_].get(md5(fixed.transpose(Image.FLIP_LEFT_RIGHT).tobytes()).digest())
        
        if heightPx is not None:
            if face is None: return None
            face.height = Face.getHeightFromY(heightPx, Face.HAIR_HEIGHT[face.sex][face.head])

        return face
    
    def __init__(self, sex: Sex, noseMouth: int, eyes: int, head: int, height: float | None = None):
        self.sex       = sex
        self.noseMouth = noseMouth
        self.head      = head
        self.eyes      = eyes
        self.height    = height

    @BaseDocument.field
    def descriptions(self) -> set[Description]:
        result = set()
        for piece in FacePiece:
            dict_ = Face.PARTS_DESCRIPTIONS[piece][self.sex]
            key   = getattr(self, piece.value)
            if key in dict_: result.add(dict_[key])

        return result

    def __ne__(self, other) -> bool:
        if type(other) is not Face:
            return True
        
        return self.sex != other.sex or self.noseMouth != other.noseMouth
    
    def __eq__(self, other) -> bool:
        if type(other) is not Face:
            return False
        
        return all((
            self.sex       == other.sex,
            self.noseMouth == other.noseMouth,
            self.eyes      == other.eyes,
            self.head      == other.head,
        ))
    
    def __repr__(self) -> str:
        output = f"Face({self.sex}, {self.descriptions}, n: {self.noseMouth}, e: {self.eyes}, h: {self.head}"
        if self.height is None: return output + ")"
        else:                   return output + f" ({self.height} cm))"
