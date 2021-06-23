import logging
import re

from collections import namedtuple
from pathlib import Path
from urllib.parse import urlparse

from . import badwolf
from . import curl
from . import osinfo
from . import plist
from . import APPLICATIONS
from . import APPLICATION_FOLDER
from . import ARGS
from . import FEED_URL
from . import HTTP_OK
from . import TEMPDIR

LOG = logging.getLogger(__name__)


class Application:
    """Installed application source of audio content packages."""
    def __init__(self, app):
        self.app = app
        self.f = Path(APPLICATION_FOLDER) / APPLICATIONS[self.app] / 'Contents/Resources'
        self.installed = self.f.exists()

        if self.installed:
            info = self.appinfo
            LOG.warning('{app} {version} requires macOS {minos} (macOS {osver} installed)'.format(app=info.name,
                                                                                                  version=info.ver,
                                                                                                  minos=info.min_os,
                                                                                                  osver=osinfo.version()))

            self.packages = self.parse_plist()
        else:
            self.packages = None

    def parse_plist(self):
        """Parses the plist."""
        result = None
        reg = re.compile(r'{app}\d+.plist'.format(app=self.app))
        dest = sorted([Path(_f) for _f in self.f.glob('{app}*.plist'.format(app=self.app))
                       if re.search(reg, str(_f))], reverse=True)[0]

        if dest.exists():
            result = plist.read(dest).get('Packages', None)

        # Patch and create instances of packages
        if result:
            LOG.debug('Loaded packages from {plist}'.format(plist=dest))
            result = badwolf.patch(packages=result, source=dest)

        return result

    @property
    def appinfo(self):
        """App information."""
        result = None
        f = Path(APPLICATION_FOLDER) / APPLICATIONS[self.app] / 'Contents/Info.plist'
        info = plist.read(f)
        ver = info.get('CFBundleShortVersionString', None)
        min_os = info.get('LSMinimumSystemVersion', None)
        name = info.get('CFBundleName', None)
        bundle_id = info.get('CFBundleIdentifier', None)

        Info = namedtuple('Info', ['bundle', 'min_os', 'name', 'ver'])
        result = Info(bundle=bundle_id, min_os=min_os, name=name, ver=ver)

        return result


class PropertyList:
    """Property list source of audio content packages."""
    def __init__(self, plist, comparing=False):
        self.comparing = comparing  # Used for badwolf - process ALL packages
        self.plist = '{feedurl}/{plist}'.format(feedurl=FEED_URL, plist=plist)
        self.packages = self.parse_plist()

    def parse_plist(self):
        """Parses the plist."""
        result = None
        url = urlparse(self.plist)

        # If the file is a URL, it needs to be fetched first
        if url.scheme and url.scheme in ['http', 'https']:
            dest = Path('{tmp}/{fp}'.format(tmp=str(TEMPDIR), fp=url.path.lstrip('/')))

            if curl.status(self.plist) in HTTP_OK:
                # NOTE: Always get this property list silently even in a dry run.
                f = curl.get(u=self.plist, dest=str(dest), quiet=True, http2=ARGS.http2, insecure=ARGS.insecure, dry_run=False)

                if f and dest.exists():
                    LOG.debug('Fetched {plist}'.format(plist=self.plist))
                    result = plist.read(f).get('Packages', None)

                    # Clean up
                    LOG.debug('Tidying up {plist}'.format(plist=dest))
                    dest.unlink(missing_ok=True)

                    if not dest.exists():
                        LOG.debug('Tidied up {plist}'.format(plist=dest))
                elif not dest.exists():
                    LOG.info('{plist} not found'.format(plist=dest))
        elif not url.scheme or isinstance(plist, (Path)):
            if not isinstance(self.plist, Path):
                self.plist = Path(self.plist)

            if self.plist.exists():
                result = plist.read(self.plist).get('Packages', None)

        # Patch and create instances of packages
        if result:
            LOG.debug('Loaded packages from {plist}'.format(plist=self.plist))
            result = badwolf.patch(packages=result, source=self.plist, comparing=self.comparing)

        return result
