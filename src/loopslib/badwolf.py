import logging

from pathlib import Path, PurePath

from . import package
from . import resource
from . import PACKAGE_CHOICES

LOG = logging.getLogger(__name__)


def read():
    """Read patch file (pf) for package attribute patching from specific source (source)."""
    result = resource.read(resource='badwolf.yaml')

    return result


def patch(packages, source):
    """Patch the set of packages with any updates"""
    result = set()

    # Convert either a Path/str instance to a PurePath instance
    # and get the basename of the source in the event the source
    # is a URL or filepath or a string of a filepath.
    if isinstance(source, (Path, str)):
        source = str(PurePath(source).name)

    # Map to valid sources if it doesn't end with '.plist'
    if source in PACKAGE_CHOICES and not source.endswith('.plist'):
        source = PACKAGE_CHOICES[source]

    # Raises an IndexError if the source is not a valid source
    if source.endswith('.plist'):
        if source not in [_v for _, _v in PACKAGE_CHOICES.items()]:
            LOG.info('{source} property list for patching is not a valid source.'.format(source=source))
            raise IndexError
 
    # Read the patch info from the badwolf yaml and get the relevant source patches
    patches = read().get(source, dict())

    # Total packages (_t) and counter (_c)
    _t, _c = len(packages), 1

    # Iterate and patch
    for _pkg, _attrs in packages.items():
        _pkg_id = _attrs.get('PackageID', None)
        _patched_attrs = patches.get(_pkg, None)

        # Patch
        if _patched_attrs:
            _attrs.update(_patched_attrs)
            LOG.debug('Patched attributes for {pkg}'.format(pkg=_pkg))

        # Avoid instancing something that already is instanced
        if _pkg_id and _pkg_id not in package.LoopPackage.INSTANCES:
            pkg = package.LoopPackage(**attrs)

            if not pkg.badwolf_ignore:
                result.add(pkg)
        elif _pkg_id and _pkg_id in package.LoopPackage.INSTANCES:
            LOG.info('Already processed {pkgid} - skipping'.format(pkgid=_pkg_id))

        LOG.info('Processed {pkgid}, package ({count} of {total})'.format(pkgid=pkg.package_id, count=_c, total=_t))
        _c += 1


    return result
