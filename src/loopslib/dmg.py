import logging
import re
import subprocess
import sys

from pathlib import Path

from . import plist
from . import ARGS
from . import DMG_DEFAULT_FS
from . import DMG_MOUNT
from . import DMG_VOLUME_NAME
from . import VALID_DMG_FS

LOG = logging.getLogger(__name__)


def mountpoint(entities):
    """Return tuple of (mountpoint, device) from 'hdiutil' output"""
    result = None
    reg = re.compile(r'/dev/disk\d+')

    # When a DMG is mounted, the mount volume and device 'keys'
    # are in the same entity, so when both 'mount' and 'device'
    # exist, we have the right info.
    for ent in entities:
        _dev = ent.get('dev-entry', None)
        device = re.findall(reg, _dev)[0] if _dev else None
        mount = ent.get('mount-point', None)

        if mount and device:
            result = (mount, device)
            break

    return result


def sparse_exists(p):
    """Checks for any sparseimages already mounted"""
    result = None
    cmd = ['/usr/bin/hdiutil', 'info', '-plist']
    _p = subprocess.run(cmd, capture_output=True)
    LOG.debug('{cmd} ({returncode})'.format(cmd=' '.join(cmd), returncode=_p.returncode))

    if _p.returncode == 0:
        images = plist.read_string(_p.stdout).get('images', None)

        if images:
            for img in images:
                _path = img.get('image-path', None)
                _type = img.get('image-type', None)
                _entities = img.get('system-entities', None)

                if _path and _type and _path == p:
                    if _type == 'sparse disk image' and _entities:
                        result = mountpoint(_entities)
    else:
        LOG.info(_p.stderr.decode('utf-8').strip())

    return result


def mount(f, mountpoint=DMG_MOUNT, read_only=False):
    """Mount a DMG, returns the mount path if successful"""
    result = None
    cmd = ['/usr/bin/hdiutil', 'attach', '-mountpoint', str(mountpoint), '-plist', f]

    # Insert read only option in the correct spot
    if read_only:
        cmd.insert(2, '-readonly')

    if not ARGS.dry_run:
        _p = subprocess.run(cmd, capture_output=True)
        LOG.debug('{cmd} ({returncode})'.format(cmd=' '.join(cmd), returncode=_p.returncode))

        if _p.returncode == 0:
            _entities = plist.read_string(_p.stdout).get('system-entities')

            if _entities:
                result = mountpoint(_entities)
                LOG.info('Mounted {dmg} to {mountpoint}'.format(dmg=f, mountpoint=mountpoint))
        else:
            LOG.info(_p.stderr.decode('utf-8').strip())

    return result


def eject(mountpoint=DMG_MOUNT):
    """Eject a mounted DMG"""
    cmd = ['/usr/bin/hdiutil', 'eject', '-quiet', str(mountpoint)]
    _p = subprocess.run(cmd, capture_output=True, encoding='utf-8')
    LOG.debug('{cmd} ({returncode})'.format(cmd=' '.join(cmd), returncode=_p.returncode))

    if _p.returncode == 0:
        LOG.info('Unmounted {mountpoint}'.format(mountpoint=mountpoint))
        LOG.debug(_p.stdout.strip())
    else:
        LOG.debug(_p.stderr.strip())


def create_sparse(f, vol=DMG_VOLUME_NAME, fs=DMG_DEFAULT_FS, mountpoint=DMG_MOUNT):
    """Create a thin sparse image, returns the mount point if successfully created"""
    result = None

    if not ARGS.dry_run:
        if fs not in VALID_DMG_FS:
            raise TypeError

        sparse = sparse_exists(f)

        if sparse_exists(f) and Path(f).exists():
            mountpoint = sparse[0]
            result = mount(f, mountpoint)
        else:
            cmd = ['/usr/bin/hdiutil', 'create', '-ov', '-plist', '-volname', vol, '-fs', fs, '-attach', '-type', 'SPARSE', str(f)]
            _p = subprocess.run(cmd, capture_output=True)
            LOG.debug('{cmd} ({returncode})'.format(cmd=' '.join(cmd), returncode=_p.returncode))

            if _p.returncode == 0:
                LOG.info('Created temporary sparseimage {img}'.format(img=f))
                _entities = plist.read_string(_p.stdout).get('system-entities')

                if _entities:
                    result = mountpoint(_entities)
                    LOG.info('Mounted sparse image to {mountpoint}'.format(mountpoint=result))
            else:
                LOG.info(_p.stderr.decode('utf-8').strip())
                sys.exit(88)

    return result


def convert_sparse(s, f):
    """Converts a sparse image to DMG, returns the DMG path if successful"""
    result = None
    cmd = ['/usr/bin/hdiutil', 'convert', '-ov', '-quiet', str(s), '-format', 'UDZO', '-o', str(f)]

    if not ARGS.dry_run:
        LOG.info('Converting {sparseimage}'.format(sparseimage=s))
        # Eject first
        eject()
        _p = subprocess.run(cmd, capture_output=True, encoding='utf-8')
        LOG.debug('{cmd} ({returncode})'.format(cmd=' '.join(cmd), returncode=_p.returncode))

        if _p.returncode == 0:
            LOG.info('Created {dmg}'.format(dmg=f))
            result = Path(f)
        else:
            LOG.info(_p.stderr.strip())

    return result
