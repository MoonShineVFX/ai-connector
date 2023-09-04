import webuiapi
from db import RedisDatabase
from loguru import logger
from bunny import upload_bunny
import requests
from payload import normalize_payload
from settings import Settings

api = webuiapi.WebUIApi(port=Settings.A1111_PORT)
db = RedisDatabase()

if __name__ == "__main__":
    while True:
        logger.info("Waiting for job...")

        job = db.get_job()
        if job is None:
            logger.warning("No job found")
            continue

        job_id, job = job

        logger.info(f"Processing [{job.type}]: {job_id}")
        try:
            normalize_payload(job.payload)

            result = None

            if job.type == "TXT2IMG":
                result = api.txt2img(
                    **job.payload,
                )
            elif job.type == "IMG2IMG":
                result = api.img2img(
                    **job.payload,
                )
            elif job.type == "EXTRA":
                result = api.extra_single_image(
                    **job.payload,
                )

            if result is None:
                raise Exception("No result returned")

            # Upload to BunnyCDN
            result.images = upload_bunny(result.images, job.format)

            # Close job
            result = {
                "images": result.images,
                "info": result.info,
            }
            db.close_job(
                job_id,
                result,
            )

            logger.info(f"Done job {job_id}")

        except Exception as e:
            logger.error(f"Error: {e}")
            result = {"error": str(e)}
            db.close_job(job_id, result, is_failed=True)

        # Webhook
        if job.webhook:
            webhookBody = {
                "id": job_id,
            }
            try:
                requests.post(
                    job.webhook,
                    json={
                        "id": job_id,
                        **result,
                    },
                    timeout=3,
                )
            except Exception as e:
                logger.warning(f"Webhook failed: {e}")
