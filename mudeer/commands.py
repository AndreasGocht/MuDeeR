import logging
import re
import enum


class Commands(enum.Enum):
    """
    available commands
    """
    MOVE_CHANNEL = 1
    FOLLOW = 2
    SEND_MESSAGE = 3
    MOVE_USER = 4
