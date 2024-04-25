from abc    import ABC
from PIL    import Image
from typing import Self, Type, ClassVar, Callable, Any, TYPE_CHECKING
import numpy as np, pyautogui as pg

from modules.utils import bgFilter

def convertBox(box: tuple[int, int, int, int], offset: tuple[int, int]):
    return (
        box[0] - offset[0], 
        box[1] - offset[1], 
        box[2] - offset[0], 
        box[3] - offset[1]
    )

def getBox(x0, y0, x1, y2):
    return (x0, y0, x1 + 1, y2 + 1)

if TYPE_CHECKING:
    from tas import TAS

class BaseDocument(ABC):
    TAS: ClassVar[Type["TAS"]] = None # again, circular imports (ugh)

    @staticmethod
    def load(): 
        raise NotImplementedError
    
    @staticmethod
    def checkMatch(docImg: Image.Image) -> bool: 
        raise NotImplementedError
    
    @staticmethod
    def getBgs(layout: dict[str, tuple], tableOffset: tuple[int, int], innerTexture: Image.Image) -> dict[str, Image.Image]:
        return {key: innerTexture.crop(convertBox(box, tableOffset)) for key, box in layout.items()}
    
    @staticmethod
    def __sealFilter(sealArea: np.ndarray, background: Image.Image, whiteBg: Image.Image) -> np.ndarray:
        diff = bgFilter(np.asarray(background), sealArea)
    
        if whiteBg is None:
            whiteBg = background.copy()
            whiteBg.paste((255, 255, 255), (0, 0) + whiteBg.size)

        np.copyto(diff, whiteBg, where = diff != 0)
        return diff
    
    @staticmethod
    def checkNoSeal(sealArea: np.ndarray, background: Image.Image, seal: Image.Image, whiteBg: Image.Image | None = None) -> bool:
        return pg.locate(seal, Image.fromarray(BaseDocument.__sealFilter(sealArea, background, whiteBg))) is None
    
    @staticmethod
    def sealPos(sealArea: np.ndarray, background: Image.Image, whiteBg: Image.Image | None = None) -> tuple[int, int]:
        ys, xs, _ = BaseDocument.__sealFilter(sealArea, background, whiteBg).nonzero()
        return (xs[0], ys[0])
    
    @staticmethod
    def field(fn: Callable[[Self], Any]) -> Callable[[Self], Any]:
        @property
        def wrapper(self):
            fieldName = "_cached__" + fn.__name__
            try:
                val = getattr(self, fieldName)
            except AttributeError:
                val = fn(self)
                setattr(self, fieldName, val)
            return val
        return wrapper
    
    def __init__(self, docImg: Image.Image):
        self.docImg = docImg

class Document(BaseDocument): ...