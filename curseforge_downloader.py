import json
import urllib.request
import urllib.parse
import urllib.error
import os
from pathlib import Path
from datetime import datetime
import time
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
import requests
from dotenv import load_dotenv

from curseforge_api_schemas import FileRelationType, FileStatus, FileReleaseType
import logger
import curseforge_cache

load_dotenv(os.path.join(os.getcwd(), '.env'))

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
    'Accept-Encoding': 'none',
    'Accept-Language': 'en-US,en;q=0.8',
    'Connection': 'keep-alive',
    'x-api-key': os.environ.get('ETERNAL_API_KEY')
}

# Constants for Curseforge and APIs in case of change
CURSEFORGE = 'curseforge.com'
CURSEFORGE_LINK = 'https://www.curseforge.com/%s/%s/%s'
CURSEFORGE_FILES = 'https://mediafilez.forgecdn.net/files/%s/%s/%s'
CURSEFORGE_API = 'https://api.curseforge.com/v1/%s'


class CurseForgeDownloader:
    class DownloadStatus(Enum):
        ERROR = 'Error'
        SUCCESS = 'Successful'
        IGNORED = 'Ignored'

    mods_path: str
    output_path: str
    versions_list: List[str]
    excluded_versions_list: List[str]
    release_types_list: List[FileReleaseType]

    cache_games: Dict[str, int]  # slug, id
    cache_categories: Dict[str, int]  # slug, id

    mod_urls: List[str]  # url
    mod_files: List[str]  # name

    process_results: List[Tuple[str, str]]  # url, status

    #########################################################
    # FILE FUNCTIONS
    #########################################################

    def __read_file(self, file_path: str) -> List[str]:
        file = open(file_path, 'r')
        if file is None:
            logger.log_warning('File \"%s\" could not be found!' % file_path)
            return []
        lines = file.readlines()
        file.close()
        return lines

    def __read_mods(self) -> List[str]:
        return self.__read_file(self.mods_path)

    def __get_file_datetime(self, file_path: str) -> datetime:
        modified_time = os.path.getmtime(file_path)
        return datetime.fromtimestamp(modified_time)

    def __get_file_size(self, file_path: str):
        return os.path.getsize(file_path)

    def __compile_file_time_pairs(self, dir_path: str) -> List[str]:
        result_list = []
        out_path_list = os.listdir(dir_path)
        for cur_name in out_path_list:
            result_list.append(cur_name)
        return result_list

    def __download_file(self, file_path: str, download_url: str) -> bool:
        max_attempts = 5
        for attempt in range(max_attempts):
            request = requests.get(download_url, stream=True)
            if request.status_code != 200:
                logger.log_severe('Unable to access download URL, {Try: %s/%s, Code: %s, URL: %s}' %
                                  (attempt+1, max_attempts, request.status_code, download_url))
                return False
            file = open(file_path, 'wb')
            for chunk in request.iter_content(chunk_size=8192):
                file.write(chunk)
            file.close()
            request.close()
            return True
        return False

    def __init_output_path(self):
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)

    def __write_append_file(self, file_path: str, data: str):
        file = open(file_path, 'a')
        file.write(data)
        file.close()

    def __add_mod_to_file(self, mod_url: str):
        logger.log_warning('Adding missing dependency to mods list: %s' % mod_url)
        self.__write_append_file(self.mods_path, '\n' + mod_url)

    #########################################################
    # CONSTRUCTOR FUNCTIONS
    #########################################################

    def __init__(self,
                 mods_file_path: str,
                 output_folder_path: str,
                 versions_list: List[str],
                 excluded_versions_list: List[str],
                 release_types_list: List[FileReleaseType]):
        logger.log_info('Initializing CurseForge Downloader...')
        self.mods_path = mods_file_path
        self.output_path = output_folder_path
        self.__init_output_path()
        self.versions_list = versions_list
        self.excluded_versions_list = excluded_versions_list
        self.release_types_list = release_types_list
        self.cache_games = dict()
        self.cache_categories = dict()
        self.process_results = list()
        self.mod_urls = self.__read_mods()
        self.mod_files = self.__compile_file_time_pairs(self.output_path)
        logger.log_info('Successfully initialized CurseForge Downloader.')

    #########################################################
    # UTILITY FUNCTIONS
    #########################################################

    def __print_json(self, cur_json: json) -> None:
        print(json.dumps(cur_json, indent=4, sort_keys=True))

    def __get_datetime(self, unparsed_time: str) -> datetime:
        if '.' not in unparsed_time:
            return datetime.strptime(unparsed_time, '%Y-%m-%dT%H:%M:%SZ')

        return datetime.strptime(unparsed_time, '%Y-%m-%dT%H:%M:%S.%fZ')

    def __validate_url(self, url: str) -> bool:
        if not url.count('/') >= 3 and url.find(CURSEFORGE):
            logger.log_warning('URL could not be validated as CurseForge: %s' % url)
            return False
        return True

    def __url_subarg(self, url: str, index: int) -> str:
        split = url.split('/')  # 0:curseforge.com / 1:game-slug / 2:category-slug / 3:mod-slug
        if len(split) < index:
            logger.log_warning('Could not get URL part %s from URL: %s' % (index, url))
            return str()
        return split[index].strip()

    def __get_game_slug(self, url: str) -> str:
        return self.__url_subarg(url, 1)

    def __get_category_slug(self, url: str) -> str:
        return self.__url_subarg(url, 2)

    def __get_mod_slug(self, url: str) -> str:
        return self.__url_subarg(url, 3)

    def __trim_url(self, url: str):
        return url.replace('https://', '').strip()

    def __version_compat(self, file_json: json, releases: List[FileReleaseType]) -> bool:
        if 'gameVersions' not in file_json:
            return False
        if 'releaseType' not in file_json:
            return False
        file_status = file_json['releaseType']
        release_type = FileReleaseType(file_status)
        if release_type not in releases:
            return False

        game_versions = file_json['gameVersions']
        result = False
        for game_version in game_versions:
            if game_version in self.versions_list:
                result = True
            elif game_version in self.excluded_versions_list:
                result = False
                break
        return result

    def __strip_str(self, string: str) -> str:
        return string.lower().replace(' ', '').replace('-', '').replace('.', '')

    def __get_list_values(self, input_json: json, find_value: str) -> List[str]:
        output_list = list()
        for cur_json in input_json:
            output_list.append(cur_json[find_value])
        return output_list

    def __get_time_difference(self, time1: datetime, time2: datetime) -> Tuple[int, int]:
        time_difference = (time2 - time1)
        total_seconds = time_difference.total_seconds()
        minutes = int(total_seconds / 60)
        seconds = int(total_seconds % 60)
        return minutes, seconds

    #########################################################
    # QUERY FUNCTIONS
    #########################################################

    def __query(self, api: str, args: str, params=None) -> json:
        max_attempts = 5
        for attempt in range(max_attempts):
            if params is None:
                params = {}
            api_line = api % args
            api_request = requests.get(api_line, params=params, headers=HEADERS)
            if api_request.status_code == 200:
                api_json = api_request.json()
                logger.log_info('Query successfully completed')
                api_request.close()
                return api_json
            logger.log_severe('Unable to parse json for API request, {Try: %s/%s, Code: %s, URL: %s, Parameters: %s}' %
                              (attempt+1, max_attempts, api_request.status_code, api_line, params))
            api_request.close()
        logger.log_info('Query failed')

    def __query_api(self, args: str, params=None) -> json:
        logger.log_info('Querying Eternal API: %s' % args)
        return self.__query(CURSEFORGE_API, args, params)

    def __retrieve_json_section(self, json_list: json, search: Dict[str, str]):
        for sub_json in json_list:
            flag = True
            for key, value in search.items():
                if key not in sub_json:
                    logger.log_warning('Unable to read API \"%s\" value for: %s' % (key, value))
                    return None
                if sub_json[key] != value:
                    flag = False
                    break
            if flag:
                return sub_json

        return None

    def __query_game(self, game_slug: str) -> json:
        query = self.__query_api('games')
        section = self.__retrieve_json_section(query['data'], {
            'slug': game_slug
        })
        if section is None:
            logger.log_warning('No game found for: %s' % game_slug)
            return None
        return section

    def __query_game_id(self, info: Dict[str, Any]) -> int:
        game_slug = info['game_slug']
        if game_slug in self.cache_games:
            return self.cache_games[game_slug]
        cache_value = curseforge_cache.get_game_id(game_slug)
        if cache_value is not None:
            self.cache_games[game_slug] = cache_value
            return cache_value
        game_json = self.__query_game(game_slug)
        if 'id' not in game_json:
            logger.log_warning('Unable to read API \"id\" value for game: %s' % game_slug)
            return -1
        game_id = game_json['id']
        game_name = game_json['name']
        curseforge_cache.add_game(game_id, game_slug, game_name)
        self.cache_games[game_slug] = game_id
        logger.log_info('Retrieved game ID via Eternal: %s' % game_id)
        return game_id

    def __query_category(self, category_slug: str, game_id: int) -> json:
        query = self.__query_api('categories', {'gameId': game_id})
        section = self.__retrieve_json_section(query['data'], {
            'slug': category_slug,
            'gameId': game_id
        })
        if section is None:
            logger.log_warning('No category found for: %s' % category_slug)
            return None
        return section

    def __query_category_id(self, info: Dict[str, Any]) -> int:
        category_slug = info['category_slug']
        game_id = info['game_id']
        if category_slug in self.cache_categories:
            return self.cache_categories[category_slug]
        cache_value = curseforge_cache.get_category_id(category_slug)
        if cache_value is not None:
            self.cache_categories[category_slug] = cache_value
            return cache_value
        category_json = self.__query_category(category_slug, game_id)
        if 'id' not in category_json:
            logger.log_warning('Unable to read API \"id\" value for category: %s' % category_slug)
            return -1
        category_id = category_json['id']
        category_name = category_json['name']
        curseforge_cache.add_category(category_id, category_slug, category_name)
        self.cache_categories[category_slug] = category_id
        logger.log_info('Retrieved category ID via Eternal: %s' % category_id)
        return category_id

    def __query_mod_search(self, info: Dict[str, Any]):
        game_id = info['game_id']
        category_id = info['category_id']
        mod_slug = info['mod_slug']
        mod_json = self.__query_api('mods/search', {
            'gameId': game_id,
            'classId': category_id,
            'slug': mod_slug,
            'pageSize': 50,
            'index': 0
        })
        if mod_json is None:
            return
        for sub_json in mod_json['data']:
            if 'slug' in sub_json and sub_json['slug'] == mod_slug:
                return sub_json
        return None

    def __query_mod_json(self, mod_id: int) -> json:
        result = self.__query_api('mods/%s' % str(mod_id))
        if result is None:
            logger.log_severe('Unable to retrieve mod of ID from API: %s' % mod_id)
            return None
        return result['data']

    def __query_mod_manual(self, info: Dict[str, Any]) -> json:
        mod_json = None
        while True:
            mod_id = input("Mod ID: ")
            if mod_id.lower() == 'exit':
                logger.log_severe('Skipping mod due to denial of manual user input: %s' % info['mod_slug'])
                break
            if not mod_id.isdigit():
                print('The value entered is not a valid ID. Please try again.')
                continue
            mod_json = self.__query_mod_json(int(mod_id))
            if mod_json is None or 'slug' not in mod_json:
                print('The value entered is not a valid ID. Please try again.')
                continue
            if mod_json['slug'] != info['mod_slug']:
                print('The required mod \"%s\" does not match the retrieved mod \"%s\". Please enter the correct ID.' %
                      (info['mod_slug'], mod_json['slug']))
                continue
            break
        return mod_json

    def __query_mod_id_retrieval(self, info: Dict[str, Any]) -> int:
        mod_slug = info['mod_slug']
        result = self.__query_mod_search(info)
        if result is not None:
            logger.log_info("Mod information retrieved via Eternal API: %s" % mod_slug)
        if result is None:
            print('Unable to get mod \"%s\" through URL provided, please paste the ID of the mod from the mod URL: %s' %
                  (info['mod_slug'], info['url']))
            result = self.__query_mod_manual(info)
            if result is not None:
                logger.log_info("Mod information retrieved via manual user input: %s" % mod_slug)

        if 'id' not in result:
            logger.log_severe('Unable to retrieve mod ID; attempted all available methods: %s' % mod_slug)
            return -1
        return result['id']

    def __query_mod_id(self, info: Dict[str, Any]) -> int:
        mod_slug = info['mod_slug']
        mod_id = -1
        cache_value = curseforge_cache.get_mod_id(mod_slug)
        if cache_value is not None:
            return cache_value

        if mod_id == -1:
            mod_id = self.__query_mod_id_retrieval(info)
        if mod_id == -1:
            return -1

        mod_json = self.__query_mod_json(mod_id)

        if mod_json is None:
            return -1

        if 'id' not in mod_json:
            logger.log_severe('Mod does not contain an ID: %s' % mod_slug)
            return -1

        mod_id = mod_json['id']
        mod_name = mod_json['name']
        if cache_value is None:
            curseforge_cache.add_mod(mod_id, mod_slug, mod_name)
        return mod_id

    def __query_mod_files(self, info: Dict[str, Any]) -> json:
        result = []
        for i in range(0, 10000, 50):
            cur_result = self.__query_api('mods/%s/files' % info['mod_id'], {'index': i})
            if len(cur_result['data']) == 0:
                break
            result.extend(cur_result['data'])
        if len(result) == 0:
            logger.log_severe('Unable to retrieve mod files')
        return result

    def __query_mod_name(self, info) -> str:
        return curseforge_cache.get_mod_name(info['mod_slug'])

    def __query_dependency_slug(self, info: Dict[str, Any], dependency_json: json) -> str:
        dependency_id = dependency_json['modId']

        mod_slug = curseforge_cache.get_mod_slug(dependency_id)
        if mod_slug is None:
            dependency_json = self.__query_mod_json(dependency_id)
            if dependency_json is None:
                return str()
            if 'slug' not in dependency_json:
                logger.log_warning('Could not obtain slug of dependency for mod: %s' % info['mod_name'])
                return str()
            mod_slug = dependency_json['slug']
        return mod_slug

    #########################################################
    # INTERMEDIARY FUNCTIONS
    #########################################################

    def __get_latest_file(self, info: Dict[str, Any], releases: List[FileReleaseType]) -> json:
        files_json = info['files_json']
        latest = datetime.min
        latest_json = None
        for cur_json in files_json:
            if not self.__version_compat(cur_json, releases[0:1]):
                continue
            if 'fileDate' not in cur_json:
                continue
            file_date = self.__get_datetime(cur_json['fileDate'])
            if file_date > latest:
                latest = file_date
                latest_json = cur_json

        # If there are no non-release type specific files, check for all release types
        if len(releases) != 0 and latest_json is None:
            return self.__get_latest_file(info, releases[1:])

        return latest_json

    def __filter_files_json(self, info: Dict[str, Any], files_json: json) -> json:
        new_json = []
        for cur_json in files_json:
            if not self.__version_compat(cur_json, self.release_types_list):
                continue
            new_json.append(cur_json)
        return new_json

    def __get_common_name(self, info: Dict[str, Any]) -> str:
        # Use unfiltered files json just in case user has mod of different version installed
        file_names = info['unfiltered_file_names']
        common_name = self.__strip_str(file_names[0])
        for cur_name in file_names:
            cur_name = self.__strip_str(cur_name)
            new_common = ''
            for index in range(len(cur_name)):
                char_cur = cur_name[index]
                if index >= len(common_name):
                    break
                char_com = common_name[index]

                if char_cur != char_com:
                    break
                new_common += char_cur
            common_name = new_common
        return common_name

    def __filter_by_common_name(self, info: Dict[str, Any]) -> List[str]:
        files_list = list()
        common_name = self.__get_common_name(info)
        if len(common_name) == 0:
            return self.mod_files

        # sort with common name
        for file_name in self.mod_files:
            stripped_name = self.__strip_str(file_name)
            if not stripped_name.startswith(common_name):
                continue
            files_list.append(file_name)
        return files_list

    def __filter_by_compare_name(self, info: Dict[str, Any], files_list: List[str]) -> List[str]:
        file_names = info['unfiltered_file_names']
        new_names = list()
        for file_name in files_list:
            if file_name in file_names:
                new_names.append(file_name)
        return new_names

    def __get_filtered_files(self, info: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        files_list = self.__filter_by_common_name(info)
        # even if one file is found be absolutely sure that it's an official mod file
        files_list = self.__filter_by_compare_name(info, files_list)

        files_dict = {}
        for file_name in files_list:
            file_path = os.path.join(self.output_path, file_name)
            file_time = self.__get_file_datetime(file_path)
            file_size = self.__get_file_size(file_path)
            files_dict.update({file_name: {'time': file_time, 'size': file_size}})
        return files_dict

    def __check_name_overlap(self, info: Dict[str, Any]) -> bool:
        files_json = info['files_json']
        files_list = info['file_names']

        test_set = set()
        for file_name in files_list:
            if file_name in test_set:
                return True
            test_set.add(file_name)

        return False

    def __check_needs_update_normal(self, info: Dict[str, Any]) -> bool:
        latest_json = info['latest_json']
        existing_files = info['existing_files']
        latest_name = latest_json['fileName']
        existing_name = list(existing_files.keys())[0]
        return existing_name != latest_name

    def __check_needs_update_special(self, info: Dict[str, Any]) -> bool:
        latest_json = info['latest_json']
        existing_files = info['existing_files']
        existing_files: dict
        existing_tuple = list(existing_files.values())[0]
        latest_datetime = info['latest_datetime']
        existing_datetime = existing_tuple['time']

        # Compare times, if downloaded file is modified before the date of the latest upload, return true
        if existing_datetime < latest_datetime:
            return True

        # Compare the file sizes, if sizes are different, expect outdated.
        # There is an extreme edge case here that both the current file and latest file have the exact same
        # file size but are different versions. This is fixable, but it would take even more iterating.
        latest_size = latest_json['fileLength']
        existing_size = existing_tuple['size']
        return latest_size != existing_size

    def __check_needs_update(self, info: Dict[str, Any]) -> bool:
        existing_files = info['existing_files']
        if len(existing_files) > 1:
            logger.log_warning('More than one version of mod \"%s\" was located in the output folder: %s' %
                               (info['mod_name'], list(existing_files.keys())))
            return True
        if len(existing_files) == 0:
            return True

        file_names_overlap = self.__check_name_overlap(info)
        if file_names_overlap:
            return self.__check_needs_update_special(info)
        return self.__check_needs_update_normal(info)

    def __remove_old_files(self, info: Dict[str, Any]):
        existing_files = info['existing_files']
        for file_name in existing_files:
            file_path = os.path.join(self.output_path, file_name)
            logger.log_info('Removing old file: %s' % file_name)
            os.remove(file_path)

    def __download_mod_file(self, info: Dict[str, Any]):
        latest_json = info['latest_json']
        file_name = latest_json['fileName']
        download_url = latest_json['downloadUrl']
        if download_url is None:
            download_url = CURSEFORGE_FILES % (str(latest_json['id'])[:4], str(latest_json['id'])[4:], file_name)
        logger.log_info('Starting download of mod: %s %s' % (info['mod_name'], file_name))
        self.__download_file(os.path.join(self.output_path, file_name), download_url)
        logger.log_info('Download finished successfully')

    def __get_dependency_url(self, info: Dict[str, Any], dependency_slug: str) -> str:
        return CURSEFORGE_LINK % (info['game_slug'], info['category_slug'], dependency_slug)

    def __check_dependencies(self, info: Dict[str, Any]):
        latest_json = info['latest_json']
        if 'dependencies' not in latest_json or len(latest_json['dependencies']) == 0:
            logger.log_info('The mod \"%s\" has no dependencies that need to be downloaded' % info['mod_name'])
            return True
        dependencies_list = latest_json['dependencies']
        for dependency in dependencies_list:
            if 'modId' not in dependency or 'relationType' not in dependency:
                logger.log_warning('Dependency for \"%s\" could not be read properly' % info['mod_name'])
                continue
            dependency_type = dependency['relationType']
            if dependency_type != FileRelationType.REQUIRED_DEPENDENCY.value:
                continue
            dependency_slug = self.__query_dependency_slug(info, dependency)
            if len(dependency_slug) == 0:
                continue

            dependency_url = self.__get_dependency_url(info, dependency_slug)
            dependency_url_s = self.__trim_url(dependency_url)
            found = False
            for mod_url in self.mod_urls:
                mod_url_s = self.__trim_url(mod_url)
                if dependency_url_s == mod_url_s:
                    found = True
                    break
            if found:
                logger.log_info('Dependency \"%s\" for mod \"%s\" is already in the downloads list' %
                                (dependency_slug, info['mod_name']))
                continue
            self.__add_mod_to_file(dependency_url)
            self.mod_urls.append(dependency_url)


    def __get_mod_preinfo(self, url: str) -> Dict[str, Any]:
        url = self.__trim_url(url)
        if not self.__validate_url(url):
            return {}
        game_slug = self.__get_game_slug(url)
        category_slug = self.__get_category_slug(url)
        mod_slug = self.__get_mod_slug(url)
        if len(game_slug) == 0 or len(category_slug) == 0:
            return {}
        return {
            'url': url,
            'game_slug': game_slug,
            'category_slug': category_slug,
            'mod_slug': mod_slug,
        }

    def __get_mod_info(self, url: str) -> Dict[str, Any]:
        info = self.__get_mod_preinfo(url)

        game_id = self.__query_game_id(info)
        if game_id < 0:
            return {}
        info.update({'game_id': game_id})

        category_id = self.__query_category_id(info)
        if category_id < 0:
            return {}
        info.update({'category_id': category_id})

        mod_id = self.__query_mod_id(info)
        if mod_id < 0:
            return {}
        info.update({'mod_id': mod_id})

        mod_name = self.__query_mod_name(info)
        if mod_name is None:
            return {}
        info.update({'mod_name': mod_name})

        unfiltered_files_json = self.__query_mod_files(info)
        if unfiltered_files_json is None:
            return {}
        info.update({'unfiltered_files_json': unfiltered_files_json})
        files_json = self.__filter_files_json(info, unfiltered_files_json)
        info.update({'files_json': files_json})

        latest_json = self.__get_latest_file(info, self.release_types_list)
        if latest_json is None:
            return {}
        info.update({'latest_json': latest_json})

        latest_datetime = self.__get_datetime(latest_json['fileDate'])
        info.update({'latest_datetime': latest_datetime})

        unfiltered_file_names = self.__get_list_values(unfiltered_files_json, 'fileName')
        info.update({'unfiltered_file_names': unfiltered_file_names})

        file_names = self.__get_list_values(files_json, 'fileName')
        info.update({'file_names': file_names})

        existing_files = self.__get_filtered_files(info)
        info.update({'existing_files': existing_files})

        return info

    def __check_for_updates(self, info: Dict[str, Any]) -> bool:
        needs_update = self.__check_needs_update(info)
        mod_name = info['mod_name']
        if not needs_update:
            logger.log_info('The latest version of mod \"%s\" is already downloaded' % mod_name)
            return False

        logger.log_info('The mod \"%s\" has an update available.' % mod_name)
        return True

    def __download_single(self, url: str) -> DownloadStatus:
        info = self.__get_mod_info(url)
        if len(info) == 0:
            return self.DownloadStatus.ERROR

        self.__check_dependencies(info)

        needs_update = self.__check_for_updates(info)
        if not needs_update:
            return self.DownloadStatus.IGNORED

        self.__remove_old_files(info)
        self.__download_mod_file(info)

        return self.DownloadStatus.SUCCESS

    def __print_results(self, time_difference: Tuple[int, int]):
        total_success = 0
        total_counts = dict()
        for category in self.DownloadStatus:
            total_counts[category.value] = 0

        print('\n---------------------------------')
        print('Detailed results:')
        for mod_url, result in self.process_results:
            total_counts[result] = int(total_counts[result]) + 1
            if result == self.DownloadStatus.SUCCESS.value or \
               result == self.DownloadStatus.IGNORED.value:
                total_success += 1
            print('%s: %s' % (result, mod_url.strip()))

        print('\n---------------------------------')
        print('Error log:')
        errors_found = False
        for entry in logger.history:
            level = entry[0]
            text = entry[1]
            if level == logger.LogLevel.INFO:
                continue
            errors_found = True
            print('%s: %s' % (level.value, text))
        if not errors_found:
            print('Script executed with no errors')

        print('\n---------------------------------')
        print('Overview results:')
        for category, count in total_counts.items():
            print('%s: %s' % (category, count))
        print('Total successful: %s/%s' % (total_success, len(self.process_results)))
        print('Total time taken: %s minutes, %s seconds' % (time_difference[0], time_difference[1]))

    #########################################################
    # PUBLIC FUNCTIONS
    #########################################################

    def download_all(self):
        pre_time = datetime.now()

        for mod_url in self.mod_urls:
            result = self.__download_single(mod_url)
            self.process_results.append((mod_url, result.value))
        logger.log_info('Finished downloading all mods')
        post_time = datetime.now()

        self.__print_results(self.__get_time_difference(pre_time, post_time))
