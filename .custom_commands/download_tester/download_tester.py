"""
Script designed to automate the process of download testing when
given a bundle type and release version. This script has the
following requirements:

1. Must have chrome browser installed and chromedriver somewhere in your $PATH
(To install chromedriver, run script and see link in error message)

2. Run on Linux or Mac

note: if -build_id is used, you must be connected to the PDX VPN

example usages:
    python3 download_tester.py academic 21-1 -build_id 161
    python3 download_tester.py academic 21-1 -manual
"""
import argparse
import hashlib
import logging
import os
import re
import requests
import time

from argparse import RawDescriptionHelpFormatter
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys


TIMEOUT = 6000
URL = "https://schrodinger-staging.metaltoad-sites.com/downloads/releases"
ACADEMIC_URL = "https://schrodinger-staging.metaltoad-sites.com/freemaestro/"
LOGIN_CREDENTIALS = {
    "non-commercial": {
        "user": "academic@schrodinger.com",
        "pass": "password"
    },
    "commercial": {
        "user": "commercial@schrodinger.com",
        "pass": "password"
    },
    "advanced": {
        "user": "advanced@sch-gsuite.services",
        "pass": "Te5t1ng!"
    },
    "academic": {
        "user": "academic@schrodinger.com",
        "pass": "password"
    }
}


def parse_args():
    """
    Parse the command line arguments.

    :return args:  All script arguments
    :rtype args:  class:`argparse.Namespace`
    """

    parser = argparse.ArgumentParser(
        formatter_class=RawDescriptionHelpFormatter, description=__doc__)

    parser.add_argument(
        "bundle_type",
        metavar="bundle_type",
        help="Type of bundle",
        choices=["academic", "advanced", "commercial", "non-commercial"])

    parser.add_argument(
        "release",
        metavar="release",
        help="Release version in YY-Q format (eg. 21-1)")

    parser.add_argument(
        "-build_id",
        metavar="###",
        help="obtain ref checksums from given build ID (eg. 054, 132)")

    parser.add_argument(
        "-manual",
        help="manually input reference checksums",
        action="store_true",
        default=False)

    args = parser.parse_args()

    # Verify release argument is in correct format
    if not re.search('^[2][0-9]-[1-4]$', args.release):
        parser.error('Incorrect release given')

    # require -build_id or -manual to be passed
    if not args.build_id and not args.manual:
        parser.error('Missing one of the following arguments: -build_id, -manual')
    elif args.build_id and args.manual:
        parser.error(
            'You can only supply one of the following arguments: -build_id, -manual')

    # Verify -build_id argument is in correct format
    if args.build_id and not re.search('^[0-9][0-9][0-9]$', args.build_id):
        parser.error('Improper build format given')

    return args



def download_all_bundles(driver, bundle_type, release):
    for platform_id in ["edit-linux", "edit-windows-64-bit", "edit-mac"]:
        download_bundle(driver, bundle_type, platform_id, "without KNIME")
    if bundle_type != "academic":
        download_bundle(driver, bundle_type, "edit-mac", "with KNIME")


def download_bundle(driver, bundle_type, element_id, mac_version):
    driver.refresh()
    driver.find_element_by_id(element_id).click()

    if bundle_type == "academic":
        driver.find_element_by_id("edit-freemaestro-acknowledge").click()
    else:
        mac_dropdown = Select(driver.find_element_by_id("edit-mac-downloads"))
        mac_dropdown.select_by_visible_text(mac_version)

    driver.find_element_by_id("edit-eula").click()
    driver.find_element_by_id("edit-submit").click()

    #TODO: replace time.sleep() with a function that can verify
    # the download has started through scraping chrome's download tab
    time.sleep(10)
    driver.execute_script("window.history.go(-1)")


def download_files_builder(bundle_type, release):
    """
    Creates a list of all the bundles that need to be downloaded.

    :param bundle_type: bundle type given by CLI arguments
    :type bundle_type: str

    :param release: release version
    :type release: str

    :return download_files: list of all bundles to download
    :rtype download_files: list
    """

    download_files = []
    for platform in ["Linux-x86_64", "Windows-x64", "MacOSX"]:
        download_files.append(get_bundle_name(bundle_type, platform, release))
    if bundle_type != "academic":
        download_files.append(
            get_bundle_name(bundle_type, "KNIME_MacOSX", release))

    return download_files


def get_bundle_name(bundle_type, platform, release):
    """
    Constructs the bundle name

    :param platform: OS platform defined in download_files_builder()
    :type platform: str

    :return bundle_name: name of bundle
    :rtype bundle_name: str
    """
    prefix = ""
    midfix = ""
    suffix = ""

    if bundle_type == "academic":
        prefix = "Maestro"
        suffix = "_Academic"
    else:
        prefix = "Schrodinger_Suites"
        if bundle_type == "advanced":
            midfix = "_Advanced"

    if platform == "Linux-x86_64":
        ext = ".tar"
    elif platform == "Windows-x64":
        ext = ".zip"
    else:
        ext = ".dmg"

    bundle_name = f"{prefix}_20{release}{midfix}_{platform}{suffix}{ext}"

    return bundle_name


def get_ref_checksum(release, build_id, bundle):
    """
    Obtains the reference checksum of the given build_id

    :param build_id: NB build id (eg 142)
    :type build_id: str

    :return resp.text: the checksum and the path of the file it was derived from
    :rtype resp.text: str
    """
    url = f"http://build-download.schrodinger.com/NB/20{release}/build-{build_id}/{bundle}.md5"
    resp = requests.get(url, stream=True)
    resp.raise_for_status()
    return resp.text


def input_ref_checksum(prompt):
    """
    Custom input function for when -manual is selected
    If the checksum given is not in proper format, the user
    is asked to try again

    :param prompt: prompt to display when asking for checksum
    :type prompt: str

    :return checksum: checksum given by user
    :rtype checksum: str
    """
    while True:
        checksum = input(prompt)
        if len(checksum) != 32 or not checksum.isalnum():
            logger.info(f"Improper checksum format given\nPlease try again")
            continue
        else:
            break

    return checksum


def md5(fname):
    """
    Calculate the md5checksum

    :param fname: file name from which the checksum is calculated
    :type fname: str

    :return checksum: md5checksum calculated from bundles
    :rtype checksum: class `hashlib.md5`
    """
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def remove_installers(download_dir, files_to_remove):
    """
    remove all bundles in download directory

    :param download_dir: User's download directory
    :type download_dir: str

    :param list files_to_remove: name of bundles to remove
    :type list files_to_remove: list
    """
    for fname in files_to_remove:
        file_to_delete = os.path.join(download_dir, fname)
        if os.path.isfile(file_to_delete):
            os.remove(file_to_delete)


def main(*, bundle_type, release, build_id, manual):
    download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    download_files = download_files_builder(bundle_type, release)

    # Logger configuration
    date_format = '%Y-%m-%d %H:%M:%S'
    logger_format = '%(message)s'

    logger = logging.getLogger(os.path.basename(__file__))

    s_handler = logging.StreamHandler()
    f_handler = logging.FileHandler(f'{release}_dltest_report.log')
    s_handler.setLevel(logging.INFO)
    f_handler.setLevel(logging.INFO)
    logger.addHandler(s_handler)
    logger.addHandler(f_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Retrieve reference checksums depending on if -build_id or -manual is enabled
    if manual:
        checksum_references = {
            bundle: input_ref_checksum(
                f"Please enter reference checksum for {bundle}\n")
            for (bundle) in download_files
        }
    else:
        checksum_references = {
            bundle: get_ref_checksum(release, build_id, bundle)
            for (bundle) in download_files
        }

    # Remove any previous installers (of the same release) in user's download folder
    remove_installers(download_dir, download_files)

    # Set chrome settings to disable safe browsing
    chromeOptions = webdriver.ChromeOptions()
    prefs = {'safebrowsing.enabled': 'false'}
    chromeOptions.add_experimental_option("prefs", prefs)

    # Start up chrome
    try:
        driver = webdriver.Chrome(options=chromeOptions)
        driver.maximize_window()
        if bundle_type == "academic":
            driver.get(ACADEMIC_URL)
        else:
            driver.get(URL)
    except Exception as err:
        logger.info(err)
        raise Exception("Please go to https://chromedriver.chromium.org/downloads and download the proper version of chromedriver to place in your /usr/local/bin")

    # Accept cookies
    time.sleep(5)
    driver.find_element_by_id("CybotCookiebotDialogBodyButtonAccept").click()

    # Login
    user = LOGIN_CREDENTIALS[bundle_type]["user"]
    passwd = LOGIN_CREDENTIALS[bundle_type]["pass"]

    username_field = driver.find_element_by_id("edit-name")
    password_field = driver.find_element_by_id("edit-pass")
    username_field.send_keys(user)
    password_field.send_keys(passwd)
    driver.find_element_by_id("edit-submit").click()

    # Select release
    if bundle_type == "academic":
        pass
    else:
        release_dropdown = Select(driver.find_element_by_id("edit-release"))
        release_dropdown.select_by_visible_text(f"Release 20{release}")

    # Download all bundles
    download_all_bundles(driver, bundle_type, release)

    # Wait for all downloads to complete with a timeout of 2 hours
    timeout = time.time() + TIMEOUT
    for fname in download_files:
        while not os.path.exists(os.path.join(download_dir, fname)):
            time.sleep(1)
            if time.time() > timeout:
                logger.info(
                    f"{fname} download unfinished due to the timeout being met (timeout = {timeout}s) "
                )
                break

    driver.quit()

    # Calculate, compare, and report checksums
    logger.info(bundle_type.capitalize() + " md5checksums\n")
    for bundle in download_files:
        bundle_path = os.path.join(download_dir, bundle)
        bundle_checksum = md5(bundle_path)
        ref_checksum = checksum_references[bundle]
        platforms = [f"{release}_Linux", f"{release}_Windows", f"{release}_MacOSX", f"{release}_KNIME_MacOSX"]
        [logger.info(platform[5:]) for platform in platforms if platform in bundle]
        logger.info(
            f"REFERENCE: {ref_checksum}\nDOWNLOADED: {bundle_checksum} {bundle_path}"
        )

        if bundle_checksum == ref_checksum[:32]:
            logger.info("congrats, both checksums match!\n\n")
        else:
            logger.info("checksums DO NOT match\n\n")


if __name__ == '__main__':
    cmd_args = parse_args()

    main(
        bundle_type=cmd_args.bundle_type,
        release=cmd_args.release,
        build_id=cmd_args.build_id,
        manual=cmd_args.manual)
