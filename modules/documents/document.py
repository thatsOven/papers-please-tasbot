from abc    import ABC
from PIL    import Image
from typing import Self, Type, ClassVar, Callable, TypeVar, Generic, TYPE_CHECKING
import numpy as np, pyautogui as pg

from modules.utils import bgFilter, offsetBox

if TYPE_CHECKING:
    from tas import TAS

T = TypeVar("T")
class TypedGetterProperty(property, Generic[T]):
    def __get__(self, instance, owner: Type | None = None) -> T:
        return super().__get__(instance, owner)

class BaseDocument(ABC):
    TAS: ClassVar[Type["TAS"]] = None # again, circular imports (ugh)

    LAYOUT: dict[str, tuple[int, int, int, int]] = None

    @staticmethod
    def load(): 
        raise NotImplementedError
    
    @staticmethod
    def checkMatch(docImg: Image.Image) -> bool: 
        raise NotImplementedError
    
    @staticmethod
    def getBgs(layout: dict[str, tuple[int, int, int, int]], innerTexture: Image.Image) -> dict[str, Image.Image]:
        return {key: innerTexture.crop(box) for key, box in layout.items()}
    
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
    def field(fn: Callable[[Self], T]) -> TypedGetterProperty[T]:
        @TypedGetterProperty
        def wrapper(self):
            fieldName = "_cached__" + fn.__name__
            
            if hasattr(self, fieldName):
                val = getattr(self, fieldName)
            else:
                val = fn(self)
                setattr(self, fieldName, val)
            return val
        return wrapper
    
    def __init__(self, docImg: Image.Image, tableOffs: tuple[int, int]):
        self.docImg      = docImg
        self.__tableOffs = tableOffs

    def getTableBox(self, field: str):
        if self.LAYOUT is None and hasattr(self, "type_") and hasattr(getattr(self, "type_"), "layout"): # for passport class
            return offsetBox(getattr(self.type_.layout, field), self.__tableOffs)
        else:
            return offsetBox(self.LAYOUT[field], self.__tableOffs)            

class Document(BaseDocument): ...