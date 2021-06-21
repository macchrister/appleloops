import logging
import shutil

from sys import exit

from loopslib import curl
from loopslib import disk
from loopslib import dmg
from loopslib import process
from loopslib import source
from loopslib import stats
from loopslib import ARGS
from loopslib import DMG_DEFAULT_FS
from loopslib import TEMPDIR

LOG = logging.getLogger(__name__)


try:
    # NOTE: Due to how the package objects are instanced, only mandatory/optional
    #       packages will be in the 'app.packages' set if the relevant
    #       '-m/--mandatory' and/or '-o/--optional' argument is provided.
    # garageband = None
    # logicpro = None
    # mainstage = None
    # packages = set()

    # Creates a sparse image if building a DMG
    sparseimage = process.init_dmg()

    # Mount a DMG if a DMG has been specified as a the package mirror source
    deployment_dmg = process.mount_pkgsrv_dmg()

    # Set up app object instances and packages set.
    garageband, logicpro, mainstage, packages = process.apps_plists()

    # Do freespace checks, exits if not enough space.
    has_freespace, drive_dest = process.freespace_checks(packages)

    # Do the deed
    total_pkgs = len(packages)
    counter = 1

    # Generate statistics
    stats.generate(packages)

    # Download or install
    process.download_install(packages)

    # Unmount the package server DMG
    if ARGS.pkg_server and ARGS.pkg_server.endswith('.dmg'):
        deployment_dmg = dmg.eject()

    # Convert sparseimage to DMG if creating a DMG
    if ARGS.build_dmg and not ARGS.dry_run:
        converted_sparseimage = dmg.convert_sparse(s=sparseimage, f=ARGS.build_dmg)

        # Tidy up the temporary sparseimage
        if converted_sparseimage:
            sparseimage.unlink(missing_ok=True)

            if not sparseimage.exists():
                LOG.info('Tidied up sparse image {image}'.format(image=str(sparseimage)))

    # Clean up temporary working directory
    process.cleanup_tempdir()

except KeyboardInterrupt:
    LOG.info('\nKeyboard Interrupt signal received.')
    exit(22)
