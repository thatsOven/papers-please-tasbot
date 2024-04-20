import json
import logging.config
import os
import sys
import traceback
import base64

import win32com.client
import win32gui

FROZEN = getattr(sys, 'frozen', False) and hasattr(sys, "_MEIPASS")

logger = logging.getLogger('tas.' + __name__)

from modules.run import Run
from tas         import TAS

def eprint(*args, **kwargs) -> None:
    print(*args, file = sys.stderr, **kwargs)

def encode(msg: str) -> str:
    return base64.b64encode(msg.encode()).decode()

def decode(msg: str) -> str:
    return base64.b64decode(msg.encode()).decode()

def main() -> None:
    directory: str  = None
    runs: list[Run] = None
    curr: int       = None
    tas: TAS        = None
    
    while True:
        try:
            com = input().split()
        except EOFError: continue
        
        match com[0]:
            case "exit":
                sys.exit(0)
            case "select":
                curr = int(com[1])
            case "run":
                eprint("ok")
                tas.currRun = runs[curr]
                tas.hwnd    = tas.getWinHWND()
                win32com.client.Dispatch("WScript.Shell").SendKeys('%')
                win32gui.SetForegroundWindow(tas.hwnd)
                getattr(runs[curr], com[1])()
            case "set_dir":
                directory = decode(com[1])

                with open(os.path.join(directory, 'config', 'logging_config.json'), 'r', encoding = 'utf-8') as f:
                    config = json.load(f)
                logging.config.dictConfig(config)
            case "init":
                tas = TAS()
            case "load_settings":
                with open(os.path.join(directory, "config", "settings.json"), "r", encoding = "utf-8") as settings:
                    tas.SETTINGS = json.load(settings)
            case "runs":
                match com[1]:
                    case "load":
                        runs = []
                        # import all runs
                        for module in os.listdir(os.path.join(directory, "runs")):
                            if module.endswith(".py"):
                                __import__(f"runs.{module[:-3]}", locals(), globals())

                        for RunSubclass in Run.__subclasses__():
                            logger.info(f'Initializing Run "{RunSubclass.__name__}"...')
                            inst = RunSubclass()
                            inst.tas = tas
                            runs.append(inst)
                    case "get":
                        runsData = [(run.__class__.__name__, run.description()) for run in runs]
                        eprint("data")
                        eprint(encode(str(runsData)))
                    case _:
                        eprint("exc " + encode('Unknown runs command'))
                        continue
            case _:
                eprint("exc " + encode('Unknown command'))
                continue

        eprint("ok")

if FROZEN or __name__ == "__main__":
    try:
        main()
    except Exception:
        eprint("panic " + encode(traceback.format_exc()))
        while True: pass # wait for frontend to read buffers and close backend