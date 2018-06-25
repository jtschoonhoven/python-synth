class SynthError(Exception):
    """
    Generic error raised by library.
    """
    pass


class SynthValidationError(SynthError):
    """
    Raised on attribute validation failure.
    """
    pass
