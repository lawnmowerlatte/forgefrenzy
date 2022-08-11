""" This is a util function containing common patterns for scripts
>>> isinstance(log, CustomLogger)
True
>>> logging.OUTPUT
8
>>> log.output
<function CustomLogger.add_custom_levels.<locals>.custom_log_fn_wrapper.<locals>.custom_log_fn at 0x...>
>>> logging.DEBUGV
9
>>> log.debugv
<function CustomLogger.add_custom_levels.<locals>.custom_log_fn_wrapper.<locals>.custom_log_fn at 0x...>
>>> logging.ALERT
51
>>> log.alert
<function CustomLogger.add_custom_levels.<locals>.custom_log_fn_wrapper.<locals>.custom_log_fn at 0x...>
"""

import math
import builtins
import logging

from .imports import minimock, mock


class LoggerConfig:
    __default = logging.ERROR
    long_formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d %(levelname)-10.10s [%(name)s.%(module)s.%(funcName)s:%(lineno)d] %(message)s"
    )
    short_formatter = logging.Formatter("[%(levelname)-8.8s]  %(message)s")

    def __init__(self, log, default=None):
        self.log = log
        self.log.handlers = []
        self.name = self.log.name
        self.default = default or self.__default
        self.__level = self.default
        self.log.setLevel(0)

        self.__file_handler = None
        self.__console_handler = None

        self.null_handler = logging.NullHandler()
        self.log.addHandler(self.null_handler)

    @property
    def file_handler(self):
        if self.__file_handler is not None:
            return self.__file_handler

        self.__file_handler = logging.FileHandler(f"./{self.name}.log", encoding="utf8")
        self.__file_handler.setFormatter(self.long_formatter)
        self.__file_handler.setLevel(0)
        return self.__file_handler

    @property
    def console_handler(self):
        if self.__console_handler is not None:
            return self.__console_handler

        self.__console_handler = logging.StreamHandler()
        self.__console_handler.setFormatter(self.short_formatter)
        self.__console_handler.setLevel(self.level)
        return self.__console_handler

    def update(self, script):
        """Take an argparser object and look for logging related args to update the config"""
        # Enable console logging if any verbose options are selected
        if script.args.debugv or script.args.debug or script.args.console:
            self.console = True

        # Set a new default level if present in the script object
        try:
            self.default = script.default_level
        except AttributeError:
            pass

        if script.args.debugv:
            level = "DEBUGV"
        elif script.args.debug:
            level = "DEBUG"
        else:
            level = self.default

        self.level = level

        if script.args.log:
            log.config.file = True
        else:
            log.warning("No file logging enabled")

    @property
    def next(self):
        """Get next standard log level up
        >>> log.config.level = 9
        >>> log.config.level
        9
        >>> log.config.next
        10
        >>> log.config.level = 10
        >>> log.config.next
        20
        >>> log.config.level = 50
        >>> log.config.next
        50
        >>> log.config.level = 51
        >>> log.config.next
        51
        """
        next_level = math.ceil((self.level + 1) / 10) * 10

        # Get at least logging.INFO
        next_level = max(next_level, logging.DEBUG)
        # Get at most logging.CRITICAL
        next_level = min(next_level, logging.CRITICAL)
        # If log level is set higher than logging.CRITICAL, use that
        next_level = max(next_level, self.level)
        return next_level

    @property
    def effective(self):
        return self.log.getEffectiveLevel()

    @property
    def level(self):
        return self.__level

    @level.setter
    def level(self, level):
        if self.level != level:
            if isinstance(level, str):
                level = getattr(logging, level.upper())
            self.__level = level

            if self.__console_handler is not None:
                self.console_handler.setLevel(level)

            self.log.log(self.level, f"Log level set to {level}")

    def reset_level(self):
        self.level = self.default
        self.log.debug(f"Disabled debug debugging, reset to {self.default}")

    @property
    def console(self):
        return bool([h for h in self.log.handlers if not isinstance(h, logging.StreamHandler)])

    @console.setter
    def console(self, enable):
        if enable:
            self.log.addHandler(self.console_handler)
            self.log.alert(f"Enabled console logging at {logging.getLevelName(self.level)}")
        else:
            self.log.debug(f"Disabled console logging")
            self.log.handlers = [
                h for h in self.log.handlers if not isinstance(h, logging.StreamHandler)
            ]

    @property
    def file(self):
        return bool([h for h in self.log.handlers if not isinstance(h, logging.FileHandler)])

    @file.setter
    def file(self, enable):
        if enable:
            self.log.addHandler(self.file_handler)
            self.log.alert(
                f"Enabled file logging at {logging.getLevelName(self.file_handler.level)}"
            )
        else:
            self.log.handlers = [
                h for h in self.log.handlers if not isinstance(h, logging.FileHandler)
            ]


class CustomLogger(logging.getLoggerClass()):
    __config = None
    # Configure custom log levels
    custom_levels = [
        {"level": 51, "name": "alert"},
        {"level": 9, "name": "debugv"},
        {"level": 8, "name": "output"},
    ]

    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)
        self.config
        self.add_custom_levels()

    def add_custom_levels(self):
        for custom in self.custom_levels:

            def custom_log_fn_wrapper(level):
                """Generate a logger function for the given level
                >>> output = custom_log_fn_wrapper(52)
                >>> output
                <function custom_log_fn_wrapper.<locals>.custom_log_fn at 0x...>
                >>> log_dot_log = log.log
                >>> log.log = mock('log.log')
                >>> log.setLevel(logging.DEBUGV)
                >>> output("Test")
                Called log.log(8, 'Test')
                >>> log.log = log_dot_log
                """

                def custom_log_fn(message, *args, **kws):
                    # args = args or None
                    if self.isEnabledFor(level):
                        # Yes, logger takes its '*args' as 'args'.
                        self.log(level, message, *args, **kws)

                    if level == logging.OUTPUT:
                        builtins.print(message)

                return custom_log_fn

            logging.addLevelName(custom["level"], custom["name"].upper())
            setattr(self, custom["name"], custom_log_fn_wrapper(custom["level"]))
            setattr(logging, custom["name"].upper(), custom["level"])

    @property
    def config(self):
        if self.__config is not None:
            return self.__config

        self.__config = LoggerConfig(self)

        return self.__config


logging.setLoggerClass(CustomLogger)
logging.root = CustomLogger("root")
log = logging.getLogger()
