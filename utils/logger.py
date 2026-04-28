import logging
import datetime

logging.basicConfig(
    filename='log/events.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Обёртки для логирования
def log_info(content):
    logging.info(content)
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {content}")

def log_warning(content):
    logging.warning(content)
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] {content}")

def log_error(content):
    logging.error(content)
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] {content}")

def log_debug(content):
    logging.debug(content)
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [DEBUG] {content}")

if __name__ == "__main__":
    log_info("Test info")
    log_warning("Test warning")
