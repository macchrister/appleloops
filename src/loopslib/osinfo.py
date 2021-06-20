import subprocess
import sys

from os import geteuid

from . import versions as vers


def arch():
    """Hardware architecture"""
    result = None
    _cmd = ['/usr/bin/arch']
    _p = subprocess.run(_cmd, capture_output=True, encoding='utf-8')

    if _p.returncode == 0:
        result = _p.stdout.strip()

    return result


def curl_version():
    result = None

    _cmd = ['/usr/bin/curl', '--version']
    _p = subprocess.run(_cmd, capture_output=True, encoding='utf-8')

    if _p.returncode == 0:
        result = _p.stdout.strip()

    return result


def build():
    """macOS build"""
    result = None

    _cmd = ['/usr/bin/sw_vers', '-buildVersion']
    _p = subprocess.run(_cmd, capture_output=True, encoding='utf-8')

    if _p.returncode == 0:
        result = _p.stdout.strip()

    return result


def isroot():
    """User is root."""
    result = geteuid() == 0

    return result


def version():
    """macOS version number."""
    # Note: Software version "might" get reported as '10.16' depending on Python used.
    result = None
    _cmd = ['/usr/bin/sw_vers', '-productVersion']
    _p = subprocess.run(_cmd, capture_output=True, encoding='utf-8')

    if _p.returncode == 0:
        result = vers.convert(_p.stdout.strip())

    return result


def python_ver():
    """Python version."""
    result = 'Python {version}'.format(version=' '.join(sys.version.splitlines()))

    return result
