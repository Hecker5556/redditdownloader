import aiohttp, asyncio, re, json, aiofiles, os
from html import unescape
from datetime import datetime
from tqdm.asyncio import tqdm
from bs4 import BeautifulSoup
from aiohttp_socks import ProxyConnector
class redditdownloader:
    def makeconnector(proxy: str = None):
        connector = aiohttp.TCPConnector()
        if proxy:
            if "socks" in proxy:
                connector = ProxyConnector.from_url(proxy)
            else:
                connector = aiohttp.TCPConnector(proxy=proxy)
        return connector
    async def main(link: str, proxy: str = None):
        patternvideo = r'packaged-media-json=\"{&quot;playbackMp4s&quot;:((.*?)}}}]})'
        patternmanifest = r'((https://v\.redd\.it/(?:.*?)/)HLSPlaylist\.m3u8\?(?:.*?))\"'
        patterncaption = r'<shreddit-title title=\"(.*?)\"></shreddit-title>'
        patterndescription = r"<div class=\"text-neutral-content\" slot=\"text-body\">([\s\S]*?)</div>"
        patterndescription2 = r"<p>([\s\S]*?)</p>"
        patternlinks = r"<a(?:[\s\S]*?)>(.*?)</a(?:[\s\S]*?)>"
        headers = {
        'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Brave";v="116"',
        'Referer': 'https://www.reddit.com/',
        'sec-ch-ua-mobile': '?0',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'Range': 'bytes=0-',
        'sec-ch-ua-platform': '"Windows"',
        }

        async with aiohttp.ClientSession(connector=redditdownloader.makeconnector(proxy)) as session:
            async with session.get(link, headers=headers) as r:
                rtext = await r.text()
                with open('response.txt', 'w', encoding="utf-8") as f1:
                    f1.write(rtext)
            mainurls = re.findall(patternvideo, rtext)
            manifesturls = re.findall(patternmanifest, rtext)
            caption = re.findall(patterncaption, rtext)
            description = re.findall(patterndescription, rtext)
            if description:
                description = re.findall(patterndescription2, description[0])
            thetext = {"caption": caption[0] if caption else caption, "description": "\n".join([d.lstrip().rstrip() for d in description]) if description else description}
            if thetext.get("description"):
                thetext['description'] = re.sub(patternlinks, lambda match: match.group(1), thetext['description'])
                thetext['description'] = thetext['description'].replace("&quot;", "\"").replace("&#39;", "'")
            postinfo = None
            if mainurls:
                
                mainurls = json.loads(unescape(mainurls[0][0]))
                postinfo = {}
                for index, value in enumerate(mainurls['permutations']):
                    while True:
                        try:
                            async with session.get(value['source']['url'], timeout=5) as r:
                                contentlength = int(r.headers.get('content-length'))
                            postinfo[index] = {'url': value['source']['url'],
                                                'width': value['source']['dimensions']['width'],
                                                'height': value['source']['dimensions']['height'],
                                                'duration': mainurls['duration'],
                                            'contentlength': contentlength}
                            break
                        except asyncio.exceptions.TimeoutError:
                            print('timedout! retrying in 3 seconds')
                            await asyncio.sleep(3)
                            continue
                postinfo = sorted(postinfo.items(), key=lambda x: x[1].get('contentlength'), reverse=True)
                temp = {}
                for i in postinfo:
                    temp[i[0]] = i[1]
                postinfo = temp
            
            elif manifesturls:
                manifesturl = manifesturls[0][0]
                mainurl = manifesturls[0][1]
                async with session.get(manifesturl) as response:
                    responsetext = await response.text()
                audioformats = {}
                videoformats = {}
                for i in responsetext.split('\n'):
                    if i.startswith('#EXT-X-MEDIA:URI='):
                        audiourlpattern = r'URI=\"(.*?)\"'
                        audioidpattern = r'GROUP-ID=\"(.*?)\"'
                        audioformats[re.findall(audioidpattern, i)[0]] = re.findall(audiourlpattern, i)[0]
                videoformatspattern = r'#EXT-X-STREAM-INF:(?:[\s\S.]*?)AUDIO=\"(.*?)\"\n(.*?)\.m3u8'
                matches = re.findall(videoformatspattern, responsetext)
                for match in matches:
                    videoformats[match[1]] = match[0]
                videoformats = sorted(videoformats.items(), key=lambda x: int(x[0].split('_')[1]), reverse=True)
                postinfo = []
                for i in videoformats:
                    postinfo.append((mainurl + i[0]+'.ts', mainurl + audioformats[i[1]].replace('.m3u8', '.aac')))
                
                    
            else:
                urls = []
                listpattern = r"<li slot=\"page-(?:\d*?)\"([\s\S]*?)</li>"
                lists = re.findall(listpattern, rtext)
                srcsetpattern = r"srcset=\"(.*?)\""
                if lists:
                    for page in lists:
                        matches = re.findall(srcsetpattern, page)
                        if not matches:
                            continue
                        images = matches[0].split(",")
                        images = [image.split()[0].replace("amp;", "") for image in images]
                        urls.append(images[-1])
                print(urls)
                if len(urls) > 0:
                    return urls, thetext
                else:
                    patternimage = r'data=\"(.*?)\"'
                    data = re.findall(patternimage, rtext)
                    if data:
                        data = json.loads(unescape(data[0]))

                        if data.get('post').get('type') != 'text' and data.get('post').get('type') != "multi_media":
                            return data.get('post').get('url'), thetext
                    return None, thetext
        print(postinfo)
        return postinfo, thetext
    async def download(link, maxsize: int = None, proxy: str = None):
        postinfo, thetext = await redditdownloader.main(link, proxy)
        if not postinfo:
            return None, thetext
        filenames = None
        if isinstance(postinfo, dict):
            for key, value in postinfo.items():
                if not maxsize:
                    pass
                else:
                    if value.get('contentlength')/(1024*1024) > maxsize:
                        continue
                filename = f'redditvideo-{str(datetime.now().timestamp()).replace(".", "")}.mp4'
                async with aiofiles.open(filename, 'wb') as f1:
                    async with aiohttp.ClientSession(connector=redditdownloader.makeconnector(proxy)) as session:
                        async with session.get(value.get('url')) as r:
                            progress = tqdm(total=int(r.headers.get('content-length')), unit='iB', unit_scale=True)
                            while True:
                                chunk = await r.content.read(1024)
                                if not chunk:
                                    break
                                await f1.write(chunk)
                                progress.update(len(chunk))
                            progress.close()
                            break
        elif isinstance(postinfo, str):
            filetype = postinfo[-3:]
            filename = f'redditimage-{round(datetime.now().timestamp())}.{filetype}'
            async with aiofiles.open(filename, 'wb') as f1:
                async with aiohttp.ClientSession(connector=redditdownloader.makeconnector(proxy)) as session:
                    async with session.get(postinfo, allow_redirects=False) as r:
                        progress = tqdm(total=int(r.headers.get('content-length'))  if not r.headers.get('Transfer-Encoding') == 'chunked' else None, unit='iB', unit_scale=True)
                        while True:
                            chunk = await r.content.read(1024)
                            if not chunk:
                                break
                            await f1.write(chunk)
                            progress.update(len(chunk))
                        progress.close()
        elif isinstance(postinfo, list) and all(isinstance(item, str) for item in postinfo):
            filenames = []
            async with aiohttp.ClientSession(connector=redditdownloader.makeconnector(proxy)) as session:
                for index, url in enumerate(postinfo):
                    filename = f'redditimage-{round(datetime.now().timestamp())}-{index}.{"png" if "format=png" in url else "jpg"}'
                    filenames.append(filename)
                    async with aiofiles.open(filename, 'wb') as f1:
                        async with session.get(url) as r:
                            progress = tqdm(total=int(r.headers.get('content-length')), unit='iB', unit_scale=True)
                            while True:
                                chunk = await r.content.read(1024)
                                if not chunk:
                                    break
                                await f1.write(chunk)
                                progress.update(len(chunk))
                            progress.close()
        elif isinstance(postinfo, list) and all(isinstance(item, tuple) for item in postinfo):
            filename = f"redditvideo-{str(datetime.now().timestamp()).replace('.', '')}.mp4"
            async def download(link: str, filename: str, progress: tqdm, session: aiohttp.ClientSession):
                while True:
                    try:
                        async with session.get(link) as response:
                            async with aiofiles.open(filename, 'wb') as f1:
                                while True:
                                    chunk = await response.content.read(1024)

                                    if not chunk:
                                        break
                                    await f1.write(chunk)
                                    progress.update(len(chunk))
                            return
                    except aiohttp.client_exceptions.ServerTimeoutError:
                        continue

            timeout = aiohttp.ClientTimeout(total=None, sock_read=3, sock_connect=3)
            async with aiohttp.ClientSession(timeout=timeout, connector=redditdownloader.makeconnector(proxy)) as session:
                for url, audiourl in postinfo:
                    totalsize = 0
                    while True:
                        try:
                            async with session.get(url, timeout=3) as r:
                                totalsize += int(r.headers.get('content-length'))
                            async with session.get(audiourl) as r:
                                totalsize += int(r.headers.get('content-length'))
                            break
                        except asyncio.exceptions.TimeoutError:
                            print('rate limited, waiting 5 seconds...')
                            await asyncio.sleep(5)
                            continue

                        
                    if maxsize:
                        if totalsize/(1024*1024) > maxsize:
                            continue
                    progress = tqdm(total=totalsize, unit='iB', unit_scale=True, colour='red')
                    tasks = [download(url, url.split('/')[-1], progress, session), download(audiourl, audiourl.split('/')[-1], progress, session)]
                    await asyncio.gather(*tasks)
                    progress.close()
                    process = await asyncio.subprocess.create_subprocess_exec(*f"ffmpeg -i {url.split('/')[-1]} -i {audiourl.split('/')[-1]} -c copy -map 0:v:0 -map 1:a:0 -y {filename}".split(), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                    stdout, stderr = await process.communicate()
                    if maxsize:
                        if os.path.getsize(filename)/(1024*1024) >maxsize:
                            continue
                        else:
                            break
                    else:
                        break
        return filename, thetext  if not filenames else filenames, thetext
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='download videos and audios')
    parser.add_argument('link', type=str, help='link to the reddit post')
    parser.add_argument('--maxsize', '-s', type=int, help='maximum size of video')
    parser.add_argument("--proxy", type=str, help="proxy")
    args = parser.parse_args()
    print(asyncio.run(redditdownloader.download(args.link, args.maxsize, args.proxy)))