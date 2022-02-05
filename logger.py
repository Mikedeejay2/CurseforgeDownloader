from enum import Enum

history = {}


class LogLevel(Enum):
    INFO = 'INFO'
    WARNING = 'WARN'
    SEVERE = 'ERR'


for loglevel in LogLevel:
    history[loglevel] = []


#########################################################
# LOGGING FUNCTIONS
#########################################################

def log(text: str, level: LogLevel):
    print(level.value + ': ' + text)
    history[level].append(text)


def log_info(text: str):
    log(text, LogLevel.INFO)


def log_warning(text: str):
    log(text, LogLevel.WARNING)


def log_severe(text: str):
    log(text, LogLevel.SEVERE)
