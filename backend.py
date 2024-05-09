import json
import logging.config
import os
import sys
import time
import traceback
import platform

RUN_START_DELAY = 3

WINDOWS = platform.system() == "Windows"
if WINDOWS:
    import win32com.client
    import win32gui

FROZEN = getattr(sys, 'frozen', False) and hasattr(sys, "_MEIPASS")

logger = logging.getLogger('tas.' + __name__)

from modules.sockets import *

from modules.run import Run
# from tas         import TAS
from tas_experimental import NewTAS as TAS

class Backend:
    def __init__(self, port: int, directory: str):
        self.directory = directory

        with open(os.path.join(self.directory, 'config', 'logging_config.json'), 'r', encoding = 'utf-8') as f:
            config = json.load(f)
        logging.config.dictConfig(config)

        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__sock.connect(("localhost", port))

        self.currRun: int    = None
        self.runs: list[Run] = None

    def init(self):
        self.tas = TAS()

    if WINDOWS:
        def run(self, method: RunMethod) -> None:
            self.tas.currRun = self.runs[self.currRun]
            self.tas.hwnd    = self.tas.getWinHWND()

            self.tas.processEditor.init()
            win32com.client.Dispatch("WScript.Shell").SendKeys('%')
            win32gui.SetForegroundWindow(self.tas.hwnd)

            getattr(self.tas.currRun, 'run' if method == RunMethod.RUN else 'test')()
    else:
        def run(self, method: RunMethod) -> None:
            self.tas.currRun = self.runs[self.currRun]
            self.tas.winPos  = self.tas.getWinPos()
            
            self.tas.processEditor.init()
            getattr(self.tas.currRun, 'run' if method == RunMethod.RUN else 'test')()

    def select(self, idx: int) -> None:
        self.currRun = idx

    def loadSettings(self) -> None:
        with open(os.path.join(self.directory, "config", "settings.json"), "r", encoding = "utf-8") as settings:
            self.tas.SETTINGS = json.load(settings)

    def runsCommand(self, com: RunsCommand) -> None:
        match com:
            case RunsCommand.LOAD:
                self.runs = []
                # import all runs
                for module in os.listdir(os.path.join(self.directory, "runs")):
                    if module.endswith(".py"):
                        __import__(f"runs.{module[:-3]}", locals(), globals())

                for RunSubclass in Run.__subclasses__():
                    logger.info(f'Initializing Run "{RunSubclass.__name__}"...')
                    inst = RunSubclass()
                    inst.tas = self.tas
                    self.runs.append(inst)
                    
                self.ok()
            case RunsCommand.GET:
                sendCom(
                    self.__sock, BackendMessage.DATA, 
                    str([(run.__class__.__name__, run.description()) for run in self.runs]).encode()
                )

    def ok(self) -> None:
        sendCom(self.__sock, BackendMessage.OK)

    def __main(self) -> None:
        while True:
            data = recvCom(self.__sock, FrontendMessage)
            if not data: break
            com, args = data

            match com:
                case FrontendMessage.EXIT:
                    self.ok()
                    self.__sock.close()
                    sys.exit(0)
                case FrontendMessage.SELECT:
                    self.select(int.from_bytes(args))
                    self.ok()
                case FrontendMessage.RUN:
                    self.ok()
                    time.sleep(RUN_START_DELAY)
                    self.run(RunMethod(int.from_bytes(args)))
                    self.ok()
                case FrontendMessage.LOAD_SETTINGS:
                    self.loadSettings()
                    self.ok()
                case FrontendMessage.RUNS:
                    runsCom = RunsCommand(int.from_bytes(args))
                    self.runsCommand(runsCom)                        
                case _:
                    sendCom(self.__sock, BackendMessage.EXCEPTION, f'Unknown command "{com}"'.encode())

    def main(self) -> None:
        try:
            self.init()
            self.__main()
        except Exception:
            sendCom(self.__sock, BackendMessage.PANIC, traceback.format_exc().encode())

def main() -> None:
    portIdx = sys.argv.index("--frontend-port")
    sys.argv.pop(portIdx)
    port = int(sys.argv.pop(portIdx))
    
    directoryIdx = sys.argv.index("--dir")
    sys.argv.pop(directoryIdx)
    directory = decode(sys.argv.pop(directoryIdx))

    Backend(port, directory).main()

if FROZEN or __name__ == "__main__": main()