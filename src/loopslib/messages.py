import logging
import logging.handlers

from pathlib import Path, PurePath
from sys import stdout, stderr

from . import osinfo


def add_stream(stream, filters, log):
    """Add a stream handler."""
    handler = logging.StreamHandler(stream)
    handler.addFilter(lambda log: log.levelno in filters)

    if stream == stdout:
        handler.setLevel(logging.INFO)

    if stream == stderr:
        handler.setLevel(logging.ERROR)

    log.addHandler(handler)


def logging_conf(log_name, silent=False, level='INFO', log_file='appleloops.log'):
    """Configures overall logging."""
    stdout_filters = [logging.INFO]
    stderr_filters = [logging.DEBUG, logging.ERROR, logging.CRITICAL]

    if osinfo.isroot():
        base_path = Path('/var/log/')
    else:
        base_path = Path('~/Library/Application Support/com.github.carlashley/appleloops/logs/').expanduser()

    log_path = base_path / log_file

    if not log_path.exists():
        _parent = Path(PurePath(log_path).parent)
        _parent.mkdir(parents=True, exist_ok=True)

    log = logging.getLogger(log_name)
    log.setLevel(level.upper())
    file_handler = logging.handlers.RotatingFileHandler(log_path, maxBytes=(1048576 * 10), backupCount=7)
    formatter = logging.Formatter(fmt='%(asctime)s - %(name)s.%(funcName)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(formatter)
    log.addHandler(file_handler)

    # Handle printing INFO/WARNING to stdout and DEBUG/ERROR/CRITICAL to stderr
    # NOTE: DEBUG/ERROR/CRITICAL will always print out even if '-s/--silent' specified.
    add_stream(stderr, stderr_filters, log)

    if not silent:
        add_stream(stdout, stdout_filters, log)

    if Path(log_path).exists():
        file_handler.doRollover()

    # return logging.getLogger(__name__)
