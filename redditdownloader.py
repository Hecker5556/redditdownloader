from curl_cffi.requests import AsyncSession, Response
import asyncio
import aiofiles
import re
from typing import Literal
import os
from datetime import datetime
import mimetypes
import traceback
import json
from html import unescape
import logging

class REDDITDOWNLOADER:
    def __init__(self, session: AsyncSession = None, proxy: str = None, ffmpegPath: str = None):
        """
        Args:
            session (curl_cffi.requests.AsyncSession) [optional] - provided session to make requests with
            proxy (str) [optional, None] - proxy to use in a new asyncsession
            ffmpegPath (str) [optional, None] - path to ffmpeg binary if not available in directory
        """
        self.session = session
        self.proxy = proxy
        self.closeSession = None
        self.ffmpegPath = ffmpegPath
        self.logger = logging.getLogger(__name__)
        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.5',
            'priority': 'u=0, i',
            'sec-ch-ua': '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-gpc': '1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
        }
        self.imageHeaders = {
                'accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                'accept-language': 'en-US,en;q=0.9',
                'priority': 'u=1, i',
                'referer': 'https://www.reddit.com/',
                'sec-ch-ua': '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'image',
                'sec-fetch-mode': 'no-cors',
                'sec-fetch-site': 'cross-site',
                'sec-fetch-storage-access': 'none',
                'sec-gpc': '1',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
            }
    async def __aenter__(self):
        if (self.session is None):
            self.session = AsyncSession(proxy=self.proxy)
            self.closeSession = True
        return self
    async def __aexit__(self, exc, exctype, tb):
        if (self.closeSession):
            await self.session.close()
        if (exc):
            traceback.print_exception(exc, exctype, tb)

    async def getManifestVideo(self, link: str, manifestType: Literal['video', 'gif'] = 'video'):
        """
        Args:
            link (str) - link to m3u8 containing the audio and/or video
            manifestType (Literal['video','gif']) - what type of manifest to expect
        Returns:
            list[dict[str, str]]
            video:
            ```json
            {
                "captions":         (str)
                "bandwidth":        (str)
                "averageBandwidth": (str)
                "width":            (str)
                "height":           (str)
                "frameRate":        (str)
                "codecs":           (str)
                "audioUrl" :        (str)
                "url":              (str)
            }
            ```
            gif:
            ```json
            {
                "bandwidth":    (str)
                "width":        (str)
                "height":       (str)
                "codecs":       (str)
                "url":          (str)
            }
            ```
        """
        r: Response = await self.session.get(link, headers=self.headers, impersonate="chrome", stream=True)
        self.logger.debug(f"Sent a {r.request.method} to {r.request.url} with status {r.status_code}")
        text = await r.atext()
        audios = {}
        videos = []
        audiosPattern = r"#EXT-X-MEDIA:URI=\"(.*?)\",TYPE=AUDIO,GROUP-ID=\"(.*?)\",NAME=\"(?:.*?)\",DEFAULT=(?:.*?),AUTOSELECT=(?:.*?)\n"
        audiosList = await asyncio.to_thread(re.findall, audiosPattern, text)
        for url, id in audiosList:
            audios[id] = url
        if manifestType == 'video':
            if len(audios) > 0:
                videosPattern = r"#EXT-X-STREAM-INF:PROGRAM-ID=0,CLOSED-CAPTIONS=(.*?),BANDWIDTH=(\d+),AVERAGE-BANDWIDTH=(\d+),RESOLUTION=(\d+)x(\d+),FRAME-RATE=(\d+),CODECS=\"(.*?)\",AUDIO=\"(.*?)\"(?:.*?)?\n(.*?)m3u8"
            else:
                videosPattern = r"#EXT-X-STREAM-INF:PROGRAM-ID=0,CLOSED-CAPTIONS=(.*?),BANDWIDTH=(\d+),AVERAGE-BANDWIDTH=(\d+),RESOLUTION=(\d+)x(\d+),FRAME-RATE=(\d+),CODECS=\"(.*?)\"\n(.*?)m3u8"
        else:
            videosPattern = r"#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=(\d+),RESOLUTION=(\d+)x(\d+),CODECS=\"(.*?)\"\n(.*?)_v4\.m3u8"
        videosList = await asyncio.to_thread(re.findall, videosPattern, text)
        if len(videosList) == 0 and manifestType == 'gif':
            videosPattern = r"#EXT-X-STREAM-INF:PROGRAM-ID=0,CLOSED-CAPTIONS=(.*?),BANDWIDTH=(\d+),AVERAGE-BANDWIDTH=(\d+),RESOLUTION=(\d+)x(\d+),FRAME-RATE=(\d+),CODECS=\"(.*?)\"\n(.*?)m3u8"
            videosList = await asyncio.to_thread(re.findall, videosPattern, text)
            manifestType = 'video'
        baseUrl = link.split("HLSPlaylist")[0]
        if manifestType == 'video':
            if len(audios) > 0:
                for captions, bandwidth, averageBandwidth, width, height, frameRate, codecs, audioId, url in videosList:
                    videos.append({
                        "captions": captions,
                        "bandwidth": bandwidth,
                        "averageBandwidth": averageBandwidth,
                        "width": width,
                        "height": height,
                        "frameRate": frameRate,
                        "codecs": codecs,
                        "audioUrl" : (baseUrl + audios.get(audioId)).replace("m3u8", "mp4" if url.startswith("CMAF") else "aac") if audios.get(audioId) is not None else None,
                        "url": baseUrl + url + ("mp4" if url.startswith("CMAF") else "ts"),
                    })
            else:
                for captions, bandwidth, averageBandwidth, width, height, frameRate, codecs, url in videosList:
                    videos.append({
                        "captions": captions,
                        "bandwidth": bandwidth,
                        "averageBandwidth": averageBandwidth,
                        "width": width,
                        "height": height,
                        "frameRate": frameRate,
                        "codecs": codecs,
                        "url": baseUrl + url + ("mp4" if url.startswith("CMAF") else "ts"),
                    })


            videos = sorted(videos, key=lambda x: (int(x['width']) * int(x['height']), int(x['averageBandwidth'])), reverse=True)
        else:
            for bandwidth, width, height, codecs, url in videosList:
                videos.append({
                    "bandwidth": bandwidth,
                    "width": width,
                    "height": height,
                    "codecs": codecs,
                    "url": baseUrl + url + ".ts"
                })
            videos = sorted(videos, key=lambda x: (int(x['width']) * int(x['height']), int(x['bandwidth'])), reverse=True)
        return videos
    async def _downloadTask(self, filename: str, response: Response):
        async with aiofiles.open(filename, "wb") as f1:
            async for chunk in response.aiter_content(1024):
                await f1.write(chunk)
    async def _downloadMedia(self, link: str, typeMedia: Literal['video', 'image', 'gif'], postInfo: dict = None, maxFileSize: int = None):
        if typeMedia == 'image':
            if postInfo is not None:
                if not os.path.exists(postInfo['subreddit']):
                    os.mkdir(postInfo['subreddit'])
                filename = os.path.join(postInfo['subreddit'], f"{postInfo['author']}-{datetime.now().timestamp():.0f}")
            else:
                filename = f"redditpost-{datetime.now().timestamp():.0f}"
            r: Response = await self.session.get(link, headers = self.imageHeaders, impersonate="chrome", stream=True)
            self.logger.debug(f"Sent a {r.request.method} to {r.request.url} with status {r.status_code}")
            async with aiofiles.open(filename, "wb") as f1:
                async for chunk in r.aiter_content(1024):
                    await f1.write(chunk)
            ext = mimetypes.guess_extension(r.headers.get("content-type"))
            if ext is None:
                ext = ".png"
            os.rename(filename, filename + ext)
            filename += ext
            return filename
        elif typeMedia == "video":
            if postInfo is not None:
                if not os.path.exists(postInfo['subreddit']):
                    os.mkdir(postInfo['subreddit'])
                filename = os.path.join(postInfo['subreddit'], f"{postInfo['author']}-{datetime.now().timestamp():.0f}")
            else:
                filename = f"redditpost-{datetime.now().timestamp():.0f}"
            videos = await self.getManifestVideo(link)
            if maxFileSize:
                for i in videos:
                    r: Response = await self.session.get(i['url'], stream=True, impersonate="chrome", headers=self.headers)
                    self.logger.debug(f"Sent a {r.request.method} to {r.request.url} with status {r.status_code}")
                    if (i.get('audioUrl')):
                        k: Response = await self.session.get(i['audioUrl'], stream=True, impersonate="chrome", headers=self.headers)
                        self.logger.debug(f"Sent a {r.request.method} to {r.request.url} with status {r.status_code}")
                        size = int(r.headers.get("content-length")) + int(k.headers.get("content-length"))
                    else:
                        size = int(r.headers.get("content-length"))
                    if (size <= maxFileSize):
                        if (i.get('audioUrl')):
                            videoTask = asyncio.create_task(self._downloadTask(filename, r))
                            audioTask = asyncio.create_task(self._downloadTask(filename + "_audio", k))
                            await asyncio.gather(videoTask, audioTask)
                        else:
                            await self._downloadTask(filename, r)
                        ext = mimetypes.guess_extension(r.headers.get("content-type"))
                        if ext is None:
                            ext = ".mp4"
                        if (i.get('audioUrl')):
                            if self.ffmpegPath is None:
                                self.ffmpegPath = "ffmpeg"
                            arguments = ["-i", filename, "-i", filename + "_audio", "-c", "copy","-v", "error", filename + ext]
                            process = await asyncio.subprocess.create_subprocess_exec(self.ffmpegPath, *arguments, stderr=asyncio.subprocess.PIPE)
                            await process.wait()
                            if (process.returncode != 0):
                                raise Exception("Ffmpeg had error with combining video and audio stream:\n" + (await process.stderr.read()).decode())
                            os.remove(filename)
                            os.remove(filename + "_audio")
                        else:
                            os.rename(filename, filename + ext)
                        return filename + ext
                raise Exception("No videos under threshold")

            else:
                r: Response = await self.session.get(videos[0]['url'], stream=True, impersonate="chrome", headers=self.headers)
                self.logger.debug(f"Sent a {r.request.method} to {r.request.url} with status {r.status_code}")
                if (videos[0].get('audioUrl')):
                    k: Response = await self.session.get(videos[0]['audioUrl'], stream=True, impersonate="chrome", headers=self.headers)
                    self.logger.debug(f"Sent a {r.request.method} to {r.request.url} with status {r.status_code}")
                    size = int(r.headers.get("content-length")) + int(k.headers.get("content-length"))
                else:
                    size = int(r.headers.get("content-length"))
                if (videos[0].get('audioUrl')):
                    videoTask = asyncio.create_task(self._downloadTask(filename, r))
                    audioTask = asyncio.create_task(self._downloadTask(filename + "_audio", k))
                    await asyncio.gather(videoTask, audioTask)
                else:
                    await self._downloadTask(filename, r)
                ext = mimetypes.guess_extension(r.headers.get("content-type"))
                if ext is None:
                    ext = ".mp4"
                if (videos[0].get('audioUrl')):
                    if self.ffmpegPath is None:
                        self.ffmpegPath = "ffmpeg"
                    arguments = ["-i", filename, "-i", filename + "_audio", "-c", "copy","-v", "error", filename + ext]
                    process = await asyncio.subprocess.create_subprocess_exec(self.ffmpegPath, *arguments, stderr=asyncio.subprocess.PIPE)
                    await process.wait()
                    if (process.returncode != 0):
                        raise Exception("Ffmpeg had error with combining video and audio stream:\n" + (await process.stderr.read()).decode())
                    os.remove(filename)
                    os.remove(filename + "_audio")
                else:
                    os.rename(filename, filename + ext)
                return filename + ext
        elif typeMedia == 'gif':
            if postInfo is not None:
                if not os.path.exists(postInfo['subreddit']):
                    os.mkdir(postInfo['subreddit'])
                filename = os.path.join(postInfo['subreddit'], f"{postInfo['author']}-{datetime.now().timestamp():.0f}")
            else:
                filename = f"redditpost-{datetime.now().timestamp():.0f}"
            videos = await self.getManifestVideo(link, 'gif')
            if maxFileSize is not None:
                for i in videos:
                    r: Response = await self.session.get(i['url'], stream=True, impersonate="chrome", headers=self.headers)
                    self.logger.debug(f"Sent a {r.request.method} to {r.request.url} with status {r.status_code}")
                    if (int(r.headers.get("content-length")) <= maxFileSize):
                        videoTask = await (self._downloadTask(filename, r))
                        ext = mimetypes.guess_extension(r.headers.get("content-type"))
                        if ext is None:
                            ext = ".mp4"
                        os.rename(filename, filename + ext)
                        return filename + ext
                raise Exception("No videos under threshold")
            else:
                r: Response = await self.session.get(videos[0]['url'], stream=True, impersonate="chrome", headers=self.headers)
                self.logger.debug(f"Sent a {r.request.method} to {r.request.url} with status {r.status_code}")
                videoTask = await (self._downloadTask(filename, r))
                ext = mimetypes.guess_extension(r.headers.get("content-type"))
                if ext is None:
                    ext = ".mp4"
                os.rename(filename, filename + ext)
                return filename + ext
                
    async def download(self, link: str, downloadMedia: bool = True, maxFileSize: int = None) -> dict[str, str]:
        """
        Args:
            link (str) - link to reddit post
            downloadMedia (bool) [optional, True] - download media of post or just return after all info is fetched
            maxFileSize (int) [optional, None] - max file size a video can be in bytes
        Returns:
            dict[str, str]
            ```json
            {
                "title": "",
                "language": "",
                "type": "",
                "subreddit": "",
                "author": "",
                "upvotes": "",
                "upvoteRatio": "",
                "commentsCount": "",
                "awards": "",
                "created": "",
                "image": "",
                "videoUrl": "",
                "images": "",
                "filenames": [
                    
                ]
            }
        """
        r: Response = await self.session.get(link, impersonate="chrome", stream=True, headers=self.headers)
        link = r.url
        self.logger.debug(f"Made a GET request to {link}, status code: {r.status_code}")
        text = await r.atext()
        maxTries = 5
        solution_pattern = r"\)\(\"(.*?)\"\)\);"
        otherParams_pattern = r"<input type=\"hidden\" name=\"(.*?)\" value=\"(.*?)\"/>"
        solution = await asyncio.to_thread(re.search, solution_pattern, text)
        if (solution is None):
            async with aiofiles.open("response.txt", "w", encoding="utf-8") as f1:
                await f1.write(text)
            raise Exception("Couldn't solve javascript test, solution couldn't be found in page source")
        solution = solution.group(1)
        self.logger.debug(f"Found solution string: {solution}")
        params = {}
        params["solution"] = solution + solution
        otherParams = await asyncio.to_thread(re.findall, otherParams_pattern, text)
        for key, value in otherParams:
            params[key] = value
            self.logger.debug(f"Found input param: {key}: {value}")
        r: Response = await self.session.get(link, impersonate="chrome", stream=True, params=params, headers=self.headers)
        link = r.url
        self.logger.debug(f"Sent a GET request to {link} with parameters: {params}, status code: {r.status_code}")
        text = await r.atext()
        while ("Reddit - Please wait for verification" in text and maxTries > 0):
            solution = await asyncio.to_thread(re.search, solution_pattern, text)
            if (solution is None):
                async with aiofiles.open("response.txt", "w", encoding="utf-8") as f1:
                    await f1.write(text)
                raise Exception("Couldn't solve javascript test, solution couldn't be found in page source")
            solution = solution.group(1)
            self.logger.debug(f"Found solution string: {solution}")
            params = {}
            params["solution"] = solution + solution
            otherParams = await asyncio.to_thread(re.findall, otherParams_pattern, text)
            for key, value in otherParams:
                params[key] = value
                self.logger.debug(f"Found input param: {key}: {value}")
            r: Response = await self.session.get(link, impersonate="chrome", stream=True, params=params, headers=self.headers)
            link = r.url
            self.logger.debug(f"Sent a GET request to {link} with parameters: {params}, status code: {r.status_code}")
            text = await r.atext()
            maxTries -= 1
        if (maxTries == 0):
            raise Exception("Reddit gave javascript test more than 5 times, exiting")
        postPattern = r"<shreddit-post class(?:.*?)subreddit-name=\"(.*?)\">"
        postInfo = await asyncio.to_thread(re.search, postPattern, text)
        if (postInfo is None):
            redirectPattern = r"method=\"location\.replace\((.*?)\)\"></ac-call>"
            redirectUrl = await asyncio.to_thread(re.search, redirectPattern, text)
            if not redirectUrl:
                async with aiofiles.open("response.txt", "w", encoding="utf-8") as f1:
                    await f1.write(text)
                raise Exception("Couldn't get post info from page source")
            redirectUrl = 'https://reddit.com' + unescape(redirectUrl.group(1)).replace('"', '')
            r: Response = await self.session.get(redirectUrl, impersonate="chrome", stream=True, headers=self.headers)
            link = r.url
            self.logger.debug(f"Sent a GET request to {link} with parameters: {params}, status code: {r.status_code}")
            text = await r.atext()
            postInfo = await asyncio.to_thread(re.search, postPattern, text)
            if (postInfo is None):  
                async with aiofiles.open("response.txt", "w", encoding="utf-8") as f1:
                    await f1.write(text)
                raise Exception("Couldn't get post info from page source")
        post = postInfo.group(0)
        self.logger.debug(f"Found shreddit post class: {post}")
        subreddit = postInfo.group(1)
        postInfoPattern = r"post-(.*?)=\"(.*?)\""
        title = await asyncio.to_thread(re.findall, postInfoPattern, post)
        postData = {}
        for key, value in title:
            postData[key] = unescape(value)
            self.logger.debug(f"Extracted {key}: {unescape(value)} from shreddit post class")
        postData["subreddit"] = subreddit
        authorPattern = r"author=\"(.*?)\""
        author = await asyncio.to_thread(re.search, authorPattern, post)
        if author:
            postData['author'] = unescape(author.group(1))
        upvotesPattern = r"score=\"(\d+)\""
        authorAvatarPattern = r"icon=\"(.*?)\""
        authorAvatar = await asyncio.to_thread(re.search, authorAvatarPattern, post)
        if authorAvatar is not None:
            postData['authorAvatar'] = authorAvatar.group(1)
        upvotes = await asyncio.to_thread(re.search, upvotesPattern, post)
        if upvotes:
            postData['upvotes'] = upvotes.group(1)
        upvoteRatioPattern = r"upvote-ratio=\"([\d\.]+)\""
        upvoteRatio = await asyncio.to_thread(re.search, upvoteRatioPattern, post)
        if upvoteRatio:
            postData['upvoteRatio'] = upvoteRatio.group(1)[:5]
        commentsPattern = r"comment-count=\"(\d+)\""
        commentsCount = await asyncio.to_thread(re.search, commentsPattern, post)
        if commentsCount:
            postData['commentsCount'] = commentsCount.group(1)
        descriptionPattern = r"<shreddit-post-text-body slot=\"text-body\"([\s\S]*?)</shreddit-post-text-body>"
        description = await asyncio.to_thread(re.search, descriptionPattern, text)
        if (description is not None):
            descriptionTextPattern = r"<p(?: dir=\"auto\")?>([\s\S]*?)</p>"
            postData['description'] = unescape("\n".join([re.sub(r"<a(?:[\s\S]*?)?>(.*?)</a>", lambda match: match.group(1), x.strip().replace("<br>", "\n")) for x in (await asyncio.to_thread(re.findall, descriptionTextPattern, description.group(1)))]))
            self.logger.debug(f"Found description of post")
        awardsPattern = r"award-count=\"(\d+)\""
        awards = await asyncio.to_thread(re.search, awardsPattern, post)
        if awards:
            postData['awards'] = awards.group(1)
        createdPattern = r"created-timestamp=\"(.*?)\""
        created = await asyncio.to_thread(re.search, createdPattern, post)
        if created:
            postData['created'] = created.group(1)
        if postData['type'] == 'image':
            imagePattern = r"content-href=\"(.*?)\""
            image = await asyncio.to_thread(re.search, imagePattern, text)
            postData['image'] = image.group(1)
            if downloadMedia:
                postData['filenames'] = [await self._downloadMedia(postData['image'], 'image', postData)]
        elif postData['type'] == 'video':
            videoUrlPattern = r"<shreddit-player src=\"(.*?)\""
            videoUrl = await asyncio.to_thread(re.search, videoUrlPattern, text)
            postData['videoUrl'] = videoUrl.group(1).replace("&amp;", "&")
            if downloadMedia:
                postData['filenames'] = [await self._downloadMedia(postData['videoUrl'], postData['type'], postData, maxFileSize)]
        elif postData['type'] == "gallery":
            listPattern = r"<li slot=\"page-(\d+)\" class=\"(?:.*?)>([\s\S]*?)</li>"
            imageList = await asyncio.to_thread(re.findall, listPattern, text)
            postData['filenames'] = []
            postData['images'] = []
            srcPattern = r"src=\"(.*?)\""
            slugPattern = r"v0-(.*?)\.(.*?)\?"
            baseUrl = "https://i.redd.it/"
            for pageNo, imageData in imageList:
                url = (await asyncio.to_thread(re.search, srcPattern, imageData)).group(1)
                slugExt = await asyncio.to_thread(re.search, slugPattern, url)
                url = baseUrl + slugExt.group(1) + '.' + slugExt.group(2)
                postData['images'].append(url)
                if downloadMedia:
                    file = await self._downloadMedia(url, "image", postData)
                    newFilename = os.path.splitext(file)[0] + '-' + pageNo + os.path.splitext(file)[1]
                    os.rename(file, newFilename)
                    postData['filenames'].append(newFilename)
        elif postData['type'] == 'gif':
            imagePattern = r"content-href=\"(.*?)\""
            image = await asyncio.to_thread(re.search, imagePattern, text)
            if (image.group(1).endswith('.gif')):
                postData['image'] = image.group(1)
                if downloadMedia:
                    postData['filenames'] = [await self._downloadMedia(postData['image'], 'image', postData)]
            else:
                videoUrlPattern = r"<shreddit-player src=\"(.*?)\""
                videoUrl = await asyncio.to_thread(re.search, videoUrlPattern, text)
                postData['videoUrl'] = videoUrl.group(1).replace("&amp;", "&")
                if downloadMedia:
                    postData['filenames'] = [await self._downloadMedia(postData['videoUrl'], 'gif', postData, maxFileSize)]
        elif postData['type'] == 'crosspost':
            referencePattern = r"content-href=\"(.*?)\""
            referece = await asyncio.to_thread(re.search, referencePattern, text)
            if referece:
                postData['crosspost'] = await self.download("https://reddit.com" + referece.group(1), downloadMedia, maxFileSize)
        return postData
async def main():
    import argparse     
    parser = argparse.ArgumentParser()
    parser.add_argument("link", help="Link to post")
    parser.add_argument("--proxy", "-p", help="Proxy to use in connection")
    parser.add_argument("--max-size", "-m", help="Max size of video allowed to download in megabytes", type=float)
    parser.add_argument("--no-download", "-n", help="Dont download the post", action="store_false", default=True)
    parser.add_argument("--verbose", "-v", help="Enable verbosity", action="store_true", default=False)
    args = parser.parse_args()
    if (args.max_size is not None):
        maxSize = args.max_size * 1024 * 1024
    else:
        maxSize = None
    async with REDDITDOWNLOADER(proxy=args.proxy) as rd:
        if (args.verbose):
            console = logging.StreamHandler()
            rd.logger.addHandler(console)
            rd.logger.setLevel(logging.DEBUG)
        result = await rd.download(args.link, maxFileSize = maxSize, downloadMedia=args.no_download)
    print(json.dumps(result, indent=4, ensure_ascii=False))
if __name__ == "__main__":
    asyncio.run(main())
