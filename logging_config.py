import logging
import logging.handlers
import os
import time
from config import LOG_LEVEL, LOG_FILE

def setup_logging():
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(LOG_FILE)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)

    # Set up log formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Configure file output handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=10*1024*1024, backupCount=5  # 10 MB per file, keep 5 backup files
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Configure console output handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Configure loggers for different modules
    loggers = [
        "arbitrage_analysis", "collect_orderbooks", "fetch_data", 
        "find_common_coins", "spread_process_first", "spread_process_second", 
        "spread_process_third", "volatility"
    ]

    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(LOG_LEVEL)

    # Separate logger for execution time tracking
    time_logger = logging.getLogger("time_analysis")
    time_logger.setLevel(logging.DEBUG)
    time_handler = logging.FileHandler(os.path.join(log_dir, "time_analysis.log"))
    time_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    time_logger.addHandler(time_handler)

def log_execution_time(logger):
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            logger.debug(f"{func.__name__} executed in {end_time - start_time:.2f} seconds")
            return result
        return wrapper
    return decorator

# Example usage:
# @log_execution_time(logging.getLogger("time_analysis"))
# def some_function():
#     # Function implementation
#     pass

# Configure logger for critical errors
critical_logger = logging.getLogger("critical_errors")
critical_logger.setLevel(logging.CRITICAL)
critical_handler = logging.handlers.SMTPHandler(
    mailhost=("smtp.example.com", 587),
    fromaddr="bot@example.com",
    toaddrs=["admin@example.com"],
    subject="Critical Error in Arbitrage Bot",
    credentials=("username", "password"),
    secure=()
)
critical_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
critical_logger.addHandler(critical_handler)

# Example usage for critical error handling:
# try:
#     # Code execution
# except CriticalError as e:
#     critical_logger.critical(f"A critical error occurred: {str(e)}")

if __name__ == "__main__":
    setup_logging()
    logging.info("Logging system initialized")