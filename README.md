# smarthash
SmartHash is a command line application for the BitTorrent Peer-to-Peer network. It allows users to more easily prepare and publish content and metadata

Capabilities include:
* Creating metadata (.torrent) files
Identifying audio and video files
Extracting screenshots from video files
Extracting mediainfo and tagging information
Parsing accompanying release information, extracting IMDb IDs

### Handlers

Smarthash uses pluggable handlers, allowing for custom actions in different usage scenarios. By default, a .torrent file is saved. An additional provided handler writes out the .torrent, screenshots, MediaInfo and NFO to a folder.

Custom handlers can be dropped into the application (for example, allowing automatic publication of your content to an Internet-based site). Audio metadata or screenshots could also be automatically uploaded. Where necessary, additional command line parameters can be captured by the handler.

### Metadata

Audio-specific metadata is extracted, and provided as a parameter to the handers.

A set of screenshots are extracted from each video file. These can be useful for estimating quality before downloading a torrent - candidates are selected using a Laplacian transform/variance calculation, which effectively extracts a useful selection.

### Usage instructions

Windows installation
* Download and install Python 3.6.5 (or later) - https://www.python.org/downloads
* Download and install Git - https://git-scm.com/download/win
* In your C:\, right click, and select "Git Bash Here" from the context menu
* Install virtualenv for Python, by entering: 
```pip install virtualenv```
* Clone the SmartHash repository, by entering: 
```git clone https://github.com/spiritualized/smarthash.git```
* Run win-install.bat to set up the virtualenv
* Add C:\smarthash to your PATH

Linux
* Clone the repo
* Create a virtualenv (use -p python3) and install from requirements.txt

Usage examples
* smarthash "C:\My Home Movies"