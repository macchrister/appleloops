import logging
import shutil

from . import curl
from . import disk
from . import dmg
from . import source
from . import ARGS
from . import TEMPDIR

LOG = logging.getLogger(__name__)

def init_dmg():
    """Creates sparseimages for DMG building."""
    result = None

    # Create a sparse image if building a DMG
    if ARGS.build_dmg and not ARGS.dry_run:
        fs = DMG_DEFAULT_FS
        result = dmg.create_sparse(f=ARGS.build_dmg, fs=DMG_DEFAULT_FS)

    return result


def mount_pkgsrv_dmg():
    """Mount a DMG if it's specified in the package server mirror argument"""
    result = None

    # If deployment mode, mount any DMG that might be specified as the mirror source
    if ARGS.deployment and ARGS.pkg_server and ARGS.pkg_server.endswith('.dmg'):
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
        LOG.info('Download destination is {download_dest}'.format(download_dest=ARGS.destination))

    # Process any apps
    if ARGS.apps:
        if 'garageband' in ARGS.apps:
            garageband = source.Application(app='garageband')

            if garageband and garageband.packages:
                _packages.update(garageband.packages)

        if 'logicpro' in ARGS.apps:
            logicpro = source.Application(app='garageband')

            if logicpro and logicpro.packages:
                _packages.update(logicpro.packages)

        if 'mainstage' in ARGS.apps:
            mainstage = source.Application(app='mainstage')

            if mainstage and mainstage.packages:
                _packages.update(mainstage.packages)

    if ARGS.plists:
        for plist in ARGS.plists:
            app = source.PropertyList(plist=plist)

            if app and app.packages:
                _packages.update(app.packages)

    # If deploying packages, only return those that are being upgraded/installed (or forced install)
    if _packages:
        if ARGS.deployment:
            packages = {pkg for pkg in packages if pkg.upgrade or not pkg.installed or ARGS.force}
        else:
            packages = _packages

        packages = set(sorted(list(packages), key=lambda pkg: pkg.download_name))

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

    if ARGS.deployment and ARGS.pkg_server.endswith('.dmg'):
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
        deploymt_msg_prefix = 'Install' if ARGS.dry_run else 'Installing'

        LOG.info('{dld_prefix} {count} of {total} - {pkgname} ({size})'.format(dld_prefix=download_msg_prefix,
                                                                               count=padded_counter,
                                                                               total=total_pkgs,
                                                                               pkgname=pkg.download_name,
                                                                               size=disk.convert(pkg.download_size)))

        # Do the download
        if not ARGS.dry_run:
            if ARGS.force:
                pkg.download_dest.unlink(missing_ok=True)

            f = curl.get(u=pkg.url, dest=pkg.download_dest, quiet=ARGS.silent, resume=True, http2=ARGS.http2, insecure=ARGS.insecure)

        # Do the deployment
        if ARGS.deployment:
            if pkg.upgade:
                deployment_msg_prefix = 'Upgrade' if ARGS.dry_run else 'Upgrading'

            LOG.info('{inst_prefix} {count} of {total} - {pkgname}'.format(inst_prefix=deployment_msg_prefix,
                                                                           count=padded_counter,
                                                                           total=total_pkgs,
                                                                           pkgname=pkg.download_name))

            # Install - success is logged by the object method.
            installed = pkg.install()

            # Tidy up if this isn't a deployment DMG that's being used as source mirror
            if ARGS.pkg_server and not ARGS.pkg_server.endswith('.dmg'):
                pkg.download_dest.unlink(missing_ok=True)

                if not pkg.download_dest.exists():
                    LOG.warning('Tidied up {pkgname}'.format(pkgname=pkg.download_name))

        counter += 1


def cleanup_tempdir():
    """Cleans up temporary working directory"""
    if TEMPDIR.exists():
        shutil.rmtree(str(TEMPDIR), ignore_errors=True)

        if not TEMPDIR.exists():
            LOG.warning('Tidied up temporary working directory.')
