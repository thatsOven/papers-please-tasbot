from abc import ABC, abstractmethod
from typing import Type, ClassVar
import os

if "MAKING_DEF" not in os.environ:
    from modules.tasdef import TASDef

class Run(ABC):
    if "MAKING_DEF" not in os.environ:
        TAS: ClassVar[Type[TASDef]] = None
        tas: TASDef
    
    @abstractmethod
    def run(self):
        ...

    def credits(self):
        return "No credits"

    def test(self):
        ...