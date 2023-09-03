import webuiapi
from db import RedisDatabase
from loguru import logger

api = webuiapi.WebUIApi()
db = RedisDatabase()

if __name__ == "__main__":
    while True:
        logger.info("Waiting for job...")

        job = db.get_job()
        if job is None:
            logger.warning("No job found")
            continue

        job_id, job = job

        if job.model is not None:
            logger.debug(f"Setting model to {job.model}")
            api.util_set_model(job.model)

        logger.info(f"Processing [{job.type}]: {job_id}")
        logger.debug(f"Payload: {job.payload}")

        try:
            if job.type == "TXT2IMG":
                logger.debug("Generating image...")
                result = api.txt2img(
                    **job.payload,
                )

                logger.debug("Saving image...")
                image_url = f"source/{job_id}.png"
                result.image.save(image_url)
                db.done_job(job_id, {"image_url": image_url})

            elif job.type == "IMG2IMG":
                logger.debug("Generating image...")
                result = api.img2img(
                    **job.payload,
                )

                logger.debug("Saving image...")
                image_url = f"source/{job_id}.png"
                result.image.save(image_url)
                db.done_job(job_id, {"image_url": image_url})

            elif job.type == "EXTRA":
                logger.debug("Generating image...")
                result = api.extra_single_image(
                    **job.payload,
                )

                logger.debug("Saving image...")
                image_url = f"source/{job_id}.png"
                result.image.save(image_url)
                db.done_job(job_id, {"image_url": image_url})

            logger.info(f"Done job {job_id}")

        except Exception as e:
            logger.error(f"Error: {e}")
            db.fail_job(job_id, str(e))
