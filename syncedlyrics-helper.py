#!/usr/bin/env python3

import argparse
import logging
from pathlib import Path
from tinytag import TinyTag, TinyTagException
from colorlog import ColoredFormatter
import syncedlyrics

class Downloader:
    def __init__(self, blacklisted_genres = []) -> None:
        self.f_unsuccessful_fetches = "unsuccessful_fetches.txt"
        self.unsuccessful_fetches = self.load_unsuccessful_fetches()
        self.blacklisted_genres = blacklisted_genres
        self.lyrics_providers = ["Deezer", "Lrclib", "NeatEase", "Megalobiz"]

    def load_unsuccessful_fetches(self):
        try:
            with open(self.f_unsuccessful_fetches, "r") as file:
                return set(file.read().split("\n"))
        except FileNotFoundError:
            return {}

    def write_unsuccessful_fetches_to_disk(self, track):
        with open(self.f_unsuccessful_fetches, "a") as file:
            file.write(f"{track}\n")

    def check_for_existing(self, keywords):
        if keywords in self.unsuccessful_fetches:
            log.info(f"Skipping {keywords} since it's been tried before")
            return True
        return False

    def check_for_blacklisted_genre(self, tags):
        for genre in self.blacklisted_genres:
            try:
                if genre.lower() in tags.genre.lower():
                    log.info(f"song {tags.title} was skipped because it was of the genre: {tags.genre}")
                    return True
            except AttributeError:
                pass
        return False

    def run(self, filename):
        try:
            tags = TinyTag.get(filename)
        except TinyTagException:
            log.debug(f"{filename} is not a song")
            return False

        title = tags.title
        keywords = f"{title} {tags.artist}"
        if self.check_for_existing(keywords) or self.check_for_blacklisted_genre(tags):
            return False

        lyrics = filename.with_suffix(".lrc")
        if lyrics.exists():
            log.info(f"{title} already has an associated lyrics file")
            return False
        log.info(f"Fetching lyrics for {title} ({tags.genre})")
        lrc = syncedlyrics.search(keywords, allow_plain_format=False, save_path=str(lyrics.resolve()), enhanced=False, providers=self.lyrics_providers)
        if not lrc:
            log.error(f"Couldn't find lyrics for {title}")
            self.write_unsuccessful_fetches_to_disk(f"{title} {tags.artist}")
            return False
        return True

class Crawler:
    def __init__(self, path, blacklisted_genres) -> None:
        self.success_count = 0
        self.downloader = Downloader(blacklisted_genres)
        self.recursive_download(Path(path))

    def recursive_download(self, path):
        if path.is_dir():
            for item in path.iterdir():
                if item.is_dir():
                    self.recursive_download(item)
                else:
                    self.download_lyrics(item)
        else:
            self.download_lyrics(path)

    def download_lyrics(self, path):
        if self.downloader.run(path):
            self.success_count += 1


parser = argparse.ArgumentParser(description="Download synced lyrics from NetEase Cloud Music")
required = parser.add_argument_group('Required arguments')
required.add_argument('-p', '--path', help='directory or filepath', required=True)
optional = parser.add_argument_group('Optional arguments')
optional.add_argument('-g', '--blacklisted_genres', nargs='+', help='blacklisted genres', required=False, default=[])
optional.add_argument('-l', '--log_level', help='log level (DEBUG, INFO, WARNING, ERROR)', required=False, default="INFO")
args = parser.parse_args()

log_dict = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR
}
LOG_LEVEL = log_dict.get(args.log_level.upper(), "INFO")
LOGFORMAT = "%(log_color)s%(levelname)-8s%(reset)s | %(log_color)s%(message)s%(reset)s"
logging.root.setLevel(LOG_LEVEL)
formatter = ColoredFormatter(LOGFORMAT)
stream = logging.StreamHandler()
stream.setLevel(LOG_LEVEL)
stream.setFormatter(formatter)
log = logging.getLogger('pythonConfig')
log.setLevel(LOG_LEVEL)
log.addHandler(stream)

cr = Crawler(args.path, args.blacklisted_genres)
print(f"🎷 Successfully downloaded {cr.success_count} .lrc files!")