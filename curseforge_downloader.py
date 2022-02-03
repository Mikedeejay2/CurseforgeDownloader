import json
import urllib.request
import urllib.parse
import urllib.error
import os
from pathlib import Path
from datetime import datetime
from key import api_key  # Follow instructions in readme to make this compile
from typing import List, Dict, Optional
from enum import Enum

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
    'Accept-Encoding': 'none',
    'Accept-Language': 'en-US,en;q=0.8',
    'Connection': 'keep-alive',
    'x-api-key': api_key.API_KEY  # Follow instructions in readme to make this compile
}

# Constants for Curseforge and APIs in case of change
CURSEFORGE = 'curseforge.com'
CURSEFORGE_FILES = 'https://media.forgecdn.net/files/%s/%s/%s'
CURSEFORGE_API = 'https://api.curseforge.com/v1/%s'


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

    def __query_api(self, args: str) -> json:
        api_line = 'Unknown'
        try:
            api_line = CURSEFORGE_API % args
            api_request = urllib.request.Request(api_line, headers=HEADERS)
            api_url = urllib.request.urlopen(api_request)
            api_json = json.loads(api_url.read().decode())
            return api_json
        except urllib.error.HTTPError as e:
            print('ERROR: API threw error %s: %s' % (e.code, api_line))
            return None

    def __retrieve_json_section(self, json_parent: json, section: str, search_key: str, find_value: str):
        if section not in json_parent:
            self.__log_warning('Unable to read API \"data\" value for game: %s' % find_value)
            return None
        for sub_json in json_parent['data']:
            if search_key not in sub_json:
                self.__log_warning('Unable to read API \"slug\" value for game: %s' % find_value)
                return None
            if sub_json[search_key] == find_value:
                return sub_json
        return None

    def __query_game(self, game_slug: str) -> json:
        query = self.__query_api('games')
        section = self.__retrieve_json_section(query, 'data', 'slug', game_slug)
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
        query = self.__query_api('categories?gameId=%s' % game_id)

    def __query_category_id(self, category_slug: str, game_id: int) -> int:
        if category_slug in self.cache_categories:
            return self.cache_categories[category_slug]

        category_json = self.__retrieve_json_section(query, 'data', 'slug', category_slug)
        if category_json is None:
            self.__log_warning('No category found for: %s' % category_slug)
            return -1

        if 'id' not in category_json:
            self.__log_warning('Unable to read API \"id\" value for category: %s' % category_slug)
            return -1
        category_id = category_json['id']
        self.cache_categories[category_slug] = category_id
        return category_id

    def __query_mod_id(self, game_id: id, category_id: int) -> int:
        mod_json = self.__query_api('mods/search?gameId=%s&categoryId=%s' % (game_id, category_id))
        self.__print_json(mod_json)

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

    def __download_single(self, url: str):
        url = self.__trim_url(url)
        if not self.__validate_url(url):
            return
        game_slug = self.__get_game_slug(url)
        category_slug = self.__get_category_slug(url)
        if len(game_slug) == 0 or len(category_slug) == 0:
            return -1

        game_id = self.__query_game_id(game_slug)
        if game_id < 0:
            return -1
        category_id = self.__query_category_id(category_slug, game_id)
        # mod_id = self.__query_mod_id(url, game_id, category_slug)

    #########################################################
    # PUBLIC FUNCTIONS
    #########################################################

    def download_all(self):
        for mod_url in self.__read_mods():
            self.__download_single(mod_url)
            break