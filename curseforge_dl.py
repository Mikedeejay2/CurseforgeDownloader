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

CURSEFORGE = 'curseforge.com'
CURSEFORGE_FILES = 'https://media.forgecdn.net/files/%s/%s/%s'
CURSEFORGE_API = 'https://api.cfwidget.com/%s'


def get_latest_json(files_section, versions):
    index = 0
    previous_time = datetime.min
    for version in versions:
        for i, j in enumerate(files_section):
            if version not in j['versions']:
                continue
            upload_time: datetime
            unparsed_time = j['uploaded_at']
            if '.' not in unparsed_time:
                upload_time = datetime.strptime(unparsed_time, '%Y-%m-%dT%H:%M:%SZ')
            else:
                upload_time = datetime.strptime(unparsed_time, '%Y-%m-%dT%H:%M:%S.%fZ')
            if upload_time > previous_time:
                previous_time = upload_time
                index = i

    return files_section[index]


def get_file_url(url='', file_name=''):
    id_part_1 = url[len(url) - 7:len(url) - 3]
    id_part_2 = url[len(url) - 3:len(url)]
    while id_part_2.startswith('0'):
        id_part_2 = id_part_2[1:len(id_part_2)]

    return CURSEFORGE_FILES % (id_part_1, id_part_2, urllib.parse.quote(file_name))


def download(output_folder='', url='', file_name=''):
    print("Downloading %s" % file_name)
    file_request = urllib.request.Request(get_file_url(url, file_name), headers=HEADERS)
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


def download_all(path='', output_folder='', versions=None):
    mods_file = open(path, 'r')

    mods_file_lines = mods_file.readlines()
    Path(output_folder).mkdir(parents=True, exist_ok=True)

    downloaded_count = 0
    for cur_line in mods_file_lines:
        if CURSEFORGE not in cur_line:
            continue
        print('Initializing download for url ' + cur_line.strip())
        line_new = cur_line.strip().split(CURSEFORGE + '/')[1]
        api_request = urllib.request.Request(CURSEFORGE_API % line_new, headers=HEADERS)
        api_url = urllib.request.urlopen(api_request)
        api_json = json.loads(api_url.read().decode())
        latest_json = get_latest_json(api_json['files'], versions)

        file_url = latest_json['url']
        name = latest_json['name']
        download(output_folder, file_url, name)
        downloaded_count += 1

    print('Successfully downloaded %s files' % downloaded_count)
