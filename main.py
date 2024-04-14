import json
import logging.config
import os
import pathlib

import win32com.client
import win32gui

from tas import TAS
from run import Run

logger = logging.getLogger('tas.' + __name__)
log_config_path = os.path.join(TAS.PROGRAM_DIR, 'config', 'logging_config.json')
with open(log_config_path) as f:
    config = json.load(f)
logging.config.dictConfig(config)

tas = TAS()

# import all runs
for module in os.listdir(pathlib.Path('./runs')):
    if module.endswith(".py"):
        __import__(f"runs.{module[:-3]}", locals(), globals())

RUNS: list[Run] = []
for RunSubclass in Run.__subclasses__():
    logger.info(f'Initializing Run "{RunSubclass.__name__}"...')
    inst = RunSubclass()
    inst.tas = tas
    RUNS.append(inst)


def select(msg: str, options: list) -> int:
    while True:
        print(msg)
        for i, opt in enumerate(options):
            print(f"{i + 1}) {opt}")

        res = input()
        try:
            _ = int(res)
        except ValueError:
            pass
        else:
            res = int(res) - 1
            if 0 <= res < len(options):
                return res

        print("Invalid input.")


def main():
    while True:
        i = select("Select run:", [run.__class__.__name__ for run in RUNS])
        act = select("Select action:", ["Run", "Test", "View credits"])

        if act in (0, 1):
            tas.currRun = RUNS[i]
            tas.hwnd    = tas.getWinHWND()
            shell = win32com.client.Dispatch("WScript.Shell")
            shell.SendKeys('%')
            win32gui.SetForegroundWindow(tas.hwnd)

        match act:
            case 0:
                RUNS[i].run()
            case 1:
                RUNS[i].test()
            case 2:
                print(RUNS[i].credits())

if __name__ == '__main__': main()