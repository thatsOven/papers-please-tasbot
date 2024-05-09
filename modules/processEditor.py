import pymem
import pymem.memory
import pymem.process
from peachpy import *
from peachpy.x86_64 import *
from peachpy.x86_64.instructions import Instruction
from typing import Iterable, Any

from modules.constants.other import *

FACE_SET_FLIP = bytearray((
    0x0F, 0x97, 0xC0, # seta al
    0x88, 0x47, 0x28  # mov byte ptr [rdi + 0x28], al
))

FACE_CHANGE_COMMON = bytearray((
    0x48, 0x8B, 0xC7,       # mov rax, rdi
    0x48, 0x83, 0xC4, 0x20, # add rsp, 20
    0x5F,                   # pop rdi
    0xC3                    # ret
))

MEM_EDITS: dict[str, dict[Any, dict[str, tuple[Instruction, ...] | bytearray]]] = {
    "sexForced": {
        True: {
            "self.gameAssemblyDLL + 0x968A9B": tuple(NOP() for _ in range(2)),
            "self.gameAssemblyDLL + 0x968AEC": tuple(NOP() for _ in range(5))
        },
        False: {
            "self.gameAssemblyDLL + 0x968A9B": bytearray((0x74, 0x54)),
            "self.gameAssemblyDLL + 0x968AEC": bytearray((0xE9, 0x91, 0, 0, 0))
        }
    },
    "sex": {
        None: {
            "self.gameAssemblyDLL + 0x968B3C": bytearray((0x76, 0x22))
        },
        Sex.F: {
            "self.gameAssemblyDLL + 0x968B3C": bytearray((0xEB, 0x22))
        },
        Sex.M: {
            "self.gameAssemblyDLL + 0x968B3C": tuple(NOP() for _ in range(2))
        }
    },
    "faceChange": {
        False: {
            "self.gameAssemblyDLL + 0x993857": FACE_SET_FLIP + FACE_CHANGE_COMMON
        }
    }
}

def encodeAll(instructions: Iterable[Instruction]) -> bytearray:
    output = bytearray()
    for instruction in instructions:
        output += instruction.encode()
    return output

def getFaceCode(
    head: int | None = None, eyes: int | None = None, 
    noseMouth: int | None = None, shoulders: int | None = None, 
    palette: int | None = None, flipped: bool | None = None
) -> bytearray:
    if flipped is None:
        topCode = FACE_SET_FLIP
    else:
        topCode = bytearray()
    
    code = []

    if head is not None:
        code += [
            MOV(edx, head),
            MOV([rdi + 0x18], edx)
        ]

    if eyes is not None:
        code += [
            MOV(edx, eyes),
            MOV([rdi + 0x1C], edx)
        ]

    if noseMouth is not None:
        code += [
            MOV(edx, noseMouth),
            MOV([rdi + 0x20], edx)
        ]

    if shoulders is not None:
        code += [
            MOV(edx, shoulders),
            MOV([rdi + 0x14], edx)
        ]

    if palette is not None:
        code += [
            MOV(edx, palette),
            MOV([rdi + 0x24], edx)
        ]

    if flipped is not None:
        code += [
            MOV(edx, int(flipped)),
            MOV([rdi + 0x28], edx)
        ]

    code.append(POP(rdx))
    return topCode + encodeAll(code) + FACE_CHANGE_COMMON

class ProcessEditor:
    def __init__(self):
        self.process         = None
        self.gameAssemblyDLL = None
        self.faceSetCodePtr  = None

    def init(self) -> None:
        self.process = pymem.Pymem(PROCESS_NAME)
        self.gameAssemblyDLL = pymem.process.module_from_name(self.process.process_handle, "GameAssembly.dll").lpBaseOfDll

    def alloc(self, size: int) -> int:
        return pymem.memory.allocate_memory(self.process.process_handle, size)
    
    def getAddr(self, expr: str) -> int:
        return eval(expr)
    
    def doMemEdit(self, edit: str, setting: Any) -> None:
        for key, data in MEM_EDITS[edit][setting].items():
            if type(data) is tuple:
                data = bytes(encodeAll(data))
            else:
                data = bytes(data)

            self.process.write_bytes(self.getAddr(key), data, len(data))

    def resetFace(self) -> None:
        self.doMemEdit("faceChange", False)
        self.process.free(self.faceSetCodePtr)
        self.faceSetCodePtr = None

    def setFace(
        self, head: int | None = None, eyes: int | None = None, 
        noseMouth: int | None = None, shoulders: int | None = None, 
        palette: int | None = None, flipped: bool | None = None
    ) -> None:
        code = bytes(getFaceCode(head, eyes, noseMouth, shoulders, palette, flipped))
        self.faceSetCodePtr = self.alloc(len(code))
        self.process.write_bytes(self.faceSetCodePtr, code, len(code))

        jump = bytes(encodeAll((
            PUSH(rdx),
            MOV(rdx, self.faceSetCodePtr),
            JMP(rdx)
        )))

        key = list(MEM_EDITS["faceChange"][False].keys())[0]
        self.process.write_bytes(self.getAddr(key), jump, len(jump))

    def setSex(self, sex: Sex) -> None:
        self.doMemEdit("sexForced", True)
        self.doMemEdit("sex", sex)

    def resetSex(self) -> None:
        self.doMemEdit("sexForced", False)
        self.doMemEdit("sex", None)