# CurseforgeDownloader
A python script for mass downloading curseforge mods

### Uses
This python script has the ability to download, update, or check for updates on a single URL or a text file of URLs for 
project pages of Curseforge projects. In this case, nothing fancy like manifest files or anything similar are used, just
a text file containing a curseforge link on each line. This makes it extremely easy to mass download a lot of Curseforge
links all at once.

### Motives
This script was created for the ability to easily maintain a Minecraft modpack so that updates could automatically be checked
for 200+ mods all automatically. This script without a doubt has saved me so much trouble of manually downloading each file and
subsequently having to check for updates for all mods every month or so. However, I'm sure that it can be used for many other
things besides this.

### How to use
1. Clone this repository into the Python development environment of your choice.
2. In `main.py`, uncomment the type of downloading that you want to occur. It should be self explanatory that `download_all`
will download all files, `update_all` will update all files, and `check_for_updates` checks for updates of all files without
actually downloading them.
3. Somewhere in the project, create a folder and a text file. The text file will contain all Curseforge project links to the mods
and the folder will be the final download location of the mods.
4. After pasting all Curseforge links into the text file and saving the file, change the `MODS_FILE` to reflect the location of
the text file that was just created. Similarly, change the `OUTPUT_FOLDER` to reflect the final destination of the downloaded
files.
5. Run the Python script. Remember that the line of code that was uncommented in a previous step is the type of download method
that will be used. Only one download method should be used, as using multiple would be redundant.

### Reporting Issues
If you're having an issue understanding instructions, you can contact me on my Discord on my Github profile. If there is an
issue or error with the script itself please open an issue on the Github repository and describe the issue or error with the
script.
