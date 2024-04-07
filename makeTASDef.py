# should be ran (or modified, in some cases) by developers when making changes to the TAS class in tas.py
# it's used for better syntax highlighting

import inspect, os

TAB = "    "

ADD_VARS = [
    "date: datetime.date"
]

STATIC_METHODS = {
    "select"
}

BASE_CODE = """
from typing import Callable
import pyautogui
import datetime
import typing
import numpy
import PIL

import modules

class TASDef:
""".lstrip()

if __name__ == "__main__":
    os.environ["MAKING_DEF"] = ""
    from tas import TAS

    result = BASE_CODE

    vars = set()
    for var in TAS.__annotations__:
        vars.add(var)
        result += TAB + var + ": "

        hint = TAS.__annotations__[var]
        if type(hint) is type:
            result += hint.__name__
        else:
            result += str(hint)
        result += "\n"

    for var in ADD_VARS:
        vars.add(var)
        result += TAB + var + "\n"
    
    result += "\n"

    for item in dir(TAS):
        if not item.startswith("__"):
            obj = getattr(TAS, item)

            if inspect.isfunction(obj):
                vars.add(item)
                if item in STATIC_METHODS: result += TAB + "@staticmethod\n"
                result += TAB + f"def {item}{str(inspect.signature(obj))}: ...\n"
            elif inspect.ismethod(obj):
                vars.add(item)
                result += TAB + "@classmethod\n" + TAB + f"def {item}{str(inspect.signature(obj))}: ...\n"

    with open(os.path.join(TAS.PROGRAM_DIR, "modules", "tasdef.py"), "w") as f:
        f.write(result)