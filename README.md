# SlowCopy

Copy directories to a fixed destination and build md5 hashes. Some criterias are checked while selecting the source directory. Some subdirectories with to many files will be zipped.

The GUI is close to a well known copy tool so the old dogs don´t need to learn new tricks.

RoboCopy is used so this is for Windows.

There is a check for updates on startup.

The tool can be also be run on PowerShel/CMD. Try

`slowcopy.exe -h xxx-vx.x.x.exe -h`

to learn usage.

PyInstaller is needed to bild Windows executables. A make-script can build multiple executables for different destinations. Edit `make-slowcopy.py` and run

`python make-slowcopy.py`

to find the executables in the subfolder `dist`.

Still testing. The author is not responsible for any malfunction and/or lost data.

MIT License
