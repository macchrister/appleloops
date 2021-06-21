import logging
import sys

from pathlib import PurePath

from . import disk
from . import ARGS

LOG = logging.getLogger(__name__)


def generate(packages):
    """Generates statistics about packages"""
    # Generate statistics for display
    mandatory_count = len([pkg for pkg in packages if pkg.mandatory])
    optional_count = len([pkg for pkg in packages if not pkg.mandatory])
    mandatory_dld_size = disk.convert(sum([pkg.download_size for pkg in packages if pkg.mandatory]))
    optional_dld_size = disk.convert(sum([pkg.download_size for pkg in packages if not pkg.mandatory]))
    mandatory_inst_size = disk.convert(sum([pkg.installed_size for pkg in packages if pkg.mandatory]))
    optional_inst_size = disk.convert(sum([pkg.installed_size for pkg in packages if not pkg.mandatory]))

    discover_msg = 'Discovered'

    if ARGS.mandatory:
        mandatory_pkgs = '{count} mandatory packages'.format(count=mandatory_count)
        space_msg = '({download} download size, {install} installed size)'.format(download=mandatory_dld_size,
                                                                                  install=mandatory_inst_size)
        discover_msg = '{msg} {mand_pkgs} {space}'.format(msg=discover_msg,
                                                          mand_pkgs=mandatory_pkgs,
                                                          space=space_msg)

    if ARGS.optional:
        if ARGS.mandatory:
            optional_pkgs = 'and {count} optional packages'.format(count=optional_count)
        else:
            optional_pkgs = '{count} optional packages'.format(count=optional_count)
        space_msg = '({download} download size, {install} installed size)'.format(download=optional_dld_size,
                                                                                  install=optional_inst_size)
        discover_msg = '{msg} {opt_pkgs} {space}'.format(msg=discover_msg,
                                                         opt_pkgs=optional_pkgs,
                                                         space=space_msg)

    LOG.info(discover_msg)
