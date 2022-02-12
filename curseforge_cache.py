import sqlite3
from sqlite3 import Connection
from typing import Any

import logger

db_name = 'cache.db'
db: Connection

TABLE_GAMES = 'Games'
TABLE_CATEGORIES = 'Categories'
TABLE_MODS = 'Mods'

ROW_ID = 'ID'
ROW_SLUG = 'Slug'
ROW_NAME = 'Name'


def __create_table(table_name: str):
    db.execute('''
    CREATE TABLE IF NOT EXISTS `%s`(
    `%s` INT PRIMARY KEY NOT NULL,
    `%s` CHAR(50) UNIQUE NOT NULL,
    `%s` CHAR(50) UNIQUE NOT NULL
    );''' % (table_name, ROW_ID, ROW_SLUG, ROW_NAME))


def connect():
    global db
    db = sqlite3.connect(db_name)
    __create_table(TABLE_GAMES)
    __create_table(TABLE_CATEGORIES)
    __create_table(TABLE_MODS)
    logger.log_info('(Cache) Connected to cache database successfully')


def close():
    db.close()


def insert(table: str, id_key: int, slug: str, name: str):
    name = name.replace('\'', '\'\'')
    db.execute("INSERT INTO `%s` VALUES ('%s', '%s', '%s');" % (table, id_key, slug, name))
    db.commit()
    logger.log_info('(Cache) Saved %s, %s into table %s' % (id_key, slug, table))


def select(table: str, row: str, slug: str, selecting_row: str) -> Any:
    result = db.execute("SELECT `%s` FROM `%s` WHERE `%s`='%s';" % (row, table, selecting_row, slug))
    fetched = result.fetchone()
    if result is None or fetched is None:
        return None
    logger.log_info('(Cache) Retrieved %s %s of \"%s\" via cache: %s' % (table, row, slug, fetched[0]))
    return fetched[0]


def get_game_id(slug: str):
    return select(TABLE_GAMES, ROW_ID, slug, ROW_SLUG)


def get_game_name(slug: str):
    return select(TABLE_GAMES, ROW_NAME, slug, ROW_SLUG)


def get_category_id(slug: str):
    return select(TABLE_CATEGORIES, ROW_ID, slug, ROW_SLUG)


def get_category_name(slug: str):
    return select(TABLE_CATEGORIES, ROW_NAME, slug, ROW_SLUG)


def get_mod_id(slug: str):
    return select(TABLE_MODS, ROW_ID, slug, ROW_SLUG)


def get_mod_name(slug: str):
    return select(TABLE_MODS, ROW_NAME, slug, ROW_SLUG)


def get_game_slug(game_id: str):
    return select(TABLE_GAMES, ROW_SLUG, game_id, ROW_ID)


def get_category_slug(category_id: str):
    return select(TABLE_CATEGORIES, ROW_SLUG, category_id, ROW_ID)


def get_mod_slug(mod_id: str):
    return select(TABLE_MODS, ROW_SLUG, mod_id, ROW_ID)


def add_game(id_key: int, slug: str, name: str):
    insert(TABLE_GAMES, id_key, slug, name)


def add_category(id_key: int, slug: str, name: str):
    insert(TABLE_CATEGORIES, id_key, slug, name)


def add_mod(id_key: int, slug: str, name: str):
    insert(TABLE_MODS, id_key, slug, name)
