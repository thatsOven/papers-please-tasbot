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

def sendCom(sock: socket.socket, command: FrontendMessage | BackendMessage, args: bytes | None = None) -> None:
    sock.send(command.value.to_bytes())

    if args is None:
        return
    
    if type(command) is FrontendMessage:
        if command in FRONTEND_COM_ARG_SIZES:
            size = FRONTEND_COM_ARG_SIZES[command]
        else: return
    elif type(command) is BackendMessage:
        if command in BACKEND_COM_ARG_SIZES:
            size = BACKEND_COM_ARG_SIZES[command]
        else: return

    if size is None:
          sendDynamic(sock, args)
    else: sock.send(args)

def recvCom(sock: socket.socket, type_: Type[FrontendMessage | BackendMessage]) -> tuple[FrontendMessage | BackendMessage, bytes | None] | None:
    command = sock.recv(MESSAGE_BYTES)
    if not command: return None
    command = type_(int.from_bytes(command))

    if type_ is FrontendMessage:
        if command in FRONTEND_COM_ARG_SIZES:
            size = FRONTEND_COM_ARG_SIZES[command]
        else: return command, None
    elif type_ is BackendMessage:
        if command in BACKEND_COM_ARG_SIZES:
            size = BACKEND_COM_ARG_SIZES[command]
        else: return command, None

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