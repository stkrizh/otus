### YCrawler
A Web Crawler for [Hacker News](https://news.ycombinator.com/) with asyncio coroutines

### The Task
Crawler finds and downloads all articles from the [Hacker News](https://news.ycombinator.com/) index page. Beginning with a base URL, it fetches each article and its comments, parses it for links, and download to specified directory. Crawler works in background and periodically checks the index page for new articles.

### Requirements
* Python (3.7+)
* aiohttp
* aiofiles

### Installation
```
git clone https://github.com/stkrizh/otus.git
cd otus
pip install -r ycrawler/requirements.txt
```

### To get help
```bash
python3.7 -m ycrawler --help

usage: python -m ycrawler [-h] [--output-dir OUTPUT_DIR]
                          [--refresh-time REFRESH_TIME] [--debug]

Web crawler for 'news.ycombinator.com'. The program periodically looks for new
articles from the site and stores articles to specific folder.

optional arguments:
  -h, --help            show this help message and exit
  --output-dir OUTPUT_DIR
                        Path to directory to store downloaded articles.
                        [Default: ./hacker-news/]
  --refresh-time REFRESH_TIME
                        Time in seconds to fetch new articles periodically.
                        [Default: 60]
  --debug               Show debug messages.
```


### Run
```bash
python3.7 -m ycrawler
```
