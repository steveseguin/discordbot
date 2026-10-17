import logging
import sys


class MetadataOnlyFormatter(logging.Formatter):
    """Keep diagnostic locations and error types, never message text or values."""

    def format(self, record):
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        result = "[{}] [{}] {}:{} {}".format(
            timestamp, record.levelname, record.name, record.lineno, record.funcName
        )
        if record.exc_info and record.exc_info[0]:
            result += " error=" + record.exc_info[0].__name__
            tb = record.exc_info[2]
            while tb:
                result += " {}:{}".format(tb.tb_frame.f_code.co_name, tb.tb_lineno)
                tb = tb.tb_next
        return result


def configure_logging():
    # stdout/stderr can be persisted by the service manager too. Apply the
    # same content-free formatter to application and dependency diagnostics.
    handler = logging.StreamHandler()
    handler.setFormatter(MetadataOnlyFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    logging.captureWarnings(True)
    logging.raiseExceptions = False

    def exception_hook(exc_type, exc_value, traceback):
        root.critical("Unhandled exception", exc_info=(exc_type, exc_value, traceback))

    sys.excepthook = exception_hook
