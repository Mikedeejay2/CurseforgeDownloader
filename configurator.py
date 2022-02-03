import curseforge_dl
import configparser

SECTION_DIRECTORIES = 'Directories'
KEY_MODS_FILE = 'ModsFile'
KEY_OUTPUT_FOLDER = 'OutputFolder'

SECTION_FILTERS = 'Filters'
KEY_VERSIONS = 'Versions'
KEY_EXCLUDED_VERSIONS = 'ExcludedVersions'

SECTION_EXECUTION = 'Execution'
KEY = 'ExecutionType'


def read_config(path=None):
    if path is None:
        print('Path to properties file has not been set in code')
        return
    config = configparser.ConfigParser()
    config.read(path)

