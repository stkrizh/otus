import argparse
import asyncio
import logging

from pathlib import Path

from . import crawler


DEFAULT_OUTPUT_DIR = "./hacker-news/"
DEFAULT_REFRESH_TIME = "60"


def prepare_output_dir(raw_output_dir: str) -> Path:
    """ Validate the value of `--output-dir` command line argument.
    """
    try:
        output_dir = Path(raw_output_dir).resolve()
        output_dir.mkdir(exist_ok=True, parents=True)
    except RuntimeError:
        raise argparse.ArgumentTypeError("Invalid path to output directory.")
    except OSError:
        raise argparse.ArgumentTypeError("Could not create output directory.")

    return output_dir


def prepare_refresh_time(raw_refresh_time: str) -> int:
    """ Validate the value of `--refresh-time` command line argument.
    """
    try:
        refresh_time = int(raw_refresh_time)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "Refresh time must be a positive integer."
        )

    if refresh_time < 0:
        raise argparse.ArgumentTypeError(
            "Refresh time must be a positive integer."
        )

    return refresh_time


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
    type=prepare_output_dir,
)
parser.add_argument(
    "--refresh-time",
    help=(
        "Time in seconds to fetch new articles periodically. "
        f"[Default: {DEFAULT_REFRESH_TIME}]"
    ),
    default=DEFAULT_REFRESH_TIME,
    type=prepare_refresh_time,
)
parser.add_argument(
    "--debug", action="store_true", help="Show debug messages.", default=False
)


if __name__ == "__main__":
    args = parser.parse_args()
    output_dir: Path = args.output_dir
    refresh_time: int = args.refresh_time

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="[%(asctime)s] %(levelname).1s %(message)s",
        datefmt="%Y.%m.%d %H:%M:%S",
    )

    try:
        asyncio.run(crawler.main(output_dir, refresh_time))
    except KeyboardInterrupt:
        logging.info("Crawler has stopped")
