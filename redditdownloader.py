import aiohttp, asyncio, re, json, aiofiles, os
from html import unescape
from datetime import datetime
from tqdm.asyncio import tqdm
from bs4 import BeautifulSoup
class redditdownloader:
    async def main(link: str):
        patternvideo = r'packaged-media-json=\"{&quot;playbackMp4s&quot;:((.*?)}}}]})'
        patternmanifest = r'((https://v\.redd\.it/(?:.*?)/)HLSPlaylist\.m3u8\?(?:.*?))\"'
        headers = {
        'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Brave";v="116"',
        'Referer': 'https://www.reddit.com/',
        'sec-ch-ua-mobile': '?0',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'Range': 'bytes=0-',
        'sec-ch-ua-platform': '"Windows"',
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(link, headers=headers) as r:
                rtext = await r.text()
            mainurls = re.findall(patternvideo, rtext)
            manifesturls = re.findall(patternmanifest, rtext)
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
            
            elif patternmanifest:
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
                soup = BeautifulSoup(rtext, 'html.parser')
                urls = []
                ul_elements = soup.find_all('ul')  # Find all <ul> elements
                for index, ul in enumerate(ul_elements):
                    li_elements = ul.find_all('li', attrs={'slot': True})  # Find <li> elements with a 'slot' attribute
                    for li in li_elements:
                        img = li.find('img')  # Find the <img> element inside each <li>
                        if img:
                            src = img.get('src')  # Get the 'src' attribute of the <img>
                            urls.append(src)
                if len(urls) > 0:
                    return urls
                else:
                    patternimage = r'<shreddit-screenview-data(?:[\s\S]*?)data=\"(.*?)\"\n'
                    url = re.findall(patternimage, rtext)
                    url = json.loads(unescape(url[0]))
                    url = url['post']['url']
                    postinfo = url

        return postinfo
    async def download(link, maxsize: int = None):
        postinfo= await redditdownloader.main(link)
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
                    async with aiohttp.ClientSession() as session:
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
            filename = f'redditimage-{round(datetime.now().timestamp())}.png'
            async with aiofiles.open(filename, 'wb') as f1:
                async with aiohttp.ClientSession() as session:
                    async with session.get(postinfo) as r:
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
            async with aiohttp.ClientSession() as session:
                for index, url in enumerate(postinfo):
                    filename = f'redditimage-{round(datetime.now().timestamp())}-{index}.jpg'
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
                async with session.get(link) as response:
                    async with aiofiles.open(filename, 'wb') as f1:
                        while True:
                            chunk = await response.content.read(1024)
                            if not chunk:
                                break
                            await f1.write(chunk)
                            progress.update(len(chunk))
                    return


            async with aiohttp.ClientSession() as session:
                for url, audiourl in postinfo:
                    totalsize = 0
                    while True:
                        if not os.path.exists('proxycache.txt'):
                            proxyurl = 'https://gimmeproxy.com/api/getProxy?curl=true'
                            async with session.get(proxyurl) as proxies:
                                proxy = await proxies.text()
                        else:
                            async with aiofiles.open('proxycache.txt', 'r') as f1:
                                proxy = await f1.read()

                        try:
                            async with session.get(url, proxy = proxy, timeout=3) as r:
                                totalsize += int(r.headers.get('content-length'))
                            async with session.get(audiourl, proxy = proxy, timeout=3) as r:
                                totalsize += int(r.headers.get('content-length'))
                            async with aiofiles.open('proxycache.txt', 'w') as f1:
                                await f1.write(proxy)
                            break
                        except:
                            if os.path.exists('proxycache.txt'):
                                os.remove('proxycache.txt')
                            print('getting proxy failed, trying again...')
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
        return filename if not filenames else filenames
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='download videos and audios')
    parser.add_argument('link', type=str, help='link to the reddit post')
    parser.add_argument('--maxsize', '-s', type=int, help='maximum size of video')
    args = parser.parse_args()
    print(asyncio.run(redditdownloader.download(args.link, args.maxsize)))