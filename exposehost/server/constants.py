import logging
import sys

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(" Server ")
logger.info("Starting")

MAX_TIMEOUT = 5
DOMAIN_NAME = 'exposehost.local'
CURRENT_DOMAINS: set = set()