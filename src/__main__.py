import logging

from sys import exit

from loopslib import arguments

LOG = logging.getLogger(__name__)


try:
    NotImplemented
except KeyboardInterrupt:
    LOG.info('\nKeyboard Interrupt signal received.')
    exit(0)
