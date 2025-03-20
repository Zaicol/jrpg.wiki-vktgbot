"""
Telegram Bot for automated reposting from VKontakte community pages
to Telegram channels.

v3.1
by @alcortazzo
"""

import time

from loguru import logger

from config import SINGLE_START, TIME_TO_SLEEP
from start_script import start_script
from tools import prepare_temp_folder, authors

logger.add(
    "./logs/debug.log",
    format="{time} {level} {message}",
    level="DEBUG",
    rotation="1 week",
    compression="zip",
)

logger.info("Script is started.")
# №open("./last_id.txt", "w").write("163715") # 163715 163846


@logger.catch
def main():
    # Reading authors from the csv
    with open("authors.csv", "r") as file:
        for line in file.readlines():
            authors[line.split(",")[0]] = "t.me/" + line.split(",")[1].replace("\n", "")
    start_script()
    prepare_temp_folder()


while True:
    try:
        main()
        if SINGLE_START:
            logger.info("Script has successfully completed its execution")
            exit()
        else:
            logger.info(f"Script went to sleep for {TIME_TO_SLEEP} seconds.")
            time.sleep(TIME_TO_SLEEP)
    except KeyboardInterrupt:
        logger.info("Script is stopped by the user.")
        exit()
