import logging

from . import disk
from . import ARGS

LOG = logging.getLogger(__name__)


def generate(packages):
    """Generates statistics about packages"""
    # Generate statistics for display
    mandatory_count = len([pkg for pkg in packages if pkg.mandatory])
    optional_count = len([pkg for pkg in packages if not pkg.mandatory])
    mandatory_dld_size = sum([pkg.download_size for pkg in packages if pkg.mandatory])
    optional_dld_size = sum([pkg.download_size for pkg in packages if not pkg.mandatory])
    mandatory_inst_size = sum([pkg.installed_size for pkg in packages if pkg.mandatory])
    optional_inst_size = sum([pkg.installed_size for pkg in packages if not pkg.mandatory])

    discover_msg = 'Discovered'

    if ARGS.mandatory and mandatory_dld_size > 0:
        mandatory_pkgs = '{count} mandatory packages'.format(count=mandatory_count)
        space_msg = '({download} download size, {install} installed size)'.format(download=disk.convert(mandatory_dld_size),
                                                                                  install=disk.convert(mandatory_inst_size))
        discover_msg = '{msg} {mand_pkgs} {space}'.format(msg=discover_msg,
                                                          mand_pkgs=mandatory_pkgs,
                                                          space=space_msg)
    else:
        discover_msg = 'No mandatory packages to process'

    if ARGS.optional and optional_count > 0:
        if ARGS.mandatory:
            optional_pkgs = 'and {count} optional packages'.format(count=optional_count)
        else:
            optional_pkgs = '{count} optional packages'.format(count=optional_count)
        space_msg = '({download} download size, {install} installed size)'.format(download=disk.convert(optional_dld_size),
                                                                                  install=disk.convert(optional_inst_size))
        discover_msg = '{msg} {opt_pkgs} {space}'.format(msg=discover_msg,
                                                         opt_pkgs=optional_pkgs,
                                                         space=space_msg)
    else:
        if optional_dld_size > 0 and mandatory_dld_size > 0:
            discover_msg = 'and no optional packages to process.'
        elif optional_dld_size > 0:
            discover_msg = 'No optional packages to process.'

    LOG.info(discover_msg)
