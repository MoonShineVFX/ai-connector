from job import api
from loguru import logger
from time import sleep
from posthog import Posthog
from defines import Settings


def check_webui_alive():
    try:
        api.get_queue_status()
        return True

    except Exception as e:
        return False


def restart_webui():
    try:
        api.restart_server()
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


posthog = Posthog(Settings.POSTHOG_API_KEY, host=Settings.POSTHOG_HOST)
