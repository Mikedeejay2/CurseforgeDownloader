from enum import Enum


class FileReleaseType(Enum):
    RELEASE = 1
    BETA = 2
    ALPHA = 3


class FileStatus(Enum):
    PROCESSING = 1
    CHANGES_REQUIRED = 2
    UNDER_REVIEW = 3
    APPROVED = 4
    REJECTED = 5
    MALWARE_DETECTED = 6
    DELETED = 7
    ARCHIVED = 8
    TESTING = 9
    RELEASED = 10
    READY_FOR_REVIEW = 11
    DEPRECATED = 12
    BAKING = 13
    AWAITING_PUBLISHING = 14
    FAILED_PUBLISHING = 15


class FileRelationType(Enum):
    EMBEDDED_LIBRARY = 1
    OPTIONAL_DEPENDENCY = 2
    REQUIRED_DEPENDENCY = 3
    TOOL = 4
    INCOMPATIBLE = 5
    INCLUDE = 6
