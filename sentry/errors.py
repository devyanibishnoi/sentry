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


class SemanticError(SentryError):
    def __init__(self, message: str, line: int = None, column: int = None):
        self.message = message
        self.line = line
        self.column = column
        if line is not None:
            super().__init__(f"{message} (line {line}, column {column})")
        else:
            super().__init__(message)


class InterpreterError(SentryError):
    def __init__(self, message: str, line: int = None, column: int = None):
        self.message = message
        self.line = line
        self.column = column
        if line is not None:
            super().__init__(f"{message} (line {line}, column {column})")
        else:
            super().__init__(message)
