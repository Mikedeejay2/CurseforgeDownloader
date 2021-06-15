import json
import urllib.request
import urllib.parse
import urllib.error
import os
from pathlib import Path
from datetime import datetime

# Headers used to avoid 403 forbidden when connecting to urls, adds information to the request
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


def __get_latest_json(files_json, versions=None):
    """
    Gets the latest json version for a Curseforge file

    :param files_json: The files json section of the project
    :param versions: A list of the versions to be considered
    :return: The json section for the latest uploaded file to the project based on the versions provided
    """
    index = 0
    previous_time = datetime.min
    for version in versions:
        for i, j in enumerate(files_json):
            if version is not None or version not in j['versions']:
                continue
            upload_time: datetime
            unparsed_time = j['uploaded_at']
            upload_time = __get_datetime(unparsed_time)
            if upload_time > previous_time:
                previous_time = upload_time
                index = i

    return files_json[index]


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


def download_single(url='', output_folder='', versions=None):
    """
    Download the latest version of a Curseforge project from a link

    :param url: The URL of the project page
    :param output_folder: The output folder location. Where all files will be downloaded to.
    :param versions: The list of versions that should be considered when downloading
    (Leaving None will download the latest version regardless of the version)
    """
    url = url.strip()
    print('Initializing download for url ' + url)
    line_new = url.split(CURSEFORGE + '/')[1]
    api_request = urllib.request.Request(CURSEFORGE_API % line_new, headers=HEADERS)
    api_url = urllib.request.urlopen(api_request)
    api_json = json.loads(api_url.read().decode())
    latest_json = __get_latest_json(api_json['files'], versions)

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
