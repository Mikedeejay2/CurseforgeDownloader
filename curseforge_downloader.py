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
import logger
import curseforge_cache

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
CFWIDGET_API = 'https://api.cfwidget.com/%s'


class CurseforgeDownloader:
    mods_path: str
    output_path: str
    versions_list: list
    excluded_versions_list: list

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

    def __print_json(self, cur_json: json) -> None:
        print(json.dumps(cur_json, indent=4, sort_keys=True))

    #########################################################
    # UTILITY FUNCTIONS
    #########################################################

    def __validate_url(self, url: str) -> bool:
        if not url.count('/') >= 3 and url.find(CURSEFORGE):
            logger.log_warning('URL could not be validated as CurseForge: %s' % url)
            return False
        return True

    def __url_subarg(self, url: str, index: int) -> str:
        split = url.split('/')  # 0:curseforge.com / 1:game-slug / 2:category-slug / 3:mod-slug
        if len(split) < index:
            logger.log_warning('Could not get URL part %s from URL: %s' % (index, url))
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

    def __query(self, api: str, args: str, params=None) -> json:
        if params is None:
            params = {}
        api_line = api % args
        api_request = requests.get(api_line, params=params, headers=HEADERS)
        if api_request.status_code == 200:
            api_json = api_request.json()
            return api_json
        logger.log_severe("Unable to parse json for API request: %s %s" % (api_line, params))

    def __query_api(self, args: str, params=None) -> json:
        return self.__query(CURSEFORGE_API, args, params)

    def __query_cfwidget(self, args: str, params=None) -> json:
        return self.__query(CFWIDGET_API, args, params)

    def __retrieve_json_section(self, json_list: json, search: Dict[str, str]):
        # if section != '' and section not in json_parent:
        #     logger.log_warning('Unable to read API \"%s\" value for: %s' % (search_key, find_value))
        #     return None
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
        query = self.__query_api('game')
        section = self.__retrieve_json_section(query, {
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
        cache_value = curseforge_cache.get_id(curseforge_cache.TABLE_GAMES, game_slug)
        if cache_value != -1:
            self.cache_games[game_slug] = cache_value
            return cache_value
        game_json = self.__query_game(game_slug)
        if 'id' not in game_json:
            logger.log_warning('Unable to read API \"id\" value for game: %s' % game_slug)
            return -1
        game_id = game_json['id']
        curseforge_cache.insert(curseforge_cache.TABLE_GAMES, game_id, game_slug)
        self.cache_games[game_slug] = game_id
        logger.log_info('Retrieved game ID via ForgeSVC: %s' % game_id)
        return game_id

    def __query_category(self, category_slug: str, game_id: int) -> json:
        query = self.__query_api('category')
        section = self.__retrieve_json_section(query, {
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
        cache_value = curseforge_cache.get_id(curseforge_cache.TABLE_CATEGORIES, category_slug)
        if cache_value != -1:
            self.cache_categories[category_slug] = cache_value
            return cache_value
        category_json = self.__query_category(category_slug, game_id)
        if 'id' not in category_json:
            logger.log_warning('Unable to read API \"id\" value for category: %s' % category_slug)
            return -1
        category_id = category_json['id']
        curseforge_cache.insert(curseforge_cache.TABLE_CATEGORIES, category_id, category_slug)
        self.cache_categories[category_slug] = category_id
        logger.log_info('Retrieved category ID via ForgeSVC: %s' % category_id)
        return category_id

    def __query_mod_search(self, info: Dict[str, Any], search: str):
        game_id = info['game_id']
        category_id = info['category_id']
        mod_slug = info['mod_slug']
        # mod_json = self.__query_api('mods/search?gameId=%s&categoryId=%s' % (game_id, category_id))
        mod_json = self.__query_api('addon/search', {
            'gameId': game_id,
            'sectionId': category_id,
            'searchFilter': search,
            # 'pageSize': 10
        })
        if mod_json is None:
            return
        for sub_json in mod_json:
            if 'slug' in sub_json and sub_json['slug'] == mod_slug:
                return sub_json
        if len(search) > 2:
            new_search = search
            if '-' in new_search:
                new_search = new_search[0:new_search.rindex('-')]
            else:
                new_search = new_search[0:len(new_search) - 1]
            return self.__query_mod_search(info, new_search)
        return None

    def __query_mod_cfwidget(self, info: Dict[str, Any]) -> json:
        result = self.__query_cfwidget('%s/%s/%s' % (info['game_slug'], info['category_slug'], info['mod_slug']))
        if result is None:
            logger.log_warning('No mod found for: %s' % info['mod_slug'])
            return None
        return result

    def __query_mod_info(self, mod_id: int) -> json:
        result = self.__query_api('addon/%s' % str(mod_id))
        if result is None:
            logger.log_severe('Unable to retrieve mod of ID from API: %s' % mod_id)
            return None
        return result

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
            mod_json = self.__query_mod_info(int(mod_id))
            if mod_json is None or 'slug' not in mod_json:
                print('The value entered is not a valid ID. Please try again.')
                continue
            if mod_json['slug'] != info['mod_slug']:
                print('The required mod \"%s\" does not match the retrieved mod \"%s\". Please enter the correct ID.' %
                      (info['slug'], mod_json['slug']))
                continue
            break
        return mod_json

    def __query_mod_id_retrieval(self, info: Dict[str, Any]) -> int:
        mod_slug = info['mod_slug']
        result = self.__query_mod_search(info, mod_slug)
        if result is not None:
            logger.log_info("Mod information retrieved via ForgeSVC API: %s" % mod_slug)
        if result is None:
            logger.log_warning('Unable to retrieve mod from ForgeSVC API, trying CFWidget API: %s' % mod_slug)
            result = self.__query_mod_cfwidget(info)
            if result is not None:
                logger.log_info("Mod information retrieved via CFWidget API: %s" % mod_slug)
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

    def __query_mod(self, info: Dict[str, Any]) -> json:
        mod_slug = info['mod_slug']
        mod_id = -1
        cache_value = curseforge_cache.get_id(curseforge_cache.TABLE_MODS, mod_slug)
        if cache_value != -1:
            mod_id = cache_value

        if mod_id == -1:
            mod_id = self.__query_mod_id_retrieval(info)
        if mod_id == -1:
            return None

        mod_json = self.__query_mod_info(mod_id)

        if mod_json is None:
            return None

        if cache_value == -1:
            curseforge_cache.insert(curseforge_cache.TABLE_MODS, mod_json['id'], mod_slug)
        return mod_json

    def __get_mod_id(self, info: Dict[str, Any]) -> int:
        mod_json = info['mod_json']
        mod_slug = info['mod_slug']
        if mod_json is None:
            return -1
        if 'id' not in mod_json:
            logger.log_severe("Mod does not contain an ID: %s" % mod_slug)
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

        mod_json = self.__query_mod(info)
        if mod_json is None:
            return {}
        info.update({'mod_json': mod_json})

        mod_id = self.__get_mod_id(info)
        if mod_id < 0:
            return {}
        info.update({'mod_id': mod_id})

        return info

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
