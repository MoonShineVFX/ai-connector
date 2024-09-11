from job import api, forge_api
from loguru import logger
from time import sleep
from db import RedisDatabase


def check_webui_alive():
    try:
        api.get_queue_status()
        if forge_api is not None:
            forge_api.get_queue_status()
        return True

    except Exception as e:
        return False


def restart_webui(db: RedisDatabase):
    db.update_worker_status("RESTART")

    try:
        api.restart_server()
        if forge_api is not None:
            forge_api.restart_server()
    except:
        pass

    sleep(3)  # Wait for webui to close

    is_webui_running = False
    while not is_webui_running:
        is_webui_running = check_webui_alive()
        if not is_webui_running:
            logger.info("Waiting for webui to restart...")
            sleep(5)

    logger.info("WebUI restarted")
