import logging
import re

from datetime import datetime

from . import curl
from . import osinfo
from . import plist
from . import APPLICATIONS
from . import FEED_URL
from . import HTTP_OK
from . import SYSTEM_UPDATER
from . import USER_UPDATER

LOG = logging.getLogger(__name__)


def check(apps, latest, check_ahead):
    """Checks for updates of latest plists on Apple content server and returns the resulting files as a dict"""
    reg = re.compile(r'\d+.plist')  # Compiled regex to strip the version value and plist file extension
    apps = sorted([re.sub(reg, '', app) for app in apps])  # Have to convert these over to basic app names not plist values
    supported = [_k for _k, _ in APPLICATIONS.items()]
    minor_ver_max, patch_ver_max = [int(n) for n in check_ahead]
    result = latest if latest else dict()  # Used if the file doesn't exist or has no updated apps
    found_updates = {'garageband': None,
                     'logicpro': None,
                     'mainstage': None}

    # Source the correct plist to read preferences
    if osinfo.isroot():
        updater_pref = SYSTEM_UPDATER
    else:
        updater_pref = USER_UPDATER

    # Read the last update done to iterate over, ensuring the most recent files that were ok are sourced
    last_update = plist.read(f=updater_pref) if updater_pref.exists() else None

    # If the last update doesn't exist, fetch it
    if not last_update:
        plist.write(d=result, f=updater_pref)
        last_update = result.copy()

    # Iterate over the apps in the last update and get the version value from the plist filename
    # and then jump forward N number of versions to check.

    # Print check message and last check time

    for app, source_plist in last_update.items():
        if app in apps:
            check_msg = f'Checking for updated sources to {app}'

            try:
                check_date = last_update['last_checked'][app]
            except KeyError:
                check_date = None

            try:
                updte_date = last_update['last_updated'][app]
            except KeyError:
                updte_date = None

            if check_date:
                check_date = check_date.strftime('%Y-%m-%d %H:%M:%S')
                check_msg = f'{check_msg} (last checked {check_date})'

            if updte_date:
                updte_date = updte_date.strftime('%Y-%m-%d %H:%M:%S')
                check_msg = f'{check_msg} - last updates found on {updte_date}'

            LOG.info(''.join(check_msg))

            if app in (supported and apps):
                ver = int(source_plist.replace(app, ''))
                ver_str = str(ver)

                # Parse the version string. Hacky at best, will require manual intervention
                # if any of the versioning changes significantly to break this pattern
                if len(ver_str) == 3:  # MainStage
                    major_ver, minor_ver, patch_ver = int(ver_str[0]), int(ver_str[1]), int(ver_str[2])
                elif len(ver_str) == 4:  # GarageBand/Logic Pro
                    major_ver, minor_ver, patch_ver = int(ver_str[:2]), int(ver_str[2]), int(ver_str[3])

                # New max versions, add one to the minor version because it is used in a while loop
                # Don't add one to the  patch version because it checks xxx0 twice.
                new_minor_ver = minor_ver + minor_ver_max + 1
                new_patch_ver = patch_ver + patch_ver_max

                # Create a URL to check, make sure it exists, if it does, update the result dict.
                # This should always return the current 'latest' version if no URL's are found
                while minor_ver < new_minor_ver:
                    _ver = int(f'{major_ver}{minor_ver}{patch_ver}')

                    for new_ver in range(_ver, _ver + new_patch_ver):
                        new_plist = '{app}{ver}'.format(app=app, ver=new_ver)
                        url = '{feedurl}/{plist}.plist'.format(feedurl=FEED_URL, plist=new_plist)

                        LOG.debug('Checking {url}'.format(url=url))

                        status = curl.status(url)

                        if status in HTTP_OK and new_plist != result[app]:
                            found_updates[app] = new_plist
                            result[app] = new_plist

                            # Include a timestamp for the last with successfull update.
                            try:
                                result['last_updated'][app] = datetime.now()
                            except KeyError:
                                result['last_updated'] = {app: datetime.now()}

                            LOG.debug('Found updated source plist at {url}'.format(url=url))

                        # Include a timestamp for the last app check.
                        try:
                            result['last_checked'][app] = datetime.now()
                        except KeyError:
                            result['last_checked'] = {app: datetime.now()}

                    minor_ver += 1

    # Include a last checked timestamp
    result['last_check_in'] = datetime.now()

    # Write the results
    if result:
        plist.write(d=result, f=updater_pref)

    # Collect the updated apps and generate a list of strings to use in update found message.
    updated_apps = ['{plist}.plist'.format(plist=new_plist) for app, new_plist in found_updates.items() if new_plist]

    # Log the updates found
    if updated_apps:
        LOG.info('Found updated sources {updates}, using updated sources'.format(updates=', '.join(updated_apps)))
    else:
        LOG.info('No updated sources found for {apps}, using last known current sources'.format(apps=', '.join(apps)))

    result = {_k: _v for _k, _v in result.items() if _k in apps}

    return result
