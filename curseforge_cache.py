import sqlite3
from sqlite3 import Connection
import logger

db_name = 'cache.db'
db: Connection

TABLE_GAMES = 'Games'
TABLE_CATEGORIES = 'Categories'
TABLE_MODS = 'Mods'

ROW_ID = 'ID'
ROW_SLUG = 'Slug'


def __create_table(table_name: str):
    db.execute('''
    CREATE TABLE IF NOT EXISTS `%s`(
    `%s` INT PRIMARY KEY NOT NULL,
    `%s` CHAR(50) UNIQUE NOT NULL
    );''' % (table_name, ROW_ID, ROW_SLUG))


def connect():
    global db
    db = sqlite3.connect(db_name)
    __create_table(TABLE_GAMES)
    __create_table(TABLE_CATEGORIES)
    __create_table(TABLE_MODS)


def close():
    db.close()


def insert(table: str, id_key: int, slug: str):
    db.execute("INSERT INTO `%s` VALUES ('%s', '%s');" % (table, id_key, slug))
    db.commit()
    logger.log_info('Saved %s, %s into table %s' % (id_key, slug, table))


def get_id(table: str, slug: str) -> int:
    result = db.execute("SELECT `%s` FROM `%s` WHERE `%s`='%s';" % (ROW_ID, table, ROW_SLUG, slug))
    fetched = result.fetchone()
    if result is None or fetched is None:
        return -1
    return fetched[0]
