import socket
import base64
from typing import Type

from modules.constants.sockets import *

def sendDynamic(sock: socket.socket, data: bytes) -> None:
    sock.send(len(data).to_bytes(SIZE_COM_BYTES))
    sock.send(data)

def recvDynamic(sock: socket.socket) -> bytes | None:
    size = sock.recv(SIZE_COM_BYTES)
    if not size: return None
    return sock.recv(int.from_bytes(size))

def getArgsSize(command: FrontendMessage | BackendMessage) -> int | None:
    if type(command) is FrontendMessage:
        if command not in FRONTEND_COM_ARG_SIZES: return -1
        return FRONTEND_COM_ARG_SIZES[command]
    elif type(command) is BackendMessage:
        if command not in BACKEND_COM_ARG_SIZES: return -1
        return BACKEND_COM_ARG_SIZES[command]
    return -1

def sendCom(sock: socket.socket, command: FrontendMessage | BackendMessage, args: bytes | None = None) -> None:
    sock.send(command.value.to_bytes())

    if args is None: return
    size = getArgsSize(command)
    if size == -1: return

    if size is None:
          sendDynamic(sock, args)
    else: sock.send(args)

def recvCom(sock: socket.socket, type_: Type[FrontendMessage | BackendMessage]) -> tuple[FrontendMessage | BackendMessage, bytes | None] | None:
    command = sock.recv(MESSAGE_BYTES)
    if not command: return None
    command = type_(int.from_bytes(command))

    size = getArgsSize(command)
    if size == -1: return command, None

    if size is None:
          args = recvDynamic(sock)
    else: args = sock.recv(size)

    if not args: return None
    return command, args

# they have nothing to do with sockets, but whatever
def encode(msg: str) -> str:
    return base64.b64encode(msg.encode()).decode()

def decode(msg: str) -> str:
    return base64.b64decode(msg.encode()).decode()