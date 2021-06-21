import logging
import re
import subprocess

from collections import namedtuple
from pathlib import Path, PurePath

from . import osinfo
from . import plist
from . import versions

LOG = logging.getLogger(__name__)


def convert(b):
    """Converts bytes to human readable value"""
    result = None
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    counter = 0

    while b > 1024 and counter < 5:
        counter += 1
        b = b / 1024.0

    suffix = suffixes[counter]
    result = '{0:.2f}'.format(b)
    result = result.replace('.0', '') if result.endswith('.0') else result
    result = result.replace('.00', '') if result.endswith('.00') else result
    result = '{size} {suffix}'.format(size=result, suffix=suffix)

    return result


def df(p):
    """Parse 'df' to determine the device of the specified path."""
    # NOTE: The regex here includes the full logical device path
    # as when the result is passed to 'diskutil' if the device
    # is the phyiscal device, then free space stats are not necessarily
    # provided.
    result = None
    p = Path(p)

    # The specified directory may not exist, so travel up the path until one does
    while not p.exists():
        p = Path(PurePath(p).parent)

    cmd = ['/bin/df', str(p)]
    _p = subprocess.run(cmd, capture_output=True, encoding='utf-8')
    reg = re.compile(r'/dev/disk\w+')  # Include the 'slices' for proper logical device

    if _p.returncode == 0:
        for line in _p.stdout.splitlines():
            line = line.strip()

            if re.search(reg, line):
                result = re.findall(reg, line)[0]
                break

    return result


def freespace(d):
    """Freespace available on specified destination, returns namedtuple (bytes, hr)"""
    result = None
    device = df(d)  # Query for the device because 'diskutil' only works on disks, duh.
    cmd = ['/usr/sbin/diskutil', 'info', '-plist', str(device)]
    fs_key = 'FreeSpace' if osinfo.version() < versions.convert('10.15') else 'APFSContainerFree'
    Result = namedtuple('Result', ['bytes', 'hr'])

    _p = subprocess.run(cmd, capture_output=True)

    if _p.returncode == 0:
        b = plist.read_string(_p.stdout).get(fs_key, None)
        b = float(b) if b else None
        hr = convert(b)
        result = Result(b, hr)

    return result
