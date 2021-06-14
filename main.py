import curseforge_dl

MODS_FILE = 'test\\mods.txt'
OUTPUT_FOLDER = 'test\\output'
VERSIONS = ['1.12.2', '1.12.1', '1.12']

if __name__ == '__main__':
    curseforge_dl.download_all(MODS_FILE, OUTPUT_FOLDER, VERSIONS)
