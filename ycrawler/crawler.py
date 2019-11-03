import asyncio
import logging
import re

from functools import wraps
from html import unescape
from pathlib import Path
from typing import Coroutine, List, Optional, Tuple, Type

import aiofiles
import aiohttp

from .helpers import ignore_aiohttp_ssl_eror


logging.basicConfig(
    format="%(asctime)s %(levelname).1s: %(message)s",
    level=logging.INFO,
    datefmt="%H:%M:%S",
)


BASE_URL = "https://news.ycombinator.com/"
DOWNLOAD_CHUNK_SIZE_BYTES = 1024
DOWNLOAD_MAX_SIZE_MB = 3
LIMIT_PER_HOST_CONNECTIONS = 3
RE_COMMENT_LINK = re.compile(r'<span class="commtext.+?<a href="(.+?)"')
RE_STORY_LINK = re.compile(
    r"<tr class=\'athing\' id=\'(\d+)\'>\n.+?"
    r'<a href="(.+?)" class="storylink".*?>(.+?)</a>'
)
RETRY_MAX_ATTEMPTS = 3
RETRY_DELAY_SEC = 1
REQUEST_TIMEOUT = 30


class DownloadMaxSizeExceeded(Exception):
    pass


class Story:
    """ Class represents one news from the main hacker-news page.
    """

    def __init__(self, id: int, url: str, title: str):
        self.id = id
        self.url = url
        self.title = title
        self.urls_from_comments: List[str] = []
        self.comments_parsed_successfully: bool = False

    def __str__(self) -> str:
        return f"Story: {self.id}"

    @property
    def slug(self) -> str:
        return re.sub("\W", "_", self.title)

    @property
    def comments_url(self) -> str:
        return f"{BASE_URL}item?id={self.id}"

    async def parse_urls_from_comments(
        self, session: aiohttp.ClientSession
    ) -> None:
        """ Find URLs in story's comments.
        """
        try:
            status, html = await fetch(session, self.comments_url)
        except Exception:
            return None

        raw_urls: List[str] = re.findall(RE_COMMENT_LINK, html)
        logging.info(f"Found {len(raw_urls)} URLs in comments for {self}")

        self.urls_from_comments.extend(map(unescape, raw_urls))
        self.comments_parsed_successfully = True

    async def download(self, session: aiohttp.ClientSession, output_dir: Path):
        """ Download story and URLs from its comments to `output_dir`
        """
        await self.parse_urls_from_comments(session)

        story_dir: Path = output_dir / self.slug
        story_dir.mkdir()
        story_comments_dir: Path = story_dir / "comments"
        story_comments_dir.mkdir()

        if self.comments_parsed_successfully:
            tasks = {
                asyncio.create_task(
                    download(session, url, story_comments_dir)
                ): url
                for url in self.urls_from_comments
            }
            tasks[
                asyncio.create_task(download(session, self.url, story_dir))
            ] = self.url

            successfully_downloaded: int = 0

            for task in tasks:
                try:
                    await task
                except asyncio.TimeoutError:
                    logging.warning(f"URL: {tasks[task]} failed by timeout.")
                except aiohttp.ClientError as exc:
                    logging.warning(
                        f"URL: {tasks[task]} is unavailable ({exc})"
                    )
                except DownloadMaxSizeExceeded:
                    logging.warning(
                        f"URL: {tasks[task]} the file size exceeds the "
                        f"limit allowed and cannot be saved."
                    )
                except OSError:
                    logging.warning(
                        f"URL: {tasks[task]} could not write the file."
                    )
                except Exception as exc:
                    logging.warning(
                        f"URL: {tasks[task]} unexpected error. "
                        f"{type(exc)} was raised."
                    )
                else:
                    successfully_downloaded += 1

            logging.info(
                f"{self} has been downloaded "
                f"[{successfully_downloaded} of {len(tasks)}]"
            )

        else:
            logging.warning(
                f"{self} download has failed. "
                f"Could not fetch comments page."
            )


def retry(raise_immediately: Optional[Tuple[Type[Exception], ...]] = None):
    """ Decorator to retry coroutine `coro` if some exception occurs.
    """
    raise_immediately = () if raise_immediately is None else raise_immediately

    def decorator(coro: Coroutine):
        @wraps(coro)  # type: ignore
        async def wrapper(*args, **kwargs):
            raised = None
            for attempt in range(1, RETRY_MAX_ATTEMPTS + 1):
                try:
                    result = await coro(*args, **kwargs)
                except Exception as exc:
                    raised = exc
                    if isinstance(exc, raise_immediately):
                        break
                    logging.debug(
                        f"Coroutine: `{coro.__name__}` raised "
                        f"{type(exc)}({exc}) [Attempt: {attempt}]. "
                        f"Args: {args}. Kwargs: {kwargs}"
                    )
                    await asyncio.sleep(RETRY_DELAY_SEC)
                else:
                    return result
            raise raised

        return wrapper

    return decorator


@retry()
async def fetch(
    session: aiohttp.ClientSession, url: str, timeout: int = REQUEST_TIMEOUT
) -> Tuple[int, str]:
    """ Wrapper for sending GET-requests.

    Raises
    ------
    aiohttp.ClientError
        If HTTP-request returns status code >= 400.
    asyncio.TimeoutError
        If `timeout` time is exceeded during HTTP-request.
    """
    client_timeout = aiohttp.ClientTimeout(total=timeout)
    async with session.get(url, timeout=client_timeout) as response:
        logging.debug(f"Got response {response.status} for: {url}")
        response.raise_for_status()
        data = await response.text()
        return response.status, data


@retry(raise_immediately=(DownloadMaxSizeExceeded, OSError))
async def download(
    session: aiohttp.ClientSession,
    url: str,
    output_dir: Path,
    timeout: int = REQUEST_TIMEOUT,
) -> None:
    """ Download data from specified `url` to `output_dir` directory.

    Raises
    ------
    aiohttp.ClientError
        If HTTP-request returns status code >= 400.
    asyncio.TimeoutError
        If `timeout` time is exceeded during HTTP-request.
    DownloadMaxSizeExceeded
        If `DOWNLOAD_MAX_SIZE_MB` is excedeed.
    OSError
        If an error occurs during try to write file.
    """
    client_timeout = aiohttp.ClientTimeout(total=timeout)
    async with session.get(url, timeout=client_timeout) as response:
        logging.debug(f"Got response {response.status} for: {url}")
        response.raise_for_status()

        ext: str = response.content_type.split("/")[-1]
        filename: str = re.sub("\W", "_", url)
        output_path = output_dir / f"{filename}.{ext}"

        content: bytes = b""
        while True:
            chunk = await response.content.read(DOWNLOAD_CHUNK_SIZE_BYTES)
            if not chunk:
                break
            content += chunk
            if len(content) > DOWNLOAD_MAX_SIZE_MB * 2 ** 20:
                raise DownloadMaxSizeExceeded()

        async with aiofiles.open(output_path, "wb") as fd:
            await fd.write(content)

        logging.debug(
            f"URL: {url} has been successfully downloaded to {output_path}"
        )


async def parse_stories(session: aiohttp.ClientSession) -> List[Story]:
    """ Find URLs and additional info on the main page `BASE_URL`.
    """
    stories: List[Story] = []

    try:
        status, html = await fetch(session, BASE_URL)
    except Exception:
        logging.error(f"Could not fetch {BASE_URL}")
        return stories

    for story_id, story_url, story_title in RE_STORY_LINK.findall(html):
        stories.append(
            Story(id=int(story_id), url=unescape(story_url), title=story_title)
        )

    logging.info(f"Found {len(stories)} stories")
    return stories


async def main():
    """ Async entry point coroutine.
    """
    ignore_aiohttp_ssl_eror(asyncio.get_running_loop())

    output_dir = Path("/home/sk/Dev/async/")
    output_dir.mkdir(exist_ok=True, parents=True)

    connector = aiohttp.TCPConnector(
        limit_per_host=LIMIT_PER_HOST_CONNECTIONS, force_close=True
    )
    async with aiohttp.ClientSession(connector=connector) as session:
        stories: List[Story] = await parse_stories(session)
        tasks = (story.download(session, output_dir) for story in stories)
        await asyncio.gather(*tasks)
