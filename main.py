import os
import sys
import time
import json
import pathlib
import traceback
import subprocess
import tkinter as tk
from collections import deque
from threading   import Thread, Lock
from tkinter     import scrolledtext, messagebox
from typing      import Callable, ClassVar, NoReturn

from modules.sockets import *

VERSION = "2024.5.5-ALPHA"
SETTINGS_VERSION = "1"

MAIN_RESOLUTION     = "380x305"
SETTINGS_RESOLUTION = "200x100"
MAX_CONSOLE_LEN     = 131_072
GUI_FRAMERATE       = 20
FRAME_SLEEP         = 1 / GUI_FRAMERATE
GET_RUNS_ATTEMPTS   = 5

STDOUT_REDIRECT = True

PROGRAM_DIR = str(pathlib.Path(__file__).parent.absolute())
FROZEN = getattr(sys, 'frozen', False) and hasattr(sys, "_MEIPASS")
    
class GUI:
    SETTINGS_FILE: ClassVar[str] = os.path.join(PROGRAM_DIR, "config", "settings.json")

    ICON: ClassVar[tk.PhotoImage] = None
    
    def __setIcon(self, window: tk.Tk) -> None:
        self.window.call(
            "wm", "iconphoto", window._w,
            GUI.ICON
        )

    def __handleExc(self, e, val, tb) -> None:
        if self.__running: raise e
        
    def cleanup(self) -> None:
        self.__running = False
        self.window.destroy()
        if self.backend is not None:
            self.backend.kill()
    
    def __cleanup(self) -> NoReturn:
        self.cleanup()
        sys.exit(0)

    def __init__(self) -> None:
        self.__running = True

        tk.Tk.report_callback_exception = self.__handleExc
        self.window = tk.Tk()

        GUI.ICON = tk.PhotoImage(
            file = os.path.join(PROGRAM_DIR, "assets", "icon.png")
        )

        self.__setIcon(self.window)
        self.window.title("Papers Please TASbot")
        self.window.geometry(MAIN_RESOLUTION)
        self.window.resizable(False, False)
        self.window.protocol("WM_DELETE_WINDOW", self.__cleanup)

        self.settings = {
            "version": SETTINGS_VERSION,
            "debug": True
        }

        self.__buildWindow()
        self.window.after(0, self.__prepare)

    def consolePrint(self, msg: str) -> None:
        self.console.config(state = tk.NORMAL)
        self.console.insert(tk.END, "\n" + str(msg))

        if len(self.console.get("0.0", tk.END)) >= MAX_CONSOLE_LEN:
            self.console.delete("0.0", "1.0")

        self.console.see(tk.END)
        self.console.config(state = tk.DISABLED)
        self.window.update()

    def __ready(self) -> None:
        self.consolePrint('Ready.')
        self.runButton.config(state = tk.NORMAL)
        self.testButton.config(state = tk.NORMAL)
        self.settingsButton.config(state = tk.NORMAL)

    def __disable(self) -> None:
        self.runButton.config(state = tk.DISABLED)
        self.testButton.config(state = tk.DISABLED)
        self.settingsButton.config(state = tk.DISABLED)

    def updateConsole(self) -> None:
        with self.__queueLock:
            while len(self.__consoleQueue) != 0:
                self.consolePrint(self.__consoleQueue.popleft())
        self.window.update()

    def errorBox(self, title: str, message: str) -> None:
        if self.__running:
            messagebox.showerror(title, message)

    def __receive(self) -> tuple[BackendMessage, bytes | None] | None:
        waiting = True
        data: tuple[BackendMessage, bytes | None] = None
        exception: Exception | None               = None

        def receive():
            nonlocal waiting, data, exception
            try:    
                data = recvCom(self.__backendSock, BackendMessage)
            except Exception as e: 
                exception = e
            waiting = False

        t = Thread(target = receive)
        t.start()

        while waiting:
            self.updateConsole()
            time.sleep(FRAME_SLEEP)

        t.join()

        if data is None:
            self.errorBox(
                "Unable to receive data",
                (
                    "Backend connection closed abruptly" 
                    if exception is None else 
                    ''.join(traceback.format_exception(exception))
                )
            )
            return None
        
        com, args = data

        if com in (BackendMessage.EXCEPTION, BackendMessage.PANIC):
            panic = com == BackendMessage.PANIC
            self.errorBox(
                "Backend crashed!" if panic else "Exception from backend",
                args.decode()
            )

            if panic:
                self.initBackend()
                self.loadRuns()
        
        return data

    def backendCom(self, com: FrontendMessage, args: bytes | None = None) -> bytes | None:
        sendCom(self.__backendSock, com, args)
        data = self.__receive()
        if not data: return None
        return data[1]
    
    def __stdoutReader(self) -> None:
        while self.backend.poll() is None:
            line = self.backend.stdout.readline()

            if line and type(line) is bytes:
                try:
                    line = line.decode('utf-8')
                except UnicodeDecodeError: pass
                else:
                    with self.__queueLock:
                        self.__consoleQueue.append(line.strip())

    def initBackend(self) -> None:
        self.consolePrint('Initializing backend...')
        
        self.__sock.listen()

        self.backend = subprocess.Popen(
            (
                [sys.executable, "--backend"] if FROZEN else
                [sys.executable, os.path.join(PROGRAM_DIR, "backend.py")]
            ) + ["--frontend-port", str(self.__sock.getsockname()[1]), "--dir", encode(PROGRAM_DIR + os.sep)], 
            stdout = subprocess.PIPE if STDOUT_REDIRECT else None
        )

        self.__backendSock = self.__sock.accept()[0]

        self.__queueLock = Lock()
        if STDOUT_REDIRECT:
            self.__stdoutThread = Thread(target = self.__stdoutReader, daemon = True)
            self.__stdoutThread.start()

        self.backendCom(FrontendMessage.LOAD_SETTINGS)
        
    def loadRuns(self) -> None:
        self.consolePrint('Loading runs...')

        self.backendCom(FrontendMessage.RUNS, RunsCommand.LOAD.value.to_bytes())

        for _ in range(GET_RUNS_ATTEMPTS):
            data = self.backendCom(FrontendMessage.RUNS, RunsCommand.GET.value.to_bytes())
            if data is not None: break
        else:
            self.errorBox("Error", f"Unable to get runs from backend after {GET_RUNS_ATTEMPTS} attempts. Closing")
            self.__cleanup()

        self.runs = eval(data)

        self.runsList.delete(0, tk.END)
        for name, _ in self.runs:
            self.runsList.insert(tk.END, name)

    def __dictUpdateAndCleanup(self, new: dict, old: dict, version: str) -> dict:
        unused = []
        for key in new:
            if key not in old:
                unused.append(key)

        for key in unused:
            del new[key]

        for key in old:
            if key not in new:
                new[key] = old[key]

        new["version"] = version

        return new
    
    def writeSettings(self) -> None:
        try:
            with open(GUI.SETTINGS_FILE, "w", encoding = "utf-8") as settings:
                json.dump(self.settings, settings)
        except Exception:
            self.errorBox(
                "Unable to write settings", 
                "Unable to write settings. Error:\n" + traceback.format_exc()
            )

    def loadSettings(self) -> None:
        if os.path.exists(GUI.SETTINGS_FILE):
            try:
                with open(GUI.SETTINGS_FILE, "r", encoding = "utf-8") as settings:
                    tmpSettings = json.load(settings)

                if tmpSettings["version"] != SETTINGS_VERSION:
                    self.settings = self.__dictUpdateAndCleanup(tmpSettings, self.settings, SETTINGS_VERSION)
                    self.writeSettings()
                else:
                    self.settings = tmpSettings
            except Exception:
                self.errorBox(
                    "Unable to read settings", 
                    "Unable to read settings. Error:\n" + traceback.format_exc()
                )
        else:
            self.writeSettings()

    def __prepare(self) -> None:
        self.loadSettings()

        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__sock.bind(("localhost", 0))
        self.__consoleQueue = deque()

        self.initBackend()
        self.loadRuns()
        self.__ready()

    def updateDescription(self, description: str | None = None) -> None:
        if description is None:
            description = "Select a run"

        self.description.config(state = tk.NORMAL)

        self.description.delete("0.0", tk.END)
        self.description.insert(tk.END, description)

        self.description.see("0.0")
        self.description.config(state = tk.DISABLED)
        self.window.update()
    
    def __updateDescriptionOnSelect(self, event) -> None:
        runIdx = event.widget.curselection()
        if len(runIdx) == 0:
            self.updateDescription()
            return
        
        self.updateDescription(self.runs[runIdx[0]][1])

    def __buildWindow(self) -> None:
        self.leftFrame = tk.Frame(master = self.window)

        tk.Label(master = self.leftFrame, text = "Runs").pack()

        self.runsFrame = tk.Frame(master = self.leftFrame)

        self.scrollRuns = tk.Scrollbar(master = self.runsFrame, orient = tk.VERTICAL)
        self.scrollRuns.pack(side = tk.RIGHT, fill = tk.Y)

        self.runsList = tk.Listbox(master = self.runsFrame, yscrollcommand = self.scrollRuns.set, selectmode = tk.SINGLE)
        self.runsList.pack(side = tk.LEFT, fill = tk.BOTH)
        self.runsList.bind('<<ListboxSelect>>', self.__updateDescriptionOnSelect)

        self.scrollRuns.config(command = self.runsList.yview)

        self.runsFrame.pack(ipady = 20)

        self.runButton = tk.Button(master = self.leftFrame, text = "Run", state = tk.DISABLED, command = self.__selectedRunAct(RunMethod.RUN, "Running"))
        self.runButton.pack(fill = tk.X)

        self.testButton = tk.Button(master = self.leftFrame, text = "Test", state = tk.DISABLED, command = self.__selectedRunAct(RunMethod.TEST, "Testing"))
        self.testButton.pack(fill = tk.X)

        self.settingsButton = tk.Button(master = self.leftFrame, text = "Settings", state = tk.DISABLED, command = self.__settingsWindow)
        self.settingsButton.pack(fill = tk.X)

        self.rightFrame = tk.Frame(master = self.window)

        tk.Label(master = self.rightFrame, text = "Description").pack()

        self.description = scrolledtext.ScrolledText(master = self.rightFrame, state = tk.DISABLED, height = 5, width = 50, wrap = tk.WORD)
        self.description.pack(fill = tk.X, expand = True)
        self.updateDescription()

        tk.Label(master = self.rightFrame, text = "Console").pack()

        self.console = scrolledtext.ScrolledText(master = self.rightFrame, state = tk.DISABLED, height = 9, width = 50, wrap = tk.WORD)
        self.console.pack(fill = tk.X, expand = True)

        self.leftFrame.pack(side = tk.LEFT, fill = tk.Y, expand = True)
        self.rightFrame.pack(side = tk.RIGHT, fill = tk.Y, expand = True)

    def __centerWindow(self, window):
        self.window.update_idletasks()
        window.update_idletasks()
        posX, posY = (self.window.winfo_x() + self.window.winfo_width()  // 2 - window.winfo_width()  // 2, 
                      self.window.winfo_y() + self.window.winfo_height() // 2 - window.winfo_height() // 2)
        window.geometry(f"+{posX}+{posY}")

    def __settingsWindow(self):
        settingsWin = tk.Toplevel(master = self.window)
        self.__setIcon(settingsWin)
        settingsWin.grab_set()
        settingsWin.title("Settings")
        settingsWin.geometry(SETTINGS_RESOLUTION)
        self.__centerWindow(settingsWin)
        settingsWin.resizable(False, False)

        self.debugSet = tk.BooleanVar(value = self.settings["debug"])
        debugCheckbox = tk.Checkbutton(
            master = settingsWin, text = "Debug", 
            variable = self.debugSet
        )
        debugCheckbox.pack()

        def restartBackend():
            self.__disable()
            self.backendCom(FrontendMessage.EXIT)
            self.initBackend()
            self.loadRuns()
            self.__ready()

            messagebox.showinfo(title = "Done", message = "Backend was restarted.")

        restartBackendButton = tk.Button(master = settingsWin, text = "Restart backend", command = restartBackend)
        restartBackendButton.pack()

        buttonFrame = tk.Frame(master = settingsWin)

        def onSave():
            write = False

            if self.debugSet.get() != self.settings["debug"]:
                self.settings["debug"] = self.debugSet.get()
                write = True

            if write:
                self.consolePrint("Writing settings file...")
                self.writeSettings()
                self.backendCom(FrontendMessage.LOAD_SETTINGS)

            settingsWin.destroy()

        saveButton = tk.Button(master = buttonFrame, text = "Save", command = onSave)
        saveButton.pack(side = tk.RIGHT)

        tk.Label(master = buttonFrame, text = "v" + VERSION).pack(side = tk.LEFT)

        buttonFrame.pack(side = tk.BOTTOM, fill = tk.X)

    def run(self, runIdx: int, method: RunMethod) -> None:
        self.__disable()
        
        self.backendCom(FrontendMessage.SELECT, runIdx.to_bytes())
        self.backendCom(FrontendMessage.RUN, method.value.to_bytes())
        self.__receive() # waits for run to complete

        self.__ready()
    
    def __selectedRunAct(self, method: RunMethod, word: str) -> Callable[[], None]:
        def fn():
            runIdx = self.runsList.curselection()
            if len(runIdx) == 0:
                messagebox.showwarning(title = "No run selected", message = "Select a run first")
                return
            
            self.consolePrint(f"{word} {self.runsList.get(runIdx)}...")
            self.run(runIdx[0], method)

        return fn

if __name__ == "__main__":
    if FROZEN and "--backend" in sys.argv:
        import backend
    else:
        gui = None
        try:
            gui = GUI()
            tk.mainloop()
        except Exception as e:
            if gui is not None: gui.cleanup()
            raise e