import os
import sys
import time
import json
import base64
import pathlib
import subprocess
import tkinter as tk
from threading import Thread
from queue     import Queue
from tkinter   import scrolledtext, messagebox
from typing    import Literal, Callable, ClassVar, NoReturn

VERSION = "2024.4.20"
SETTINGS_VERSION = "1"

MAIN_RESOLUTION     = "380x305"
SETTINGS_RESOLUTION = "200x100"
MAX_CONSOLE_LEN     = 131_072
GET_RUNS_ATTEMPTS   = 5

PROGRAM_DIR = str(pathlib.Path(__file__).parent.absolute())
FROZEN = getattr(sys, 'frozen', False) and hasattr(sys, "_MEIPASS")

def encode(msg: str) -> str:
    return base64.b64encode(msg.encode()).decode()

def decode(msg: str) -> str:
    return base64.b64decode(msg.encode()).decode()

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
        
    def cleanup(self) -> NoReturn:
        self.__running = False
        self.window.destroy()
        if self.backend is not None:
            self.backend.kill()
        quit()

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
        self.window.protocol("WM_DELETE_WINDOW", self.cleanup)

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

    def __wait(self, cond: Callable[[str], bool]) -> str | None:
        q = Queue()
        waiting = True

        def fn():
            nonlocal waiting

            def stdout():
                while waiting:
                    line = self.backend.stdout.readline()

                    if line and type(line) is bytes:
                        try:
                            line = line.decode('utf-8')
                        except UnicodeDecodeError: pass
                        else:
                            q.put(("stdout", line.strip()))

            t = Thread(target = stdout)
            t.start()

            while self.backend.poll() is None:
                line = self.backend.stderr.readline()

                if line and type(line) is bytes:
                    try:
                        line = line.decode('utf-8')
                    except UnicodeDecodeError: pass
                    else:
                        stripped = line.strip()
                        splitted = stripped.split()

                        panic = splitted[0] == "panic"
                        if panic or splitted[0] == "exc":
                            if panic:
                                title = "Backend crashed!"

                                q.put(("exec", "killBackend"))
                                q.put(("exec", "initBackend"))
                                q.put(("exec", "loadRuns"))
                            else:
                                title = "Exception from backend"

                            q.put(("popup", {
                                "title": title,
                                "type": "error",
                                "body": decode(splitted[1])
                            }))

                            q.put(("ret", None))
                            break

                        if cond(stripped): 
                            q.put(("ret", stripped))
                            break
                                
            waiting = False
            t.join()

        t = Thread(target = fn)
        t.start()

        while waiting:
            time.sleep(0.1)
            while not q.empty():
                com = q.get()

                match com[0]:
                    case "stdout":
                        self.consolePrint(com[1])
                    case "exec":
                        getattr(self, com[1])()
                    case "popup":
                        settings = com[1]
                        match settings["type"]:
                            case "error":
                                messagebox.showerror(settings["title"], settings["body"])
                            case "warn":
                                messagebox.showwarning(settings["title"], settings["body"])
                            case "info":
                                messagebox.showinfo(settings["title"], settings["body"])
                    case "ret":
                        return com[1]
                    
                self.window.update()
            self.window.update()

        t.join()

    def killBackend(self) -> None:
        if self.backend.poll() is not None:
            self.backend.kill()

    def backendCom(self, com: str) -> None:
        self.backend.stdin.write((com + '\n').encode())
        self.backend.stdin.flush()
        self.__wait(lambda x: x == "ok")

    def backendDataCom(self, com: str) -> str:
        self.backend.stdin.write((com + '\n').encode())
        self.backend.stdin.flush()
        self.__wait(lambda x: x == "data")
        data = self.__wait(lambda _: True)
        if data is None: return None

        self.__wait(lambda x: x == "ok")
        return decode(data)

    def initBackend(self) -> None:
        self.consolePrint('Initializing backend...')

        self.backend = subprocess.Popen(
            [sys.executable, "--backend"] if FROZEN else
            [sys.executable, os.path.join(PROGRAM_DIR, "backend.py")], 
            stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE,
            creationflags = subprocess.CREATE_NO_WINDOW
        )
        self.backendCom(f"set_dir {encode(PROGRAM_DIR + os.sep)}")
        self.backendCom("init")
        self.backendCom("load_settings")
        
    def loadRuns(self) -> None:
        self.consolePrint('Loading runs...')

        self.backendCom("runs load")

        for _ in range(GET_RUNS_ATTEMPTS):
            data = self.backendDataCom("runs get")
            if data is not None: break
        else:
            messagebox.showerror("Error", f"Unable to get runs from backend after {GET_RUNS_ATTEMPTS} attempts. Closing")
            self.cleanup()

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
        with open(GUI.SETTINGS_FILE, "w", encoding = "utf-8") as settings:
            json.dump(self.settings, settings)

    def loadSettings(self) -> None:
        if os.path.exists(GUI.SETTINGS_FILE):
            with open(GUI.SETTINGS_FILE, "r", encoding = "utf-8") as settings:
                tmpSettings = json.load(settings)

            if tmpSettings["version"] != SETTINGS_VERSION:
                self.settings = self.__dictUpdateAndCleanup(tmpSettings, self.settings, SETTINGS_VERSION)
                self.writeSettings()
            else:
                self.settings = tmpSettings
        else:
            self.writeSettings()

    def __prepare(self) -> None:
        self.loadSettings()
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

        self.runButton = tk.Button(master = self.leftFrame, text = "Run", state = tk.DISABLED, command = self.__selectedRunAct('run'))
        self.runButton.pack(fill = tk.X)

        self.testButton = tk.Button(master = self.leftFrame, text = "Test", state = tk.DISABLED, command = self.__selectedRunAct('test'))
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
            self.backendCom("exit")
            self.initBackend()
            self.loadRuns()

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
                self.backendCom("load_settings")

            settingsWin.destroy()

        saveButton = tk.Button(master = buttonFrame, text = "Save", command = onSave)
        saveButton.pack(side = tk.RIGHT)

        tk.Label(master = buttonFrame, text = "v" + VERSION).pack(side = tk.LEFT)

        buttonFrame.pack(side = tk.BOTTOM, fill = tk.X)

    def run(self, runIdx: int, method: Literal['run', 'test']) -> None:
        self.__disable()
        
        self.backendCom(f"select {runIdx}")
        self.backendCom(f"run {method}")
        self.__wait(lambda x: x == "ok")

        self.__ready()
    
    def __selectedRunAct(self, method: Literal['run', 'test']) -> Callable[[], None]:
        def fn():
            runIdx = self.runsList.curselection()
            if len(runIdx) == 0:
                messagebox.showwarning(title = "No run selected", message = "Select a run first")
                return
            
            self.run(runIdx[0], method)

        return fn

if __name__ == "__main__":
    if "--backend" in sys.argv:
        import backend
    else:
        try:
            gui = GUI()
            tk.mainloop()
        except Exception:
            gui.cleanup()
