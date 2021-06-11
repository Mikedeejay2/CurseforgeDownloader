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


def get_file_url(files_section, versions):
    index = 0
    # print(json.dumps(files_section, indent=4, sort_keys=True))
    new_section: json
    previous_time = datetime.min
    for version in versions:
        for i, j in enumerate(files_section):
            # print(j['versions'])
            if version not in j['versions']:
                continue
            time: datetime
            time_str = j['uploaded_at']
            if '.' not in time_str:
                time = datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%SZ')
            else:
                time = datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
            if time > previous_time:
                # print('%s is greater than %s, is name of %s' % (time, previous_time, current[i]['name']))
                previous_time = time
                index = i

        # print(index)

    # print(json.dumps(files_section[index], indent=4, sort_keys=True))
    return files_section[index]


def download(output_folder='', url='', file_name=''):
    print("Downloading %s" % file_name)
    id1 = url[len(url) - 7:len(url) - 3]
    id2 = url[len(url) - 3:len(url)]
    if id2.startswith('0'):
        id2 = id2[1:len(id2)]
        if id2.startswith('0'):
            id2 = id2[1:len(id2)]
    # print(id1)
    # print(id2)
    url2 = 'https://media.forgecdn.net/files/' + id1 + '/' + id2 + '/' + urllib.parse.quote(file_name)
    request = urllib.request.Request(url2, headers=HEADERS)
    # print(url2)
    url3 = urllib.request.urlopen(request)
    file = open(os.path.join(output_folder, file_name), 'wb')

    # print(url2)

    buf_size = 8192
    while True:
        buffer = url3.read(buf_size)
        if not buffer:
            break

        file.write(buffer)
    file.close()
    print('Successfully finished download of file ' + file_name)


def download_all(path='', output_folder='', versions=None):
    mods_file = open(path, 'r')

    lines = mods_file.readlines()
    Path(output_folder).mkdir(parents=True, exist_ok=True)

    count = 0
    for line in lines:
        if 'curseforge.com' not in line:
            continue
        print('Initializing download for url ' + line.strip())
        count += 1
        line_new = line.strip().split('curseforge.com/')[1]
        url = 'https://api.cfwidget.com/' + line_new
        # print(url)
        request = urllib.request.Request(url, headers=HEADERS)
        url3 = urllib.request.urlopen(request)
        data = json.loads(url3.read().decode())
        files_section = data['files']
        selected = get_file_url(files_section, versions)

        file_url = selected['url']
        name = selected['name']
        # print(json.dumps(data, indent=4, sort_keys=True))
        download(output_folder, file_url, name)
        # print(data['download']['version'])
        # print(url2)


if __name__ == '__main__':
    download_all('test\\mods.txt', 'test\\output', versions=['1.12.2', '1.12.1', '1.12'])
