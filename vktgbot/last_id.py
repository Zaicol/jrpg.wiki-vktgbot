import datetime

from loguru import logger


def read_id() -> int:
    try:
        return int(open("./last_id.txt", "r").read())
    except ValueError:
        logger.critical(
            "The value of the last identifier is incorrect. Please check the contents of the file 'last_id.txt'."
        )
        exit()


def write_id(new_id: int) -> None:
    open("./last_id.txt", "w").write(str(new_id))
    logger.info(f"New ID, written in the file: {new_id}")


def write_time() -> None:
    time = datetime.datetime.now()
    open("./last_check.txt", "w+").write(str(time))
    logger.info(f"New time, written in the file: {time}")
