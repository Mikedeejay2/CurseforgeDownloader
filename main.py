import os
from os import path
from dotenv import load_dotenv
from curseforge_downloader import CurseForgeDownloader
import curseforge_cache
from curseforge_api_schemas import FileReleaseType

# Change these values here:
# The path to the input mods list (Text file or similar)
MODS_FILE = 'run\\mods.txt'
# The output folder location. Where all files will be downloaded to.
OUTPUT_FOLDER = 'run\\output'
# The list of versions that should be considered when downloading
VERSIONS = ['1.16', '1.16.1', '1.16.2', '1.16.3', '1.16.4', '1.16.5']
# The list of versions that should be excluded when downloading
EXCLUDED = ['Fabric']
# The list of release types that should be considered when downloading
RELEASE_TYPES = [FileReleaseType.RELEASE, FileReleaseType.BETA, FileReleaseType.ALPHA]

if __name__ == '__main__':
    curseforge_cache.connect()
    downloader = CurseForgeDownloader(MODS_FILE, OUTPUT_FOLDER, VERSIONS, EXCLUDED, RELEASE_TYPES)
    downloader.download_all()
    curseforge_cache.close()
