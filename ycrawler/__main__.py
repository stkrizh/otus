import argparse
import json

from pathlib import Path


DEFAULT_OUTPUT_DIR = "./Ynews/"
DEFAULT_REFRESH_TIME = 60


parser = argparse.ArgumentParser(
    description=(
        "Web crawler for 'news.ycombinator.com'. The program periodically "
        "looks for new articles from the site and stores articles to "
        "specific folder."
    )
)
parser.add_argument(
    "--output-dir",
    help=(
        "Path to directory to store downloaded articles. "
        f"[Default: {DEFAULT_OUTPUT_DIR}]"
    ),
    default=DEFAULT_OUTPUT_DIR,
)
parser.add_argument(
    "--refresh-time",
    type=int,
    help=(
        "Time in seconds to fetch new articles periodically. "
        f"[Default: {DEFAULT_REFRESH_TIME}]"
    ),
    default=DEFAULT_REFRESH_TIME,
)


if __name__ == "__main__":
    args = parser.parse_args()
    print(json.dumps(vars(args), indent=4, sort_keys=True))
