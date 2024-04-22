from enum import Enum

PORT_BYTES     = 2
SIZE_COM_BYTES = 4
MESSAGE_BYTES  = 1

class FrontendMessage(Enum):
    LOAD_SETTINGS, EXIT, RUNS, SELECT, RUN = range(5)

class RunsCommand(Enum):
    LOAD, GET = range(2)

class RunMethod(Enum):
    RUN, TEST = range(2)

FRONTEND_COM_ARG_SIZES = {
    FrontendMessage.RUNS: 1,
    FrontendMessage.SELECT: 1,
    FrontendMessage.RUN: 1
}

class BackendMessage(Enum):
    OK, DATA, EXCEPTION, PANIC = range(4)

BACKEND_COM_ARG_SIZES = {
    BackendMessage.DATA: None,
    BackendMessage.EXCEPTION: None,
    BackendMessage.PANIC: None
}