import os

from django.core.asgi import get_asgi_application

from settings.conf import ENV_ID
from settings.constants import SETTINGS_MODULES

os.environ.setdefault("DJANGO_SETTINGS_MODULE", SETTINGS_MODULES[ENV_ID])
application = get_asgi_application()
