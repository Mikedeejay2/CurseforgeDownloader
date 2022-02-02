import curseforge_dl

# Change these values here:
# The path to the input mods list (Text file or similar)
MODS_FILE = 'run\\mods.txt'
# The output folder location. Where all files will be downloaded to.
OUTPUT_FOLDER = 'run\\output'
# The list of versions that should be considered when downloading
VERSIONS = ['1.16', '1.16.1', '1.16.2', '1.16.3', '1.16.4', '1.16.5']
# The list of versions that should be excluded when downloading
EXCLUDED = ['Fabric']

if __name__ == '__main__':
    curseforge_dl.download_all(MODS_FILE, OUTPUT_FOLDER, VERSIONS, EXCLUDED)
    # curseforge_dl.check_for_updates(MODS_FILE, OUTPUT_FOLDER, VERSIONS)
    # curseforge_dl.update_all(MODS_FILE, OUTPUT_FOLDER, VERSIONS)
