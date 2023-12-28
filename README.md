# Simple Reddit Post Downloader
## First time setup
### Install [python](https://python.org)
### In cmd
```bash
git clone "https://github.com/Hecker5556/redditdownloader.git"
```
```bash
cd redditdownloader
```
```bash
pip install -r requirements.txt
```
download [ffmpeg](https://www.ffmpeg.org/download.html)
# Usage
## Usage with exe (you can add to path)
```
usage: redditdownloader.exe [-h] [--maxsize MAXSIZE] link

download videos and audios

positional arguments:
  link                  link to the reddit post

options:
  -h, --help            show this help message and exit
  --maxsize MAXSIZE, -s MAXSIZE
                        maximum size of video
```
## Usage in cli
```
usage: redditdownloader.py [-h] [--maxsize MAXSIZE] link

download videos and audios

positional arguments:
  link                  link to the reddit post

options:
  -h, --help            show this help message and exit
  --maxsize MAXSIZE, -s MAXSIZE
                        maximum size of video
```

## Usage in python
```python
import asyncio, sys
if '/path/to/redditdownloader/' not in sys.path:
    sys.path.append('/path/to/redditdownloader/')
from redditdownloader.redditdownloader import redditdownloader
#Create event loop 
filenames = asyncio.run(redditdownloader.download(link='', maxsize=50))

#In running event loop
async def main():
    filenames = await redditdownloader.download(link='', maxsize=50)
    return filenames
```
