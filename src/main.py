from db import RedisDatabase
from loguru import logger
from killer import GracefulKiller
import traceback
from defines import CommandType
from utils import restart_webui, check_webui_alive
from time import sleep


if __name__ == "__main__":
    db = RedisDatabase()
    killer = GracefulKiller()

    is_waiting_for_webui_alive = False
    is_previous_signal_received = True

    while True:
        # Check exit
        if killer.is_exit:
            break

        # Check webui alive
        is_alive = check_webui_alive()
        if not is_alive:
            if not is_waiting_for_webui_alive:
                db.update_worker_status("DISCONNECTED")
                logger.error("WebUI is not alive, Waiting...")
                is_waiting_for_webui_alive = True
            sleep(5)
            continue
        if is_waiting_for_webui_alive:
            logger.info("WebUI is alive")

        is_waiting_for_webui_alive = False

        # Check signal
        if is_previous_signal_received:
            logger.info("<< Standby >>")
            is_previous_signal_received = False

        try:
            wait_result = db.wait_signal()
        except Exception as e:
            logger.error(f"Failed to wait signal: {e}")
            logger.error(traceback.format_exc())
            continue
        if wait_result is None:
            continue

        # Signal received
        is_previous_signal_received = True
        signalType, payload, queue_key = wait_result
        db.update_worker_status("PROCESSING")

        # Command
        if signalType == "COMMAND":
            logger.info(f"Received command: {payload}")
            command: CommandType = payload

            if command == "STOP":
                break

            if command == "RESTART_WEBUI":
                restart_webui(db)

            if command == "FLUSH_QUEUE":
                db.flush_queue()

        # Queue
        if signalType == "JOB":
            logger.info(f"Received job: {payload}")

            try:
                job = db.get_job(payload, queue_key)
                if job is None:
                    logger.warning("No job found or failed to get job")
                    continue
            except:
                logger.error(traceback.format_exc())
                continue

            # Run
            is_success = job.generate()
            if not is_success:
                restart_webui(db)
                continue

            is_success = job.postprocess()
            if not is_success:
                restart_webui(db)
                continue

            job.close()

    logger.info("Exiting...")
    db.close()
