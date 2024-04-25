from typing import TYPE_CHECKING

from modules.documents.document import Document
from modules.documents.passport import Passport
from modules.constants.screen   import *
from modules.constants.other    import TASException

if TYPE_CHECKING:
    from tas import TAS

class DocumentStack:
    def __init__(self, tas: "TAS"):
        self.passport = None
        self.moved    = False
        self.__array  = []
        self.__map    = {}
        self.__ptr    = 0
        self.__tas    = tas

    def reset(self):
        self.__array.clear()
        self.__map.clear()
        self.passport = None
        self.moved    = False
        self.__ptr    = 0
        
    def push(self, document: Document | Passport):
        if type(document) is Passport:
            self.passport = document
            self.moved    = True
            self.__tas.dragTo(SLOTS[0])
        else:
            self.__map[type(document)] = len(self.__array)
            self.__array.append(document)
            
            self.__ptr += 1
            if self.__ptr == len(SLOTS):
                raise TASException("No more slots left")

            self.__tas.dragTo(SLOTS[self.__ptr])

    def pop(self) -> Document | None:
        if len(self.__array) != 0:
            self.__tas.moveTo(SLOTS[self.__ptr])
            self.__ptr -= 1
            self.__tas.dragTo(PERSON_POS)
            
            doc = self.__array.pop()
            del self.__map[type(doc)]
            return doc
        return None
    
    def get(self, type_) -> Document | None:
        if type_ in self.__map:
            return self.__array[self.__map[type_]]
        return None
    
    def getSlot(self, type_) -> int | None:
        if type_ in self.__map:
            return self.__map[type_] + 1
        return None
    
    def mulDocs(self) -> bool:
        return len(self.__array) != 0
            
    def __len__(self) -> int:
        return len(self.__array)