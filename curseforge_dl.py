import json
import urllib.request
import urllib.parse
import urllib.error
import os
from pathlib import Path
from datetime import datetime

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
    'Accept-Encoding': 'none',
    'Accept-Language': 'en-US,en;q=0.8',
    'Connection': 'keep-alive'}

# Constants for Curseforge and APIs in case of change
CURSEFORGE = 'curseforge.com'
CURSEFORGE_FILES = 'https://media.forgecdn.net/files/%s/%s/%s'
CURSEFORGE_API = 'https://api.cfwidget.com/%s'


def __get_datetime(unparsed_time=''):
    """
    Gets the datetime of an unparsed time for easy comparison

    :param unparsed_time: The unparsed time retrieved from an API
    :return: The parsed datetime
    """
    if '.' not in unparsed_time:
        return datetime.strptime(unparsed_time, '%Y-%m-%dT%H:%M:%SZ')

    return datetime.strptime(unparsed_time, '%Y-%m-%dT%H:%M:%S.%fZ')


def __versions_compat(file_json, versions=None):
    if versions is None:
        return True
    for version in versions:
        if version in file_json['versions']:
            return True
    return False


def __get_latest_json(files_json, versions=None):
    """
    Gets the latest json version for a Curseforge file

    :param files_json: The files json section of the project
    :param versions: A list of the versions to be considered
    :return: The json section for the latest uploaded file to the project based on the versions provided
    """
    json_index = 0
    previous_time = datetime.min
    for cur_index, api_json in enumerate(files_json):
        if not __versions_compat(api_json, versions):
            continue

        upload_time: datetime
        unparsed_time = api_json['uploaded_at']
        upload_time = __get_datetime(unparsed_time)
        if upload_time > previous_time:
            previous_time = upload_time
            json_index = cur_index

    return files_json[json_index]


def __get_file_url(url='', file_name=''):
    """
    Get the direct download url of a Curseforge file url

    :param url: The original Curseforge project file URL (Not direct download)
    :param file_name: The name of the file that is being downloaded
    :return: The direct download to the file
    """
    url_split = url.split('/')
    id_full = url_split[len(url_split) - 1]
    split = 4
    if len(id_full) == 6:
        split = 3
    id_part_1 = id_full[0:split]
    id_part_2 = id_full[split:len(id_full)]
    while id_part_2.startswith('0'):
        id_part_2 = id_part_2[1:len(id_part_2)]

    return CURSEFORGE_FILES % (id_part_1, id_part_2, urllib.parse.quote(file_name))


def __dl_from_file_url(output_folder='', url='', file_name=''):
    """
    Download a file from from a direct download url

    :param output_folder: The output location where the file should be downloaded to
    :param url: The URL of the file to be downloaded. This should be a direct link.
    :param file_name: The name of the file that is being downloaded
    """
    print("Downloading %s" % file_name)
    file_request = urllib.request.Request(__get_file_url(url, file_name), headers=HEADERS)
    file_url = urllib.request.urlopen(file_request)
    file = open(os.path.join(output_folder, file_name), 'wb')

    buf_size = 8192
    while True:
        buffer = file_url.read(buf_size)
        if not buffer:
            break
        file.write(buffer)

    file.close()
    print('Successfully finished download of file ' + file_name)


def __query_curseforge(url=''):
    try:
        line_new = url.split(CURSEFORGE + '/')[1]
        api_request = urllib.request.Request(CURSEFORGE_API % line_new, headers=HEADERS)
        api_url = urllib.request.urlopen(api_request)
        api_json = json.loads(api_url.read().decode())
        return api_json
    except urllib.error.HTTPError:
        print("ERROR: This URL caused an error, please check that it is valid: %s" % url)
        return


def __get_files_json(api_json):
    return api_json['files']


def download_single(url='', output_folder='', versions=None):
    """
    Download the latest version of a Curseforge project from a link

    :param url: The URL of the project page
    :param output_folder: The output folder location. Where all files will be downloaded to.
    :param versions: The list of versions that should be considered when downloading
    (Leaving None will download the latest version regardless of the version)
    """
    url = url.strip()
    api_json = __query_curseforge(url)
    print('Initializing download for ' + api_json['title'])
    files_json = __get_files_json(api_json)
    latest_json = __get_latest_json(files_json, versions)

    file_url = latest_json['url']
    file_name = latest_json['name']
    __dl_from_file_url(output_folder, file_url, file_name)


def download_all(path='', output_folder='', versions=None):
    """
    Download the latest version of all Curseforge project urls from a text document or similar

    :param path: The path to the input mods list (Text file or similar)
    :param output_folder: The output folder location. Where all files will be downloaded to.
    :param versions: The list of versions that should be considered when downloading
    (Leaving None will download the latest version regardless of the version)
    """
    mods_file = open(path, 'r')

    mods_file_lines = mods_file.readlines()
    Path(output_folder).mkdir(parents=True, exist_ok=True)

    downloaded_count = 0
    for cur_line in mods_file_lines:
        if CURSEFORGE not in cur_line:
            continue
        download_single(cur_line, output_folder, versions)
        downloaded_count += 1

    print('Successfully downloaded %s files' % downloaded_count)


def __get_all_file_names(folder=''):
    """
    Iterate through a folder and get all file names located in that folder

    :param folder: The path to the folder to be iterated through
    :return: A list of all file names
    """
    folder_dir = os.fsencode(folder)
    file_names = []
    for cur_file in os.listdir(folder_dir):
        file_name = os.fsdecode(cur_file)
        file_names.append(file_name)
    return file_names


def __check_exists_in_folder(files_json, file_names=None, versions=None):
    """
    Check whether a mod exists in a list of file names given a json file of all mod names and a list of versions to
    check for

    :param files_json: The json section for the mod
    :param file_names: The list of file names
    :param versions: A list of the versions to be considered
    :return: True if it does exist in the folder, False if not
    """
    for cur_json in files_json:
        if not __versions_compat(cur_json, versions):
            continue
        if cur_json['name'] in file_names:
            return True
    return False


def __check_needs_update(files_json, file_names=None, versions=None):
    """
    Check whether a mod needs an update based on a json file of all mod names and a list of versions to check for

    :param files_json: The json section for the mod
    :param file_names: The list of file names
    :param versions: A list of the versions to be considered
    :return: True if it needs an update, False if not
    """
    latest_json = __get_latest_json(files_json, versions)

    for cur_json in files_json:
        if not __versions_compat(cur_json, versions):
            continue
        cur_name = cur_json['name']
        if cur_name not in file_names:
            continue
        if cur_name is not latest_json['name']:
            return True
    return False


def __check_single_update(api_json, files_folder='', versions=None):
    """
    Check a single mod using its json file for an update

    :param api_json: The json from the Curseforge API for the mod
    :param files_folder: The folder from the current mods folder
    :param versions: A list of the versions to be considered
    :return:
    """
    if 'files' not in api_json:
        print('ERROR: No files key found for project %s' % (api_json['title']))
        return False

    files_json = __get_files_json(api_json)
    file_names = __get_all_file_names(files_folder)

    if len(files_json) == 0:
        print('ERROR: No files found for project %s' % (api_json['title']))
        return False

    latest_json = __get_latest_json(files_json, versions)

    for cur_json in files_json:
        if not __versions_compat(cur_json, versions):
            continue
        cur_name = cur_json['name']
        if cur_name not in file_names:
            continue
        if cur_name is not latest_json['name']:
            print('There is an update available for %s' % api_json['title'])
            print('You have %s, but the version %s is available' % (cur_name, latest_json['name']))
            return True
        else:
            print('The file is up to date for %s' % api_json['title'])
            return False
    print('Could not find an existing file for %s' % api_json['title'])
    return True


def check_single_update(url='', files_folder='', versions=None):
    """
    Check for a mod update from the mod's URL

    :param url: The URL for the mod's project page
    :param files_folder: The current mods folder
    :param versions: A list of the versions to be considered when checking for updates
    :return: True if an update is available, False if not
    """
    url = url.strip()

    api_json = __query_curseforge(url)
    return __check_single_update(api_json, files_folder, versions)


def check_for_updates(path='', files_folder='', versions=None):
    """
    Check a list of Curseforge mods for updates

    :param path: The file path to the mods text file
    :param files_folder: The current mods folder
    :param versions: A list of the versions to be considered when checking for updates
    """
    mods_file = open(path, 'r')

    mods_file_lines = mods_file.readlines()
    needs_update_count = 0
    for cur_line in mods_file_lines:
        if CURSEFORGE not in cur_line:
            continue
        needs_update = check_single_update(cur_line, files_folder, versions)
        if needs_update:
            needs_update_count += 1
    print('%s files need updates ' % needs_update_count)


def update_single(url='', files_folder='', versions=None):
    """
    Update a mod from a mod's URL

    :param url: The URL for the mod's project page
    :param files_folder: The current mods folder
    :param versions: A list of the versions to be considered when updating
    :return: True if the mod was updated, False if not
    """
    api_json = __query_curseforge(url)
    if api_json is None:
        return False

    needs_update = __check_single_update(api_json, files_folder, versions)
    if not needs_update:
        return False

    api_json = __query_curseforge(url)
    files_json = __get_files_json(api_json)

    file_names = __get_all_file_names(files_folder)

    for cur_json in files_json:
        if not __versions_compat(cur_json, versions):
            continue
        cur_name = cur_json['name']
        if cur_name not in file_names:
            continue
        print('Deleting file %s' % cur_name)
        os.remove(os.path.join(files_folder, cur_name))
        file_names = __get_all_file_names(files_folder)

    download_single(url, files_folder, versions)
    return True


def update_all(path='', files_folder='', versions=None):
    """
    Update a list of Curseforge mods

    :param path: The file path to the mods text file
    :param files_folder: The current mods folder
    :param versions: A list of the versions to be considered when updating
    """
    mods_file = open(path, 'r')

    mods_file_lines = mods_file.readlines()
    updated_count = 0
    for cur_line in mods_file_lines:
        if CURSEFORGE not in cur_line:
            continue
        updated = update_single(cur_line, files_folder, versions)
        if updated:
            updated_count += 1
    print('Updated %s files' % updated_count)
