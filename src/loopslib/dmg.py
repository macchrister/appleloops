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


def mount_device(entities):
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
                result = mount_device(_entities)
                LOG.warning('Mounted {dmg} to {mountpoint}'.format(dmg=f, mountpoint=mountpoint))
        else:
            LOG.info(_p.stderr.decode('utf-8').strip())

    return result


def eject(mountpoint=DMG_MOUNT, silent=False):
    """Eject a mounted DMG"""
    cmd = ['/usr/bin/hdiutil', 'eject', '-quiet', str(mountpoint)]
    _p = subprocess.run(cmd, capture_output=True, encoding='utf-8')
    LOG.debug('{cmd} ({returncode})'.format(cmd=' '.join(cmd), returncode=_p.returncode))

    if _p.returncode == 0:
        if not silent:
            LOG.info('Unmounted {mountpoint}'.format(mountpoint=mountpoint))

        LOG.debug(_p.stdout.strip())
    else:
        LOG.debug(_p.stderr.strip())


def create_sparse(f, vol=DMG_VOLUME_NAME, fs=DMG_DEFAULT_FS, mountpoint=DMG_MOUNT):
    """Create a thin sparse image, returns the mount point if successfully created"""
    result = None
    sparseimage = Path('{f}.sparseimage'.format(f=f)) if not str(f).endswith('.sparseimage') else Path(f)
    mountpoint = Path(mountpoint)

    if not ARGS.dry_run:
        if fs not in VALID_DMG_FS:
            raise TypeError

        # If the sparseimage exists and is already mounted
        if  sparseimage.exists() and mountpoint.exists():
            LOG.warning('Unmounting existing mount point for {mount}'.format(mount=mountpoint))
            eject(silent=True)
            result = mount(sparseimage, mountpoint)
        else:
            cmd = ['/usr/bin/hdiutil', 'create', '-ov', '-plist', '-volname', vol, '-fs', fs, '-attach', '-type', 'SPARSE', str(f)]
            _p = subprocess.run(cmd, capture_output=True)
            LOG.debug('{cmd} ({returncode})'.format(cmd=' '.join(cmd), returncode=_p.returncode))

            if _p.returncode == 0:
                LOG.warning('Created temporary sparseimage for {img}'.format(img=f))
                _stdout = plist.read_string(_p.stdout)
                _image_path = _stdout.get('image-components')[0]  # This may not always be the sparseimage filename?
                _entities = _stdout.get('system-entities')

                if _entities:
                    result = mount_device(_entities)
                    LOG.warning('Mounted sparse image to {mountpoint}'.format(mountpoint=result))
            else:
                LOG.info(_p.stderr.decode('utf-8').strip())
                sys.exit(88)

    if result and sparseimage and sparseimage not in result:
        result = (sparseimage, result[0], result[1])

    return result


def convert_sparse(s, f):
    """Converts a sparse image to DMG, returns the DMG path if successful"""
    result = None
    cmd = ['/usr/bin/hdiutil', 'convert', '-ov', '-quiet', str(s), '-format', 'UDZO', '-o', str(f)]

    if not ARGS.dry_run:
        LOG.info('Converting {sparseimage}'.format(sparseimage=s))
        # Eject first
        eject(silent=True)
        _p = subprocess.run(cmd, capture_output=True, encoding='utf-8')
        LOG.debug('{cmd} ({returncode})'.format(cmd=' '.join(cmd), returncode=_p.returncode))

        if _p.returncode == 0:
            LOG.info('Created {dmg}'.format(dmg=f))
            result = Path(f)
        else:
            LOG.info(_p.stderr.strip())

    return result
