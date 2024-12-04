import logging

logger = logging.getLogger("dash_app")


class ConfigError(Exception):
    """
    Exception raised for errors in the config file

    :param message: error message
    :param hint: hint to solve the error
    """

    def __init__(self, message: str, hint: str = "") -> None:
        self.message = message
        self.hint = hint

    def __str__(self) -> str:
        return f"{self.message} Hint: {self.hint}"

    def __repr__(self) -> str:
        return f"ConfigError({self.message}, {self.hint})"

    def log(self) -> None:
        _log_error(self.message, self.hint, exception=self)


def _log_error(error: str, hint: str = "", exception=None) -> None:
    if exception:
        logger.exception(exception)
        return
    message = f"\033[91mERROR\033[0m {error}"

    if hint:
        message += "\n" + f"\033[92mHINT\033[0m {hint}"

    logger.error(message)


class ParserException(Exception):
    """Exception raised when a parser is not found"""


class NotNeeded(Exception):
    """Exception raised when a value is not needed."""
