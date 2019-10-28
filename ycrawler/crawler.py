import asyncio
import re

from html import unescape
from typing import List, NamedTuple

import aiohttp


BASE_URL = "https://news.ycombinator.com/"
RE_COMMENT_LINK = re.compile(r'<span class="commtext.+?<a href="(.+?)"')
RE_STORY_LINK = re.compile(
    r"<tr class=\'athing\' id=\'(\d+)\'>\n.+?"
    r'<a href="(.+?)" class="storylink">(.+?)</a>'
)


class YNews(NamedTuple):
    url: str
    id: int
    slug: str


async def fetch_news(session) -> List[YNews]:
    """ Doc
    """
    async with session.get(BASE_URL) as response:
        html = await response.text()
        news: List[YNews] = [
            YNews(
                url=unescape(link_url),
                id=int(link_id),
                slug=re.sub("\W", "_", link_title),
            )
            for link_id, link_url, link_title in re.findall(
                RE_STORY_LINK, html
            )
        ]

    return news


async def fetch_urls_from_comments(session, news_id: int) -> List[str]:
    """ Doc
    """
    async with session.get(f"{BASE_URL}item?id={news_id}") as response:
        html = await response.text()
        comments_urls: List[str] = [
            unescape(url) for url in re.findall(RE_COMMENT_LINK, html)
        ]

    return comments_urls


async def main():
    async with aiohttp.ClientSession() as session:
        news = await fetch_news(session)
        for item in news:
            comments_urls = await fetch_urls_from_comments(session, item.id)
            print(item.id, item.url, item.slug, sep="\n", end="\n\n")
            for url in comments_urls:
                print(f"    {url}")
            print("\n\n")
