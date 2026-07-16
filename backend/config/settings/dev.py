from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

LOGGING['formatters']['json'] = {
    'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
}
