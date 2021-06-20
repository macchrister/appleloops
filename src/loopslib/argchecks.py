import logging
import sys

from pathlib import Path
from urllib.parse import urlparse

from . import curl
from . import osinfo
from . import HTTP_OK
from . import HTTP_MIRROR_TEST_PATHS

LOG = logging.getLogger(__name__)


def error(msg, helper, fatal=False, returncode=1):
    _prefix = '{name}: error: argument'.format(name=sys.argv[0])

    helper(sys.stderr)
    LOG.error('{prefix} {msg}'.format(prefix=_prefix, msg=msg))

    if fatal:
        sys.exit(returncode)


def check(args, helper):
    """Check arguments for specific conditions"""
    # Deployment - must be root
    if args.deployment:
        if not osinfo.isroot():
            LOG.error('You must be root to run in deployment mode.')
            sys.exit(66)

    # Must provide 'mandatory' or 'optional' package set
    if not (args.mandatory or args.optional):
        error(msg='-m/--mandatory or -o/--optional or both are required', fatal=True, helper=helper, returncode=60)

    # APFS DMG requires build
    if args.apfs_dmg and not args.build_dmg:
        error(msg='--APFS: not allowed without argument -b/--build-dmg', fatal=True, helper=helper, returncode=59)

    # Valid Caching Server URL
    if args.cache_server:
        url = urlparse(args.cache_server)

        if not url.port:
            error(msg='-c/--cache-server: requires a port number in http://example.org:556677 format', fatal=True,
                  helper=helper, returncode=58)

        if not url.scheme == 'http':
            error(msg='-c/--cache-server: https is not supported', fatal=True, helper=helper, returncode=57)

    # Specific package mirror options
    if args.pkg_server:
        http_schemes = ['http', 'https']
        args.pkg_server = args.pkg_server.rstrip('/')
        url = urlparse(args.pkg_server)

        # Only do a status check if url scheme
        if url.scheme and url.scheme in http_schemes:
            status = curl.status(args.pkg_server)
        else:
            status = None

        # Correct scheme
        if url.scheme and url.scheme not in http_schemes:
            error(msg='--pkg-server: HTTP/HTTPS scheme required', fatal=True, helper=helper, returncode=56)

        # If the pkg server is not a DMG
        if not args.pkg_server.endswith('.dmg'):
            # Test the mirror has either of the expected mirroring folders per Apple servers
            if not any([curl.status('{mirror}/{testpath}'.format(mirror=args.pkg_server, testpath=_p)) in HTTP_OK
                        for _p in HTTP_MIRROR_TEST_PATHS]):

                _test_paths = ["'{pkgsrv}/{p}'".format(pkgsrv=args.pkg_server, p=_p) for _p in HTTP_MIRROR_TEST_PATHS]
                _msg = ('--pkg-server: mirrored content cannot be found, please ensure packages exist in '
                        '{testpaths}'.format(testpaths=', and/or '.join(_test_paths)))
                error(msg=_msg, fatal=True, helper=helper, returncode=55)
        elif args.pkg_server.endswith('.dmg'):
            # Test if the supplied DMG path exists
            if not url.scheme:
                args.pkg_server = Path(args.pkg_server)

                if not args.pkg_server.exists():
                    error(msg='--pkg-server: file path does not exist', fatal=True, helper=helper, returncode=54)

        # Reachability check for http/https
        if status:
            if status and status not in HTTP_OK:
                error(msg='--pkg-server: HTTP {status} for specified URL'.format(status=status), fatal=True,
                      helper=helper, returncode=53)

    # Convert items that should be file paths to Path objects
    if args.destination:
        args.destination = Path(args.destination)

    if args.build_dmg:
        args.build_dmg = Path(args.build_dmg)

    result = args

    return result
