# Simple Reddit Post Downloader
## Features
* Downloads image, gif, gallery, video from a post
* Extracts post information like upvotes, title, description, and lossless images
* Fully asynchronous
* getManifestVideo method
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
## download [ffmpeg](https://www.ffmpeg.org/download.html)
Downloading videos involves combining a video and an audio, ffmpeg path can be provided
# Usage
## Usage in cli
```
usage: redditdownloader.py [-h] [--proxy PROXY] [--max-size MAX_SIZE] [--no-download] link

positional arguments:
  link                  Link to post

options:
  -h, --help            show this help message and exit
  --proxy PROXY, -p PROXY
                        Proxy to use in connection
  --max-size MAX_SIZE, -m MAX_SIZE
                        Max size of video allowed to download in megabytes
  --no-download, -n     Dont download the post
```

## Usage in python
```python
from redditdownloader import REDDITDOWNLOADER
import asyncio
async def main():
  async with REDDITDOWNLOADER() as rd:
      postInfo = await rd.download("https://reddit.com/r/somesubreddit/some_post_id")
      filenames = postInfo.get("filenames")
```
## Example output
Text post
```json
{
    "title": "What free things online should everyone take advantage of?",
    "language": "en",
    "type": "text",
    "subreddit": "AskReddit",
    "author": "[deleted]",
    "upvotes": "141636",
    "upvoteRatio": "0.953",
    "commentsCount": "14637",
    "awards": "1",
    "created": "2019-12-19T12:10:59.057000+0000"
}
```
gif stored as mp4
```json
{
    "title": "My dog got on the news. This was my favourite bit.",
    "language": "en",
    "type": "gif",
    "subreddit": "gifs",
    "author": "DrChilton",
    "upvotes": "179501",
    "upvoteRatio": "0.965",
    "commentsCount": "1770",
    "awards": "0",
    "created": "2019-03-22T14:01:30.656000+0000",
    "videoUrl": "https://v.redd.it/zbagwuwlfon21/HLSPlaylist.m3u8?f=sd%2CsubsAll%2ChlsSpecOrder&v=1&a=1783102186%2COTgxZWE4YWU4ZTIxMjZiZWMyMGQ4YjgyZDFiZjgwNzZjNjU5OWFlYjEzNjJmZWE0NjFmZTE3M2Q1NjIwOTc0Yg%3D%3D",
    "filenames": [
        "gifs\\DrChilton-1780510186.mp4"
    ]
}
```
gif stored gif
```json
{
    "title": "Who is Pecky's favorite 1960s US actor who played a lawyer?",
    "language": "en",
    "type": "gif",
    "subreddit": "PallasCats",
    "author": "escuchamenche",
    "upvotes": "114",
    "upvoteRatio": "1",
    "commentsCount": "4",
    "description": "Gregory PECK",
    "awards": "0",
    "created": "2026-06-03T02:53:26.550000+0000",
    "image": "https://i.redd.it/3wisqhvffz4h1.gif",
    "filenames": [
        "PallasCats\\escuchamenche-1780510571.gif"
    ]
}
```
video
```json
{
    "title": "Tiny Pallas Cat kitten",
    "language": "en",
    "type": "video",
    "subreddit": "Tinycatsinbigspaces",
    "author": "fullnameqwertyu",
    "upvotes": "514",
    "upvoteRatio": "1",
    "commentsCount": "6",
    "awards": "1",
    "created": "2024-05-17T22:44:42.474000+0000",
    "videoUrl": "https://v.redd.it/4d0ber11f21d1/HLSPlaylist.m3u8?f=hd%2CsubsAll%2ChlsSpecOrder&v=1&a=1783103494%2CYWIxMmVlMGM2OTc5ZGYyZGM0MWZlNTdmMjUzM2U0ZWJiNmU5MmE1ZTVmYWZkNzgyMzMzOWQ5NTVkZDAwZWI4ZA%3D%3D",
    "filenames": [
        "Tinycatsinbigspaces\\fullnameqwertyu-1780511494.mp4"
    ]
}
```
image
```json
{
    "title": "I love Manul",
    "language": "en",
    "type": "image",
    "subreddit": "PallasCats",
    "author": "[deleted]",
    "upvotes": "133",
    "upvoteRatio": "1",
    "commentsCount": "18",
    "awards": "0",
    "created": "2023-03-17T14:36:04.556000+0000",
    "image": "https://i.redd.it/4iiyi6q39boa1.jpg",
    "filenames": [
        "PallasCats\\[deleted]-1780511618.jpg"
    ]
}
```