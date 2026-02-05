import logging
from logging import Logger
from .logger import setup_logger
import sys
from .dts.builder import DeviceTreeSourceBuilder


class Assistant:

    def __init__(self, name: str):
        self.log: Logger = setup_logger(name)

        # Add a default handler if none exists (prevents "No handler found" errors)
        if not self.log.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.log.addHandler(handler)

    def set_log_level(self, level: str):
        """Sets the logging level based on a string input."""
        log: Logger = self.log
        numeric_level = getattr(logging, level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f'Invalid log level: {level}')
        log.setLevel(numeric_level)
        log.debug(f"Log level set to {level.upper()}")

    def run(self, **kwargs) -> bool:
        log: Logger = self.log
        log.debug("running assistant", extra=kwargs)

        if kwargs.get("action") == "build_dts":
            builder = DeviceTreeSourceBuilder(logger=self.log, **kwargs)
            return builder.build()
        elif kwargs.get("action") == "query_dts":
            builder = DeviceTreeSourceBuilder(logger=self.log, **kwargs)
            return builder.query()
        
        raise Exception(f"No valid action specified in run command. Got: {kwargs.get("action")}")
