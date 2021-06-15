import curseforge_dl

# Change these values here:
# The path to the input mods list (Text file or similar)
MODS_FILE = 'test\\mods.txt'
# The output folder location. Where all files will be downloaded to.
OUTPUT_FOLDER = 'test\\output'
# The list of versions that should be considered when downloading
VERSIONS = ['1.12.2', '1.12.1', '1.12']

if __name__ == '__main__':
    # curseforge_dl.download_all(MODS_FILE, OUTPUT_FOLDER, VERSIONS)
    curseforge_dl.check_for_updates(MODS_FILE, OUTPUT_FOLDER, VERSIONS)
    # curseforge_dl.update_all(MODS_FILE, OUTPUT_FOLDER, VERSIONS)
