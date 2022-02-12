from enum import Enum
from typing import List, Tuple


class LogLevel(Enum):
    INFO = 'INFO'
    WARNING = 'WARN'
    SEVERE = 'ERR'


# history: List[Tuple[LogLevel, str]]
history = []


#########################################################
# LOGGING FUNCTIONS
#########################################################

def log(text: str, level: LogLevel):
    print(level.value + ': ' + text)
    history.append((level, text))


def log_info(text: str):
    log(text, LogLevel.INFO)


def log_warning(text: str):
    log(text, LogLevel.WARNING)


def log_severe(text: str):
    log(text, LogLevel.SEVERE)
