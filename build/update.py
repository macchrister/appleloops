#!/usr/local/bin/python3
# NOTE: This is intended only to facilitate automated updating of the supported property list files
import re
import subprocess
import sys

from datetime import datetime
from pathlib import Path, PurePath

import yaml

CONFIGURATION = Path(PurePath(Path().cwd(), 'src/loopslib/resources/configuration.yaml'))
FEED_URL = 'https://audiocontentdownload.apple.com/lp10_ms3_content_2016'
GLOB = [f for f in Path().cwd().glob('*')]
HTTP_OK = [200, 301, 302, 303, 307, 308]


def status(u):
    """Status code of an HTTP/HTTPS resource"""
    result = None

    # Convert URL from path object to string if path
    if isinstance(u, (Path, PurePath)):
        u = str(u)

    cmd = ['/usr/bin/curl', '-I', '-L', '--silent', '-o', '/dev/null', '-w', '"%{http_code}"', '--user-agent', 'appleloops-update-check', u]
    _p = subprocess.run(cmd, capture_output=True, encoding='utf-8')
    result = int(_p.stdout.strip().replace('"', ''))

    return result


def read_config(conf=CONFIGURATION):
    """Read the appleloops configuration file into a dictionary."""
    result = dict()

    if conf.exists():
        with open(CONFIGURATION, 'r') as _f:
            result = yaml.safe_load(_f)

    return result


def update_supported_sources(sources):
    """Update the supported source files."""
    result = dict()
    ver_reg = re.compile(r'\d+')
    app_reg = re.compile(r'\d+.plist')
    app = list({re.sub(app_reg, '', _v) for _, _v in sources.items()})[0]
    latest_ver = int(sorted([re.findall(ver_reg, _v)[0] for _k, _v in sources.items()], reverse=True)[0]) + 1
    future_ver = latest_ver + 11

    for ver in range(latest_ver, future_ver):
        new_plist = '{app}{ver}.plist'.format(app=app, ver=ver)
        url = '{feedurl}/{sourcefile}'.format(feedurl=FEED_URL, sourcefile=new_plist)
        plist_name = '{app}{ver}'.format(app=app, ver=ver)

        print('Checking {url}'.format(url=url))
        if status(url) in HTTP_OK:
            print('Adding new supported source \'{app}:{source}\''.format(app=app, source=new_plist))
            result[plist_name] = new_plist

    return result


def main():
    cwd = PurePath(Path().cwd()).stem

    if not cwd == 'appleloops':
        print('Cannot be run outside of the \'appleloops\' directory')
        sys.exit(13)

    if CONFIGURATION.exists():
        config = read_config()
        update_version = False

        for app in ['garageband', 'logicpro', 'mainstage']:
            updates = update_supported_sources(sources=config['AUDIOCONTENT']['supported'][app])

            if updates:
                config['AUDIOCONTENT']['supported'][app].update(updates)
                update_version = True

        if update_version:
            old_version = config['MODULE']['version']
            build_date = datetime.now().strftime('%Y-%m-%d')
            major, minor, patch = old_version.split('.')
            patch = str(int(patch) + 1)
            new_version = '{major}.{minor}.{patch}'.format(major=major, minor=minor, patch=patch)

            print('Updated supported sources, bumping version from {old} to {new}, updating build to {build}'.format(old=old_version, new=new_version, build=build_date))
            config['MODULE']['version'] = new_version
            config['MODULE']['build_date'] = build_date

            with open(CONFIGURATION, 'w') as _f:
                yaml.dump(config, _f)
    else:
        print('Cannot find configuration file {conf}'.format(conf=CONFIGURATION))
        sys.exit(12)


if __name__ == '__main__':
    main()
