import requests, re
from typing import Literal
def make_request(headers: dict, params: dict, url: str, subredditpattern: re.Pattern[str], linkspattern, afterpattern: re.Pattern[str], session: requests.Session) -> tuple[list[str], str]:
    response = session.get(
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
        subreddit = re.findall(subredditpattern, response)[0]
    except:
        print(response)
        print(status)
    linksmatches = re.findall(linkspattern.replace("hello", subreddit), response)
    for link in linksmatches:
        if "https://reddit.com" + link in links:
            continue
        links.append("https://reddit.com" + link)
    after = re.findall(afterpattern, response)[0]
    return links, after
def get_links(sort_posts: Literal['top', 'hot', 'new'], subreddit: str, time_range: Literal["ALL", "DAY", "WEEK", "MONTH", "YEAR", None] = None,
              amount: int = 25, session: requests.Session = None):
    if not session:
        session = requests.Session()
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

    subredditpattern = re.compile(r"permalink=\"/r/(.*?)/comments/(?:.*?)/(?:.*?)/\"")
    linkspattern = r"href=\"(/r/hello/comments/(?:.*?)/(?:.*?)/)\""
    afterpattern = re.compile(r"more-posts-cursor=\"(.*?)\"")
    links, after = make_request(headers, params, f'https://www.reddit.com/svc/shreddit/community-more-posts/{sort_posts}/', subredditpattern, linkspattern, afterpattern, session)
    while len(links) < amount:
        params = {
            't': time_range if sort_posts != "new" and sort_posts != "hot" else "DAY",
            'name': subreddit,
            'feedLength': len(links)+25,
            'after': after + "=="
        }
        print(params)
        a, aft = make_request(headers, params, f'https://www.reddit.com/svc/shreddit/community-more-posts/{sort_posts}/', subredditpattern, linkspattern, afterpattern, session)
        for link in a:
            if "https://reddit.com" + link in links:
                continue
            links.append("https://reddit.com" + link)
        after = aft
    return links
##example  
# if __name__ == "__main__":
#     links = get_links('top', 'stories', amount=25, time_range='ALL')
#     from redditdownloader import redditdownloader
#     import asyncio
#     import traceback
#     for link in links:
#         try:
#             print(asyncio.run(redditdownloader.download(link)))
#         except Exception as e:
#             traceback.print_exc()
#             print(link)
