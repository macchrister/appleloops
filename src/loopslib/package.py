import logging
import re
import subprocess

from pathlib import Path
from urllib.parse import urlparse

from . import curl
from . import version
from . import pkgutil
from . import ARGS
from . import DMG_MOUNT
from . import FEED_URL

LOG = logging.getLogger(__name__)


class LoopPackage:
    """Package object"""
    INSTANCES = set()  # Track created instances

    def __init__(self, **kwargs):
        self.package_id = kwargs.get('PackageID', None)
        self.download_name = kwargs.get('DownloadName', None)
        self.file_check = kwargs.get('FileCheck', None)
        self.installed_size = kwargs.get('InstalledSize', None)
        self.mandatory = kwargs.get('IsMandatory', False)
        self.package_name = kwargs.get('PackageName', None)
        self.version = version.convert(kwargs.get('PackageVersion', '0.0.0'))

        # Modify Apple attributes
        self.package_id = self.package_id.replace('. ', '') if self.package_id else None  # Apple typo fix

        if self.installed_size:
            if not isinstance(self.installed_size, (int, float)):
                self.installed_size = float(self.installed_size)

        # Set custom attributes
        self.installed = pkgutil.is_installed(self.file_check, self.installed_version, self.version)
        self.upgrade = pkgutil.upgrade_pkg(self.installed_version, self.version)
        self.url = self.parse_url(self.download_name)
        self.download_dest = self.parse_dest(self.download_name)
        self.download_size = curl.headers(self.url).get('content-length', 0)
        self.installed_version = pkgutil.pkg_version(self.package_id) if self.package_id else None
        self.badwolf_ignore = False
        self.status = curl.status(self.url)

        # Add self.package_id to INSTANCES tracker
        self.__class__.INSTANCES.add(self.package_id)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return not self.__dict__ == other.__dict__
        else:
            return NotImplemented

    def __hash__(self):
        if isinstance(self, self.__class__):
            return hash(self.package_id)
        else:
            return NotImplemented

    def parse_url(self, n):
        """Parse a URL to use for downloading."""
        result = None
        _re = re.compile(r'lp10_ms3_content_2016/../lp10_ms3_content_2013')
        url = '{}/{}'.format(FEED_URL, n)
        url = re.sub(_re, 'lp10_ms3_content_2013', url)
        LOG.debug('Set package URL to {url}'.format(url=url))

        # Change the URL if cache server is specified
        if ARGS.cache_server:
            url = urlparse(url)
            url = '{cachesrv}{urlpath}?source={urlnetloc}'.format(cachesrv=ARGS.cache_server,
                                                                  urlpath=url.path,
                                                                  urlnetloc=url.netloc)

        # Change the URL if package server is specified
        if ARGS.pkg_server:
            if '.dmg' in ARGS.pkg_server:
                url = url.replace(FEED_URL, DMG_MOUNT)
            else:
                url = url.replace(FEED_URL, ARGS.pkg_server)

        LOG.debug('Updated package URL to {url}'.format(url=url))
        result = url

        return result

    def parse_dest(self, n):
        """Parse a download destination."""
        result = None
        _re = re.compile(r'lp10_ms3_content_2016/../lp10_ms3_content_2013')
        dest = '{}/{}'.format(ARGS.destination, n)

        result = Path(re.sub(_re, 'lp10_ms3_content_2013', dest))

        return result

    def install(self):
        """Install package, returns a tuple with the process returncode at [0] and success/error message at [1]"""
        result = None
        cmd = ['/usr/sbin/installer', '-dumplog', '-pkg', self.download_dest, '-target', ARGS.install_target]

        # Insert the untrusted flag into the correct part of the install command
        if ARGS.unsigned:
            cmd.insert(1, '-allowUntrusted')

        if not ARGS.dry_run:
            LOG.debug(' '.join(cmd))
            _pfx = 'Upgraded' if self.upgrade else 'Installed'
            _p = subprocess.run(cmd, capture_output=True, encoding='utf-8')

            if _p.returncode == 0:
                result = (_p.returncode, '{prefix} {pkg}'.format(prefix=_pfx, pkg=self.package_id))
                LOG.debug(_p.stdout.strip())
            else:
                _pfx = 'upgrade' if self.upgrade else 'install'
                _lp = '\'/var/log/install.log\''
                result = (_p.returncode, 'Failed to {prefix} {pkg} - check {log}'.format(prefix=_pfx,
                                                                                         pkg=self.package_id,
                                                                                         log=_lp))
                LOG.debug(_p.stderr.strip())

        return result
