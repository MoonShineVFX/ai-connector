from db import RedisDatabase
from loguru import logger
import traceback


db = RedisDatabase()


if __name__ == "__main__":
    while True:
        # Queue
        logger.info("Waiting for job...")

        try:
            job = db.get_job()
            if job is None:
                logger.warning("No job found")
                continue
        except:
            logger.error(traceback.format_exc())
            continue

        # Run
        is_success = job.generate()
        if not is_success:
            continue

        is_success = job.postprocess()
        if not is_success:
            continue

        job.close()
        job.emit_webhook()
