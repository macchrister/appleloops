import logging

from pathlib import Path, PurePath
from pprint import pformat

from . import package
from . import resource
from . import ARGS
from . import PACKAGE_CHOICES

LOG = logging.getLogger(__name__)


def read():
    """Read patch file (pf) for package attribute patching from specific source (source)."""
    result = resource.read(resource='badwolf.yaml')

    return result


def patch(packages, source, comparing=False):
    """Patch the set of packages with any updates"""
    result = set()
    sources = dict()
    _packages = {_pkg: _attrs for _pkg, _attrs in packages.items()
                 if (ARGS.mandatory and _attrs.get('IsMandatory', False)) or (ARGS.optional and not _attrs.get('IsMandatory', False))}

    for app in PACKAGE_CHOICES:
        sources.update({_k: _v for _k, _v in PACKAGE_CHOICES[app].items()})

    # Convert either a Path/str instance to a PurePath instance
    # and get the basename of the source in the event the source
    # is a URL or filepath or a string of a filepath.
    if isinstance(source, (Path, str)):
        source = str(PurePath(source).name)

    # Map to valid sources if it doesn't end with '.plist'
    if source in sources and not source.endswith('.plist'):
        source = sources[source]

    # Raises an IndexError if the source is not a valid source
    if source.endswith('.plist'):
        if source not in [_v for _, _v in sources.items()]:
            LOG.info('{source} property list for patching is not a valid source.'.format(source=source))
            raise IndexError

    # Read the patch info from the badwolf yaml and get the relevant source patches
    patches = read().get(source, dict())

    # Total packages (total) and counter (counter)
    total, counter = len([_p for _p in _packages]), 1
    LOG.info('Processing {total} packages from {source}'.format(total=total, source=source))

    # Iterate and patch
    for _pkg, _attrs in _packages.items():
        _original_attrs = _attrs.copy()
        _new_attrs = _attrs.copy()
        _pkg_id = _attrs.get('PackageID', None)
        _patched_attrs = patches.get(_pkg, None)
        _badwolf_ignore = _patched_attrs.get('BadWolfIgnore', False) if _patched_attrs else False
        _padded_count = '{i:0{width}d}'.format(width=len(str(total)), i=counter)
        # Not really a warning, but this is the easiest way to not print to stdout when logging with the stdout/stderr
        # stream handlers set up in 'messages'.
        LOG.warning('Processing ({count} of {total}) - {pkgid}'.format(pkgid=_pkg_id, count=_padded_count, total=total))

        # Patch
        if _patched_attrs:
            _new_attrs.update(_patched_attrs)

            if not _original_attrs == _new_attrs:
                LOG.debug('Original attributes for {pkg}:\n{attrs}'.format(pkg=_pkg, attrs=pformat(_original_attrs)))
                LOG.debug('Patched attributes for {pkg}:\n{attrs}'.format(pkg=_pkg, attrs=pformat(_new_attrs)))
            elif _original_attrs == _new_attrs:
                LOG.warning('Skipped patching {pkg} in {source} as attributes are correct'.format(pkg=_pkg, source=source))
                _new_attrs = None

        # If comparing sources, then the package needs to be added regardles.
        if comparing:
            pkg = package.LoopPackage(**_attrs) if not _new_attrs else package.LoopPackage(**_new_attrs)
            result.add(pkg)
        else:
            if _badwolf_ignore:
                LOG.debug('Ignoring package {pkg} per BadWolfIgnore in {source}'.format(pkg=_pkg, source=source))

            # Avoid instancing something that already is instanced
            if _pkg_id and _pkg_id not in package.LoopPackage.INSTANCES:
                pkg = package.LoopPackage(**_attrs) if not _new_attrs else package.LoopPackage(**_new_attrs)

                if not _badwolf_ignore:
                    result.add(pkg)
                    LOG.debug('{attrs}'.format(attrs=pkg.__dict__))
            elif _pkg_id and _pkg_id in package.LoopPackage.INSTANCES:
                LOG.debug('Already processed {pkgid} - skipping'.format(pkgid=_pkg_id))

        _msg = 'Processed ({count} of {total}) - {pkgid}'.format(pkgid=_pkg_id, count=_padded_count, total=total)
        counter += 1
        # Add an extra line in the debug output for readability
        if counter - 1 != total:
            _msg = '{msg}\n'.format(msg=_msg)

        LOG.debug(_msg)

    return result
