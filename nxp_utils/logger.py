import logging
import json
import sys
from datetime import datetime, timezone

class JsonFormatter(logging.Formatter):
    """Custom formatter to output logs in JSON format including 'extra' fields."""
    def format(self, record):
        # Base log record
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        
        # Add 'extra' fields. Standard attributes are filtered out.
        # We check the record's __dict__ for custom attributes.
        standard_attrs = [
            'args', 'asctime', 'created', 'exc_info', 'exc_text', 
            'filename',
            'funcName', 'levelname', 'levelno', 
            'lineno',
            'module', 'msecs',
            'message', 'msg', 'name', 'pathname', 'process', 'processName',
            'relativeCreated', 'stack_info', 'thread', 'threadName'
        ]
        non_standard_attrs = ['taskName']

        for key, value in record.__dict__.items():
            # Skip standard boring stuff
            if key in standard_attrs:
                continue
            if key in non_standard_attrs and value is None:
                continue
            log_record[key] = value

        return json.dumps(log_record)

class AssistantFilter(logging.Filter):
    """Injects 'assistant' as the taskName for all records."""
    def filter(self, record):
        record.taskName = "assistant"
        return True

def setup_logger(name: str) -> logging.Logger:
    """Configures and returns a logger with JSON formatting."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        # Default level
        logger.setLevel(logging.INFO)
        
    return logger