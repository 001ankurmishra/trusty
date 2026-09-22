import logging
import json
import traceback
import sys
from datetime import datetime, timezone

class JSONFormatter(logging.Formatter):
    """
    Format logs as structured JSON objects.
    """
    def format(self, record):
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        if record.exc_info:
            log_obj["exception"] = "".join(traceback.format_exception(*record.exc_info))
            
        if hasattr(record, "extra_info"):
            log_obj.update(record.extra_info)
            
        return json.dumps(log_obj)

def setup_logging():
    """
    Configure the root logger and FastAPI loggers to use the JSON format.
    """
    root_logger = logging.getLogger()
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    
    # Suppress verbose loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
