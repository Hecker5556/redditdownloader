import aiohttp, asyncio, re, json, aiofiles, os
from html import unescape
from datetime import datetime
from tqdm.asyncio import tqdm
from aiohttp_socks import ProxyConnector
class redditdownloader:
    def _make_connector(self, proxy: str = None):
        self.proxy = proxy if proxy and proxy.startswith("http") else None
        return ProxyConnector.from_url(proxy) if proxy and proxy.startswith("socks") else aiohttp.TCPConnector()
    async def download(self, link: str, proxy: str = None, dont_download: bool = False):
        if not hasattr(self, "session") or self.session.closed():
            async with aiohttp.ClientSession(connector=self._make_connector(proxy)) as session:
                self.session = session
                return await self._download(link, proxy, dont_download)
        else:
            return await self._download(link, proxy, dont_download)
    def _clear(self, x: str):
        while x.startswith("-"):
            x = x[1:]
        return "".join([i for i in x if i not in "\\/:*?<>|()"])
    async def _download(self, link: str, proxy: str = None, dont_download: bool = False):
        patternvideo = r'packaged-media-json=\"(.*?)\"'
        patternmanifest = r'((https://v\.redd\.it/(?:.*?)/)HLSPlaylist\.m3u8\?(?:.*?))\"'
        patterncaption = r'<shreddit-title title=\"(.*?)\"></shreddit-title>'
        patterndescription = r"<div class=\"text-neutral-content\" slot=\"text-body\">([\s\S]*?)</div>"
        patterndescription2 = r"<p>([\s\S]*?)</p>"
        patternlinks = r"<a(?:[\s\S]*?)>(.*?)</a(?:[\s\S]*?)>"
        authorpattern = r"author=\"(.*?)\""
        srcsetpattern = r"srcSet=\"(.*?)\""
        slideshowpattern = r"<li slot=\"page-\d+\"(?:[\s\S]*?)/>"
        datapattern = r"data=\"(.*?)\"[\s\S]*?>"
        commentpattern = r"https://(?:www\.)?reddit\.com/(?:.*?)/(?:.*?)/comments/(?:.*?)/comment/(.*?)(?:/|$)"
        headers = {
        'Referer': 'https://www.reddit.com/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'Range': 'bytes=0-',
        }
        async with self.session.get(link, headers=headers, proxy=self.proxy) as r:
            rtext = await r.text("utf-8")
        media = {'link': link,
                 'video_url': None,
                 'manifest_url': None,
                 'image': None,
                 'gif': None, 
                 'image_gallery': None,
                 'caption': None,
                 'description': None,
                 'author': "temp",
                 'filenames': []}
        if author := re.search(authorpattern, rtext):
            author = unescape(author.group(1))
            media['author'] = author
        if comment := re.search(commentpattern, link):
            commentid = comment.group(1)
            nextlink = "https://reddit.com" + unescape(re.search(r"href=\"((?:/svc/shreddit/comments/).*?)\"", rtext).group(1))
            async with self.session.get(nextlink, proxy=self.proxy) as r:
                comments = await r.text()
            thecomment = comments[comments.find(commentid):comments.rfind(commentid)]
            media['author'] = re.search(r"author=\"(.*?)\"", thecomment).group(1)
            if caption := re.search(r"<p>([\s\S]*?)</p>", thecomment):
                caption = unescape(caption.group(1))
                media['caption'] = caption
            elif image := re.search(r"faceplate-img\n +src=\"(.*?)\"", thecomment):
                image = unescape(image.group(1))
                media['image'] = image
                if not dont_download:
                    filename = f"{self._clear(media['author'])}-{int(datetime.now().timestamp())}"
                    filename = await self._download_image(media['image'], filename)
                    media['filenames'].append(filename)
            return media
        if data := re.search(patternvideo, rtext):
            data = unescape(data.group(1))
            data = json.loads(data)
            media['video_url'] = data['playbackMp4s']['permutations'][-1]['source']['url']
            if not dont_download:
                filename = f"{self._clear(media['author'])}-{int(datetime.now().timestamp())}.mp4"
                await self._download_video(media['video_url'], filename)
                media['filenames'].append(filename)
        elif manifests := re.search(patternmanifest, rtext):
            manifests = manifests.group(1)
            media['manifest_url'] = unescape(manifests)
            if not dont_download:
                filename = f"{self._clear(media['author'])}-{int(datetime.now().timestamp())}.mp4"
                await self._download_video_manifest(media['manifest_url'], filename)
                media['filenames'].append(filename)
        elif image := re.search(srcsetpattern, rtext):
            image = list(map(lambda x: x.split(' ')[0], unescape(image.group(1)).split(', ')))[-1]
            media['image'] = image
            if not dont_download:
                filename = f"{self._clear(media['author'])}-{int(datetime.now().timestamp())}"
                filename = await self._download_image(media['image'], filename)
                media['filenames'].append(filename)
        elif images := re.findall(slideshowpattern, rtext):
            image_links = []
            srcsetpattern2 = re.compile(r"srcset=\"(.*?)\"")
            lazydata = re.compile(r"data-lazy-src=\"(.*?)\"")
            for img_ in images:
                img = list(map(lambda x: x.split(' ')[0], unescape(re.search(srcsetpattern2, img_).group(1)).split(', ')))[-1]
                if not img:
                    img = unescape(re.search(lazydata, img_).group(1))
                    print(img)
                image_links.append(img)
            media['image_gallery'] = image_links
            if not dont_download:
                for index, image in enumerate(media['image_gallery']):
                    filename = f"{self._clear(media['author'])}-{int(datetime.now().timestamp())}-{index}"
                    filename = await self._download_image(image, filename)
                    media['filenames'].append(filename)
        elif gif := re.search(datapattern, rtext):
            data = unescape(gif.group(1))
            data = json.loads(data)
            gif = data['post']['url']
            media['gif'] = gif
            if not dont_download:
                filename = f"{self._clear(media['author'])}-{int(datetime.now().timestamp())}"
                filename = await self._download_image(media['gif'], filename)
                media['filenames'].append(filename)
        if caption := re.search(patterncaption, rtext):
            caption = unescape(caption.group(1))
            media['caption'] = caption
        if description := re.search(patterndescription, rtext):
            description = unescape(re.search(patterndescription2, description.group(0)).group(1))
            description = re.sub(patternlinks, lambda x: x.group(1), description)
            media['description'] = description
        return media
    async def _download_video(self, link: str, filename: str):
        async with aiofiles.open(filename, 'wb') as f1:
            async with self.session.get(link, proxy=self.proxy) as r:
                progress = tqdm(total=int(r.headers.get("content-length")), unit='iB', unit_scale=True, colour="green")
                while True:
                    chunk = await r.content.read(1024)
                    if not chunk:
                        break
                    await f1.write(chunk)
                    progress.update(len(chunk))
                progress.close()
    async def _download_video_manifest(self, link: str, filename: str):
        async with self.session.get(link, proxy=self.proxy) as r:
            rtext = await r.text("utf-8")
        mainurl = link.split("HLSPlaylist")[0]
        audios = {}
        audiourlpattern = r'URI=\"(.*?)\"'
        audioidpattern = r'GROUP-ID=\"(.*?)\"'
        videoaudiopattern = r'AUDIO=\"(\d+)\"'
        videoresolutionpattern = r'RESOLUTION=(\d+x\d+)'
        formats = {}
        for index, line in enumerate(rtext.split("\n")):
            if line.startswith("#EXT-X-MEDIA:URI="):
                audios[re.search(audioidpattern, line).group(1)] = f"{mainurl}{re.search(audiourlpattern, line).group(1)}"
            elif line.startswith("#EXT-X-STREAM-INF"):
                formats[re.search(videoresolutionpattern, line).group(1)] = {"video": mainurl + rtext.split("\n")[index+1], "audio": audios.get(re.search(videoaudiopattern, line).group(1))}
        for _, value in formats.items():
            tasks: list[asyncio.Task] = []
            tasks.append(asyncio.create_task(self._download_video_manifest_worker(value.get('video'), mainurl)))
            tasks.append(asyncio.create_task(self._download_video_manifest_worker(value.get('audio'), mainurl)))
            resultfiles = await asyncio.gather(*tasks)
            command = ["-i", resultfiles[0], "-i", resultfiles[1], '-c', 'copy', '-map', '0:v:0', '-map', '1:a:0', '-y', filename]
            process = await asyncio.create_subprocess_exec("ffmpeg", *command)
            await process.wait()
            [os.remove(file) for file in resultfiles]
            break
    async def _download_video_manifest_worker(self, link: str, mainurl: str):
        tempfile = f"tempfile-{int(datetime.now().timestamp())}."
        async with self.session.get(link, proxy=self.proxy) as r:
            while True:
                line = await r.content.readline()
                if ".ts" in line.decode() or ".aac" in line.decode():
                    if ".ts" in line.decode() and tempfile.endswith("."):
                        tempfile += "mp4"
                    elif ".aac" in line.decode() and tempfile.endswith("."):
                        tempfile += "aac"
                    link = mainurl + line.decode()
                    break
                if not line:
                    raise ConnectionError(f"something went wrong when getting {link}")
        async with aiofiles.open(tempfile, 'wb') as f1:
            async with self.session.get(link, proxy=self.proxy) as r:
                progress = tqdm(total=int(r.headers.get("content-length")), unit='iB', unit_scale=True, colour="green")
                while True:
                    chunk = await r.content.read(1024)
                    if not chunk:
                        break
                    await f1.write(chunk)
                    progress.update(len(chunk))
                progress.close()
        return tempfile
    async def _download_image(self, link: str, filename: str):
        async with self.session.get(link, proxy=self.proxy) as r:
            filename += "." + r.headers.get('content-type').split('/')[1]
            progress = tqdm(total=int(r.headers.get("content-length")), unit='iB', unit_scale=True, colour="green")
            async with aiofiles.open(filename, 'wb') as f1:
                while True:
                    chunk = await r.content.read(1024)
                    if not chunk:
                        break
                    await f1.write(chunk)
                    progress.update(len(chunk))
            progress.close()
            return filename
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("link", type=str, help="link to post")
    parser.add_argument("--proxy", type=str, help="proxy to use")
    parser.add_argument("--no-download", "-nd", action="store_true", help="whether to not download and just return media links")
    args = parser.parse_args()
    result = asyncio.run(redditdownloader().download(args.link, args.proxy, args.no_download))
    print(result)