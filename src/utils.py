import inspect as _inspect
import logging as _logging
import os as _os
import sys as _sys
from copy import copy as _copy
from typing import Literal as _Literal
from typing import Optional as _Optional


def p(arg=None):
    root = _os.path.abspath(_os.curdir)
    frame = _inspect.currentframe()

    if not frame or not frame.f_back:
        return None

    frame = frame.f_back
    info = _inspect.getframeinfo(frame)
    lineno = info.lineno
    file = info.filename.removeprefix(root + "/")

    if arg is not None and info.code_context:
        context = info.code_context[0].strip()
        brack_index = context.find("(") + 1
        context = context[brack_index:-1]

        print(f"{file}:{lineno} -> {context} = {arg}")
        return arg

    print(f"{file}:{lineno}")
    return None


def create_logger(name: str, with_file=False) -> _logging.Logger:
    logger = _logging.getLogger(name)
    logger.setLevel(_logging.INFO)
    stream_handler = _logging.StreamHandler(_sys.stdout)
    stream_handler.setFormatter(
        _ColourizedFormatter(
            "%(asctime)s %(levelprefix)s [%(name)s] %(module)s:%(funcName)s:%(lineno)d - %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(stream_handler)
    if with_file:
        file_handler = _logging.FileHandler(f"{name}.log")
        file_handler.setFormatter(
            _logging.Formatter(
                "%(asctime)s %(levelname)s [%(name)s] %(module)s:%(funcName)s:%(lineno)d - %(message)s",
                "%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(file_handler)

    return logger


def _colorize(message: str, color: str) -> str:
    if color == "red":
        return "\033[91m" + message + "\033[0m"

    if color == "green":
        return "\033[92m" + message + "\033[0m"

    if color == "yellow":
        return "\033[93m" + message + "\033[0m"

    if color == "blue":
        return "\033[94m" + message + "\033[0m"

    if color == "cyan":
        return "\033[96m" + message + "\033[0m"

    if color == "bright_red":
        return "\033[31;1m" + message + "\033[0m"

    return message


class _ColourizedFormatter(_logging.Formatter):
    """
    A custom log formatter class that:

    * Outputs the LOG_LEVEL with an appropriate color.
    * If a log call includes an `extras={"color_message": ...}` it will be used
      for formatting the output, instead of the plain text message.
    """

    level_name_colors = {
        5: lambda level_name: _colorize(str(level_name), "blue"),
        _logging.DEBUG: lambda level_name: _colorize(str(level_name), "cyan"),
        _logging.INFO: lambda level_name: _colorize(str(level_name), "green"),
        _logging.WARNING: lambda level_name: _colorize(str(level_name), "yellow"),
        _logging.ERROR: lambda level_name: _colorize(str(level_name), "red"),
        _logging.CRITICAL: lambda level_name: _colorize(str(level_name), "bright_red"),
    }

    def __init__(
        self,
        fmt: _Optional[str] = None,
        datefmt: _Optional[str] = None,
        style: _Literal["%", "{", "$"] = "%",
    ):
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)

    def color_level_name(self, level_name: str, level_no: int) -> str:
        def default(level_name: str) -> str:
            return str(level_name)

        func = self.level_name_colors.get(level_no, default)
        return func(level_name)

    def formatMessage(self, record: _logging.LogRecord) -> str:
        recordcopy = _copy(record)
        levelname = recordcopy.levelname
        seperator = " " * (8 - len(recordcopy.levelname))
        levelname = self.color_level_name(levelname, recordcopy.levelno)
        if "color_message" in recordcopy.__dict__:
            recordcopy.msg = recordcopy.__dict__["color_message"]
            recordcopy.__dict__["message"] = recordcopy.getMessage()
        recordcopy.__dict__["levelprefix"] = levelname + ":" + seperator
        return super().formatMessage(recordcopy)
