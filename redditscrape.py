import requests, re, os
from typing import Literal
class non_async_requests:
    def __init__(self) -> None:
        import time, requests
        self.time = time
        self.requests = requests
        self.subredditpattern = re.compile(r"permalink=\"/r/(.*?)/comments/(?:.*?)/(?:.*?)/\"")
        self.linkspattern = r"href=\"(/r/hello/comments/(?:.*?)/(?:.*?)/)\""
        self.afterpattern = re.compile(r"more-posts-cursor=\"(.*?)\"")
    def make_request(self, headers: dict, params: dict, url: str) -> tuple[list[str], str]:
        response = self.session.get(
        url,
        params=params,
        headers=headers,
        )
        status = response.status_code
        response = response.text
        with open("response.txt", "w", encoding='utf-8') as f1:
            f1.write(response)
        links = []
        try:
            subreddit = re.findall(self.subredditpattern, response)[0]
        except:
            print(response)
            print(status)
        linksmatches = re.findall(self.linkspattern.replace("hello", subreddit), response)
        for link in linksmatches:
            if "https://reddit.com" + link in links or link in links:
                continue
            if not link.startswith("https://reddit.com"):
                links.append("https://reddit.com" + link)
            else:
                links.append(link)
        after = re.findall(self.afterpattern, response)[0]
        return links, after
    def get_links(self, sort_posts: Literal['top', 'hot', 'new'], subreddit: str, time_range: Literal["ALL", "DAY", "WEEK", "MONTH", "YEAR", None] = None,
                amount: int = 25, session: requests.Session = None):
        if not session:
            session = self.requests.Session()
            self.session = session
        headers = {
            'authority': 'www.reddit.com',
            'accept': 'text/vnd.reddit.partial+html, text/html;q=0.9',
            'accept-language': 'en-US,en;q=0.8',
            'content-type': 'application/x-www-form-urlencoded',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Brave";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sec-gpc': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        params = {
            't': time_range if sort_posts != "new" and sort_posts != "hot" else "DAY",
            'name': subreddit,
            'feedLength': '25',
        }
        print(params)

        links, after = self.make_request(headers, params, f'https://www.reddit.com/svc/shreddit/community-more-posts/{sort_posts}/')
        while len(links) < amount:
            params = {
                't': time_range if sort_posts != "new" and sort_posts != "hot" else "DAY",
                'name': subreddit,
                'feedLength': len(links)+25,
                'after': after + "=="
            }
            print(params)
            a, aft = self.make_request(headers, params, f'https://www.reddit.com/svc/shreddit/community-more-posts/{sort_posts}/')
            for link in a:
                if "https://reddit.com" + link in links or link in links:
                    continue
                if not link.startswith("https://reddit.com"):
                    links.append("https://reddit.com" + link)
                else:
                    links.append(link)
            after = aft
        return links[:amount]
    ##example  
    def get_newest_posts(self, subreddit: str, delay: float, session: requests.Session = None, amount: int = 5):
        if not session:
            session = self.requests.Session()
        self.session = session
        while True:
            links = self.get_links('new', subreddit, amount=amount, time_range='ALL')
            if os.path.exists("cache.txt"):
                with open("cache.txt", "r") as f1:
                    cache = f1.read().split("\n")
                    newlinks = []
                    for link in links:
                        if link not in cache:
                            newlinks.append(link)
                    links = newlinks
            if links:
                with open("cache.txt", "a") as f1:
                    f1.write("\n".join(links))
                    f1.write("\n")
            for link in links:
                yield link
            self.time.sleep(delay)
class async_requests:
    def __init__(self) -> None:
        import aiohttp, aiofiles, asyncio
        self.aiohttp = aiohttp
        self.aiofiles = aiofiles
        self.asyncio = asyncio
        self.subredditpattern = re.compile(r"permalink=\"/r/(.*?)/comments/(?:.*?)/(?:.*?)/\"")
        self.linkspattern = r"href=\"(/r/hello/comments/(?:.*?)/(?:.*?)/)\""
        self.afterpattern = re.compile(r"more-posts-cursor=\"(.*?)\"")
    async def make_request(self, headers: dict, params: dict, url: str) -> tuple[list[str], str]:
        async with self.session.get(url, params=params, headers=headers) as response:
            status = response.status
            response = await response.text('utf-8')

        async with self.aiofiles.open("response.txt", "w", encoding='utf-8') as f1:
            await f1.write(response)
        links = []
        try:
            subreddit = re.findall(self.subredditpattern, response)[0]
        except:
            print(response)
            print(status)
        linksmatches = re.findall(self.linkspattern.replace("hello", subreddit), response)
        for link in linksmatches:
            if "https://reddit.com" + link in links or link in links:
                continue
            if not link.startswith("https://reddit.com"):
                links.append("https://reddit.com" + link)
            else:
                links.append(link)
        after = re.findall(self.afterpattern, response)[0]
        return links, after
    async def _get_links(self, sort_posts: Literal['top', 'hot', 'new'], subreddit: str, time_range: Literal["ALL", "DAY", "WEEK", "MONTH", "YEAR", None] = None,
                amount: int = 25):
        headers = {
            'authority': 'www.reddit.com',
            'accept': 'text/vnd.reddit.partial+html, text/html;q=0.9',
            'accept-language': 'en-US,en;q=0.8',
            'content-type': 'application/x-www-form-urlencoded',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Brave";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sec-gpc': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        params = {
            't': time_range if sort_posts != "new" and sort_posts != "hot" else "DAY",
            'name': subreddit,
            'feedLength': '25',
        }
        print(params)

        links, after = await self.make_request(headers, params, f'https://www.reddit.com/svc/shreddit/community-more-posts/{sort_posts}/')
        while len(links) < amount:
            params = {
                't': time_range if sort_posts != "new" and sort_posts != "hot" else "DAY",
                'name': subreddit,
                'feedLength': len(links)+25,
                'after': after + "=="
            }
            print(params)
            a, aft = await self.make_request(headers, params, f'https://www.reddit.com/svc/shreddit/community-more-posts/{sort_posts}/')
            for link in a:
                if "https://reddit.com" + link in links or link in links:
                    continue
                if not link.startswith("https://reddit.com"):
                    links.append("https://reddit.com" + link)
                else:
                    links.append(link)
            after = aft
        return links[:amount]
    async def get_links(self, sort_posts: Literal['top', 'hot', 'new'], subreddit: str, time_range: Literal["ALL", "DAY", "WEEK", "MONTH", "YEAR", None] = None,
                amount: int = 25, session = None):
        if not session:
            async with self.aiohttp.ClientSession() as session:
                self.session = session
                return await self._get_links(sort_posts, subreddit, time_range,amount)
        else:
            return await self._get_links(sort_posts, subreddit, time_range, amount)
    async def _get_newest_posts(self, subreddit: str, delay: float, amount: int = 5):
        while True:
            links = self.get_links('new', subreddit, amount=amount, time_range='ALL')
            if os.path.exists("cache.txt"):
                async with self.aiofiles.open("cache.txt", "r") as f1:
                    cache = await f1.read()
                    cache = cache.split("\n")
                    newlinks = []
                    for link in links:
                        if link not in cache:
                            newlinks.append(link)
                    links = newlinks
            if links:
                async with self.aiofiles.open("cache.txt", "a") as f1:
                    await f1.write("\n".join(links))
                    await f1.write("\n")
            for link in links:
                yield link
            await self.asyncio.sleep(delay)
    async def get_newest_posts(self, subreddit: str, delay: float, session = None):
        if not session:
            async with self.aiohttp.ClientSession() as session:
                self.session = session
                async for link in self._get_newest_posts(subreddit, delay):
                    yield link
        else:
            async for link in self._get_newest_posts(subreddit, delay):
                yield link
async def async_main():
    async for link in async_requests().get_newest_posts("okbuddyblacklung", 60*60*2):
        print(link)
def non_async_main():
    for link in non_async_requests().get_newest_posts("okbuddyblacklung", 5):
        print(link)
if __name__ == "__main__":
    non_async_main()
    # import asyncio
    # asyncio.run(async_main())