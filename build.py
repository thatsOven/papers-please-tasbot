import os
import sys
import numpy
import shutil
import pathlib

from setuptools      import setup
from Cython.Build    import cythonize
from Cython.Compiler import Options

DEPENDENCIES = [
    "win32com",
    "win32gui",
    "PIL",
    "numpy",
    "deskew",
    "skimage",
    "pyautogui",
    "cv2",
    "dateutil",
    "pythoncom",
    "pywintypes",
    "win32api",
    "winerror",
    "tas",
    "modules",
    "packaging",
    "lazy_loader",
    "scipy",
    "six",
    "pyscreeze"
]

COLLECT_ALL = [
    "skimage"
]

def build():
    Options.annotate = False

    oldArgs = sys.argv
    sys.argv = [sys.argv[0], "build_ext", "--inplace"]

    file = os.path.abspath(str(pathlib.Path('./modules/textRecognition/source/textRecognition.pyx')))
    os.chdir(str(pathlib.Path('./modules/textRecognition')))
    setup(
        name         = "textRecognition",
        include_dirs = [numpy.get_include()], 
        ext_modules  = cythonize(file, compiler_directives = {
            "language_level": "3"
        }),
        zip_safe = False
    )

    sys.argv = oldArgs
    
    file = str(pathlib.Path('./source/textRecognition.c'))
    if os.path.exists(file): os.remove(file)

    fold = str(pathlib.Path('./build'))
    if os.path.exists(fold): shutil.rmtree(fold)

def release():
    os.chdir(str(pathlib.Path(__file__).parent.absolute()))

    from ianthe import Ianthe
    ianthe = Ianthe()
    ianthe.config = {
        "source":       "main.py",
        "destination":  "PapersPleaseTAS",
        "display-mode": "console",
        "icon":         os.path.join("assets", "icon.ico"),
        "copy": {
            "runs":   "folder",
            "assets": "folder",
            "config": "folder"
        },
        "scan": False,
        "keep": DEPENDENCIES,
        "collect": {
            "all": COLLECT_ALL
        }
    }

    ianthe.execute()

if __name__ == "__main__":
    build()
    
    if "--release" in sys.argv:
        release()