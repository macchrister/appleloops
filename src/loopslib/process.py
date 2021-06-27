import logging
import shutil
import sys

from pathlib import Path, PurePath
from urllib.parse import urlparse

from . import curl
from . import compare
from . import disk
from . import dmg
from . import source
from . import ARGS
from . import DMG_DEFAULT_FS
from . import DMG_MOUNT
from . import PKG_SERVER_IS_DMG
from . import TEMPDIR

LOG = logging.getLogger(__name__)


def init_dmg():
    """Creates sparseimages for DMG building."""
    result = (None, None, None)  # Avoids unpacking errors if no sparse image is created

    # Create a sparse image if building a DMG
    if ARGS.build_dmg and not ARGS.dry_run:
        result = dmg.create_sparse(f=ARGS.build_dmg, fs=DMG_DEFAULT_FS)

    return result


def mount_pkgsrv_dmg():
    """Mount a DMG if it's specified in the package server mirror argument"""
    result = None

    # If deployment mode, mount any DMG that might be specified as the mirror source
    if ARGS.deployment and ARGS.pkg_server and PKG_SERVER_IS_DMG:
        result = dmg.mount(f=ARGS.pkg_server, read_only=True)

    return result


def apps_plists():
    """Creates object instances for each app if required, returns a tuple of objects and packages."""
    result = None
    garageband, logicpro, mainstage, packages = (None, None, None, set())
    _packages = set()

    if ARGS.dry_run:
        LOG.info('Processing Apple audio content (dry run), this may take some time.')
    else:
        LOG.info('Processing Apple audio content, this may take some time.')

    if not ARGS.deployment:
        if ARGS.build_dmg:
            dest_msg = 'Download destination is {download_dest} (mounted to {mount})'.format(download_dest=ARGS.build_dmg, mount=DMG_MOUNT)
        else:
            dest_msg = 'Download destination is {download_dest}'.format(download_dest=ARGS.destination)

        LOG.info(dest_msg)

    # Process any apps
    if ARGS.apps:
        for application in ARGS.apps:
            a = source.Application(app=application)

            if a.installed:
                if a.packages:
                    _packages.update(a.packages)
            else:
                LOG.info('No application installed for {app}, skipping'.format(app=application))

    # Process any plists
    if ARGS.plists:
        for plist in ARGS.plists:
            p = source.PropertyList(plist=plist)

            if p and p.packages:
                _packages.update(p.packages)

    # If deploying packages, only return those that are being upgraded/installed (or forced install)
    if _packages:
        if ARGS.deployment:
            packages = [pkg for pkg in _packages if pkg.upgrade or not pkg.installed or ARGS.force]
        else:
            packages = [pkg for pkg in _packages]

    # Sort the packages by the sequence number if it exists, else by name
    _unsequenced_packages = sorted([pkg for pkg in packages if not pkg.sequence_number], key=lambda pkg: pkg.download_name)
    _sequenced_packages = sorted([pkg for pkg in packages if pkg.sequence_number], key=lambda pkg: pkg.sequence_number)
    packages = _unsequenced_packages + _sequenced_packages

    result = (garageband, logicpro, mainstage, packages)

    return result


def freespace_checks(packages):
    """Handle the freespace checks and result (returned as tuple of freespace boolean, dest path)"""
    result = None
    required_disk_space = 0
    required_inst_space = 0

    # Update required space info
    required_disk_space += sum([pkg.download_size for pkg in packages])
    required_inst_space += sum([pkg.installed_size for pkg in packages])
    required_totl_space = sum([required_disk_space, required_inst_space])

    if ARGS.deployment and ARGS.pkg_server and PKG_SERVER_IS_DMG:
        has_freespace = required_inst_space < disk.freespace(d=ARGS.install_target).bytes
        drive_dest = ARGS.install_target
    elif ARGS.deployment:
        has_freespace = required_totl_space < disk.freespace(d=ARGS.install_target).bytes
        drive_dest = ARGS.install_target
    elif not ARGS.deployment:
        # Test free space in location where DMG is stored if building DMG else
        # test the download destination.
        if ARGS.build_dmg:
            has_freespace = required_disk_space < disk.freespace(d=ARGS.build_dmg).bytes
            drive_dest = str(PurePath(ARGS.build_dmg).parent)
        else:
            has_freespace = required_disk_space < disk.freespace(d=ARGS.destination).bytes
            drive_dest = ARGS.build_dmg

    result = (has_freespace, drive_dest)

    if not has_freespace:
        LOG.info('Insufficient space on {dest}'.format(dest=drive_dest))
        sys.exit(33)
    else:
        LOG.warning('Freespace checks passed.')

    return result


def download_install(packages):
    """Downloads or installs packages depending on arguments."""
    # Number of packages and incrementing counter
    total_pkgs, counter = (len(packages), 1)

    # Iterate
    for pkg in packages:
        padded_counter = '{count:0{width}d}'.format(count=counter, width=len(str(total_pkgs)))
        download_msg_prefix = 'Download' if ARGS.dry_run else 'Downloading'
        deployment_msg_prefix = 'Install' if ARGS.dry_run else 'Installing'
        urlscheme = urlparse(pkg.url).scheme

        # Update the deployment message prefix for upgrade/force install scenarios
        if pkg.upgrade:
            deployment_msg_prefix = 'Upgrade' if ARGS.dry_run else 'Upgrading'

        if ARGS.force:
            deployment_msg_prefix = 'Reinstall' if ARGS.dry_run else 'Reinstalling'

        # Only log downloads if there is a URL scheme
        if urlscheme:
            LOG.info('{dld_prefix} {count} of {total} - {pkgname} ({size})'.format(dld_prefix=download_msg_prefix,
                                                                                   count=padded_counter,
                                                                                   total=total_pkgs,
                                                                                   pkgname=pkg.download_name,
                                                                                   size=disk.convert(pkg.download_size)))

        # Do the download
        if not ARGS.dry_run:
            # Don't unlink files on a deployment server/cache server
            if ARGS.force and not ARGS.deployment and not (ARGS.pkg_server or ARGS.cache_server):
                pkg.download_dest.unlink(missing_ok=True)

            # Don't download off a mounted DMG image
            if ARGS.pkg_server and PKG_SERVER_IS_DMG:
                f = pkg.download_dest
            if urlscheme:
                f = curl.get(u=pkg.url, dest=pkg.download_dest, quiet=ARGS.silent, resume=True, http2=ARGS.http2, insecure=ARGS.insecure)

        # Do the deployment
        if ARGS.deployment:
            msg = '{inst_prefix} {count} of {total} - {pkgname}'.format(inst_prefix=deployment_msg_prefix,
                                                                        count=padded_counter,
                                                                        total=total_pkgs,
                                                                        pkgname=pkg.download_name)

            # If not dry run, safe to to do the install, else just log info
            if not ARGS.dry_run:
                if f.exists():
                    LOG.info(msg)

                    # Install - success is logged by the object method. Dry run is handled by the install method
                    installed = pkg.install()

                    # Tidy up if this isn't a deployment DMG that's being used as source mirror
                    if ARGS.pkg_server and not PKG_SERVER_IS_DMG:
                        if installed:
                            pkg.download_dest.unlink(missing_ok=True)

                            if not pkg.download_dest.exists():
                                LOG.warning('Tidied up {pkgname}'.format(pkgname=pkg.download_name))
            elif ARGS.dry_run:
                LOG.info(msg)

        counter += 1

    if ARGS.deployment and ARGS.pkg_server and PKG_SERVER_IS_DMG == '.dmg':
        dmg.eject()


def compare_sources():
    """Compare's two property lists and prints a diff output."""
    compare.sources(ARGS.compare[0], ARGS.compare[1])


def convert_sparse(s, f=ARGS.build_dmg):
    """Convert the sparseimage into a DMG"""
    if ARGS.build_dmg:
        converted_sparseimage = dmg.convert_sparse(s=s, f=ARGS.build_dmg)

        # Tidy up the temporary sparseimage
        if converted_sparseimage:
            s.unlink(missing_ok=True)

            if not s.exists():
                LOG.warning('Tidied up sparse image {image}'.format(image=str(s)))


def cleanup():
    """Cleans up temporary working directory"""
    if TEMPDIR.exists():
        shutil.rmtree(str(TEMPDIR), ignore_errors=True)

        if not TEMPDIR.exists():
            LOG.warning('Tidied up temporary working directory.')

    if Path(DMG_MOUNT).exists():
        dmg.eject()
