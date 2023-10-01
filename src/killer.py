import signal
from loguru import logger


class GracefulKiller:
    is_exit = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.__exit_gracefully)
        signal.signal(signal.SIGTERM, self.__exit_gracefully)

    def __exit_gracefully(self, signum, frame):
        logger.info(
            "Received exist signal, waiting for current job to finish..."
        )
        self.is_exit = True
