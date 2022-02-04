import json
import urllib.request
import urllib.parse
import urllib.error
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from enum import Enum
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
    'Accept-Encoding': 'none',
    'Accept-Language': 'en-US,en;q=0.8',
    'Connection': 'keep-alive'
}

# Constants for Curseforge and APIs in case of change
CURSEFORGE = 'curseforge.com'
CURSEFORGE_FILES = 'https://media.forgecdn.net/files/%s/%s/%s'
CURSEFORGE_API = 'https://addons-ecs.forgesvc.net/api/v2/%s'


class LogLevel(Enum):
    INFO = 'INFO'
    WARNING = 'WARN'
    SEVERE = 'ERR'


class CurseforgeDownloader:
    mods_path: str
    output_path: str
    versions_list: list
    excluded_versions_list: list

    output_log: Dict[LogLevel, List[str]]

    cache_games: Dict[str, int]  # slug, id
    cache_categories: Dict[str, int]  # slug, id

    def __init__(self, mods_file_path: str, output_folder_path: str, versions_list: list, excluded_versions_list: list):
        self.mods_path = mods_file_path
        self.output_path = output_folder_path
        self.versions_list = versions_list
        self.excluded_versions_list = excluded_versions_list
        self.output_log = {}
        self.cache_games = {}
        self.cache_categories = {}
        for level in LogLevel:
            self.output_log[level] = []

    def __print_json(self, cur_json: json) -> None:
        print(json.dumps(cur_json, indent=4, sort_keys=True))

    #########################################################
    # LOGGING FUNCTIONS
    #########################################################

    def __log(self, text: str, level: LogLevel):
        print(level.value + ': ' + text)
        self.output_log[level].append(text)

    def __log_info(self, text: str):
        self.__log(text, LogLevel.INFO)

    def __log_warning(self, text: str):
        self.__log(text, LogLevel.WARNING)

    def __log_severe(self, text: str):
        self.__log(text, LogLevel.SEVERE)

    #########################################################
    # UTILITY FUNCTIONS
    #########################################################

    def __validate_url(self, url: str) -> bool:
        if not url.count('/') >= 3 and url.find(CURSEFORGE):
            self.__log_warning('URL could not be validated as CurseForge: %s' % url)
            return False
        return True

    def __url_subarg(self, url: str, index: int) -> str:
        split = url.split('/')  # 0:curseforge.com / 1:game-slug / 2:category-slug / 3:mod-slug
        if len(split) < index:
            self.__log_warning('Could not get URL part %s from URL: %s' % (index, url))
            return ''
        return split[index].strip()

    def __get_game_slug(self, url: str) -> str:
        return self.__url_subarg(url, 1)

    def __get_category_slug(self, url: str) -> str:
        return self.__url_subarg(url, 2)

    def __get_mod_slug(self, url: str) -> str:
        return self.__url_subarg(url, 3)

    def __trim_url(self, url: str):
        return url.replace('https://', '').strip()

    #########################################################
    # QUERY FUNCTIONS
    #########################################################

    def __query_api(self, args: str, params=None) -> json:
        if params is None:
            params = {}
        api_line = 'Unknown'
        try:
            api_line = CURSEFORGE_API % args
            api_request = requests.get(api_line, params=params, headers=HEADERS)
            if api_request.status_code == 200:
                api_json = api_request.json()
                return api_json
            self.__log_severe("Unable to parse json for API request: %s" % api_line)
        except urllib.error.HTTPError as e:
            self.__log_severe('API threw error %s: %s' % (e.code, api_line))
            return None

    def __retrieve_json_section(self, json_list: json, search: Dict[str, str]):
        # if section != '' and section not in json_parent:
        #     self.__log_warning('Unable to read API \"%s\" value for: %s' % (search_key, find_value))
        #     return None
        for sub_json in json_list:
            flag = True
            for key, value in search.items():
                if key not in sub_json:
                    self.__log_warning('Unable to read API \"%s\" value for: %s' % (key, value))
                    return None
                if sub_json[key] != value:
                    flag = False
                    break
            if flag:
                return sub_json

        return None

    def __query_game(self, game_slug: str) -> json:
        query = self.__query_api('game')
        section = self.__retrieve_json_section(query, {
            'slug': game_slug
        })
        if section is None:
            self.__log_warning('No game found for: %s' % game_slug)
            return None
        return section

    def __query_game_id(self, game_slug: str) -> int:
        if game_slug in self.cache_games:
            return self.cache_games[game_slug]
        game_json = self.__query_game(game_slug)
        if 'id' not in game_json:
            self.__log_warning('Unable to read API \"id\" value for game: %s' % game_slug)
            return -1
        game_id = game_json['id']
        self.cache_games[game_slug] = game_id
        return game_id

    def __query_category(self, category_slug: str, game_id: int) -> json:
        query = self.__query_api('category')
        section = self.__retrieve_json_section(query, {
            'slug': category_slug,
            'gameId': game_id
        })
        if section is None:
            self.__log_warning('No game found for: %s' % category_slug)
            return None
        return section

    def __query_category_id(self, category_slug: str, game_id: int) -> int:
        if category_slug in self.cache_categories:
            return self.cache_categories[category_slug]

        category_json = self.__query_category(category_slug, game_id)
        if 'id' not in category_json:
            self.__log_warning('Unable to read API \"id\" value for category: %s' % category_slug)
            return -1
        category_id = category_json['id']
        self.cache_categories[category_slug] = category_id
        return category_id

    def __query_mod_recur(self, game_id: int, section_id: int, mod_slug: str, search: str):
        # mod_json = self.__query_api('mods/search?gameId=%s&categoryId=%s' % (game_id, category_id))
        mod_json = self.__query_api('addon/search', {
            'gameId': game_id,
            'sectionId': section_id,
            'searchFilter': search,
            # 'pageSize': 10
        })
        for sub_json in mod_json:
            if 'slug' in sub_json and sub_json['slug'] == mod_slug:
                return sub_json
        print(search)
        if len(search) > 2:
            new_search = search
            if '-' in new_search:
                new_search = new_search[0:new_search.rindex('-')]
            else:
                new_search = new_search[0:len(new_search) - 1]
            return self.__query_mod_recur(game_id, section_id, mod_slug, new_search)
        self.__log_severe("Unable to find mod of name slug: %s     Consider providing project ID instead" % mod_slug)
        return None

    def __query_mod(self, game_id: int, section_id: int, mod_slug: str) -> json:
        return self.__query_mod_recur(game_id, section_id, mod_slug, mod_slug)

    def __get_mod_id(self, mod_json: json, mod_slug: str) -> int:
        if mod_json is None:
            return -1
        if 'id' not in mod_json:
            self.__log_severe("Mod does not contain an ID: %s" % mod_slug)
            return -1
        return mod_json['id']

    #########################################################
    # FILE FUNCTIONS
    #########################################################

    def __read_file(self, file_path: str) -> List[str]:
        file = open(file_path, 'r')
        if file is None:
            print('File \"%s\" could not be found!' % file_path)
            return []
        return file.readlines()

    def __read_mods(self) -> List[str]:
        return self.__read_file(self.mods_path)

    #########################################################
    # INTERMEDIARY FUNCTIONS
    #########################################################

    def __get_mod_info(self, url: str) -> Dict[str, Any]:
        url = self.__trim_url(url)
        if not self.__validate_url(url):
            return {}
        game_slug = self.__get_game_slug(url)
        category_slug = self.__get_category_slug(url)
        mod_slug = self.__get_mod_slug(url)
        if len(game_slug) == 0 or len(category_slug) == 0:
            return {}

        game_id = self.__query_game_id(game_slug)
        if game_id < 0:
            return {}
        category_id = self.__query_category_id(category_slug, game_id)
        if category_id < 0:
            return {}
        mod_json = self.__query_mod(game_id, category_id, mod_slug)
        if mod_json is None:
            return {}
        mod_id = self.__get_mod_id(mod_json, mod_slug)
        if mod_id < 0:
            return {}

        return {
            'game_slug': game_slug,
            'category_slug': category_slug,
            'mod_slug': mod_slug,
            'game_id': game_id,
            'category_id': category_id,
            'mod_json': mod_json,
            'mod_id': mod_id,
        }

    def __download_single(self, url: str):
        info = self.__get_mod_info(url)
        if len(info) == 0:
            return

    #########################################################
    # PUBLIC FUNCTIONS
    #########################################################

    def download_all(self):
        for mod_url in self.__read_mods():
            self.__download_single(mod_url)
