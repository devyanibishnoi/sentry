class SentryError(Exception):
    """Base class for all errors raised by the Sentry toolchain."""


class LexError(SentryError):
    def __init__(self, message: str, line: int, column: int):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"{message} (line {line}, column {column})")


class ParseError(SentryError):
    def __init__(self, message: str, line: int, column: int):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"{message} (line {line}, column {column})")
