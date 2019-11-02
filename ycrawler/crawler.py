import asyncio
import logging
import random
import re

from dataclasses import dataclass, field
from html import unescape
from typing import List

import aiohttp


logging.basicConfig(
    format="%(asctime)s %(levelname)s:%(name)s: %(message)s",
    level=logging.DEBUG,
    datefmt="%H:%M:%S",
)


BASE_URL = "https://news.ycombinator.com/"
LIMIT_PER_HOST_CONNECTIONS = 3
RE_COMMENT_LINK = re.compile(r'<span class="commtext.+?<a href="(.+?)"')
RE_STORY_LINK = re.compile(
    r"<tr class=\'athing\' id=\'(\d+)\'>\n.+?"
    r'<a href="(.+?)" class="storylink".*?>(.+?)</a>'
)
RETRY_MAX_ATTEMPTS = 5


@dataclass
class YStory:
    id: int
    url: str
    slug: str
    comments_urls: List = field(default_factory=list)
    comments_parsed: bool = False


async def fetch_html(session: aiohttp.ClientSession, url: str) -> str:
    """ Doc
    """
    async with session.get(url) as response:
        logging.debug(f"Got response {response.status} for URL: {url}")
        response.raise_for_status()
        html = await response.text()
        return response.status, html


async def parse_stories(session: aiohttp.ClientSession) -> List[YStory]:
    """ Doc
    """
    stories: List[YStory] = []

    try:
        status, html = await fetch_html(session, BASE_URL)
    except Exception:
        logging.exception(f"An exception occurred while parsing {BASE_URL}")
        return stories

    for story_id, story_url, story_title in RE_STORY_LINK.findall(html):
        stories.append(
            YStory(
                id=int(story_id),
                url=unescape(story_url),
                slug=re.sub("\W", "_", story_title),
            )
        )

    logging.info(f"Found {len(stories)} stories")
    return stories


async def parse_urls_in_comments(
    session: aiohttp.ClientSession, story: YStory
) -> None:
    """ Doc
    """
    max_attempts = RETRY_MAX_ATTEMPTS
    url = f"{BASE_URL}item?id={story.id}"

    for attempt in range(1, max_attempts + 1):
        try:
            status, html = await fetch_html(session, url)
        except Exception:
            logging.debug(f"An exception occurred while parsing {url}")
            await asyncio.sleep(0.5 + 2 * random.random())
            continue
        break
    else:
        logging.info(f"Could not fetch {url}")
        return None

    story.comments_urls.extend(
        unescape(url) for url in re.findall(RE_COMMENT_LINK, html)
    )
    story.comments_parsed = True


async def main():
    connector = aiohttp.TCPConnector(limit_per_host=LIMIT_PER_HOST_CONNECTIONS)
    async with aiohttp.ClientSession(connector=connector) as session:
        stories: List[YStory] = await parse_stories(session)
        tasks = (parse_urls_in_comments(session, story) for story in stories)
        await asyncio.gather(*tasks)

        for item in stories:
            print(
                item.id,
                item.url,
                item.slug,
                item.comments_parsed,
                sep="\n",
                end="\n\n",
            )
            for url in item.comments_urls:
                print(f"    {url}")
            print("\n\n")
