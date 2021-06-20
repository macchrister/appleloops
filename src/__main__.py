import logging

from datetime import datetime
from sys import exit

from loopslib import ARGS
from loopslib import disk
from loopslib import source

LOG = logging.getLogger(__name__)


try:
    freespace = disk.freespace
    NotImplemented
except KeyboardInterrupt:
    LOG.info('\nKeyboard Interrupt signal received.')
    exit(0)
