from os import environ

import yaml

from edx_django_utils.plugins import add_plugins
from credentials.settings.base import *
from credentials.settings.utils import get_env_setting, get_logger_config
from credentials.apps.plugins.constants import PROJECT_TYPE, SettingsType

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ALLOWED_HOSTS = ["*"]

# Keep track of the names of settings that represent dicts. Instead of overriding the values in base.py,
# the values read from disk should UPDATE the pre-configured dicts.
DICT_UPDATE_KEYS = ("JWT_AUTH",)

EMAIL_BACKEND = "django_ses.SESBackend"
AWS_SES_REGION_NAME = environ.get("AWS_SES_REGION_NAME", "us-east-1")
AWS_SES_REGION_ENDPOINT = environ.get("AWS_SES_REGION_ENDPOINT", "email.us-east-1.amazonaws.com")

# Inject plugin settings before the configuration file overrides (so it is possible to manage those settings via environment).
add_plugins(__name__, PROJECT_TYPE, SettingsType.PRODUCTION)

CONFIG_FILE = get_env_setting("CREDENTIALS_CFG")
with open(CONFIG_FILE, encoding="utf-8") as f:
    config_from_yaml = yaml.safe_load(f)

    # Remove the items that should be used to update dicts, and apply them separately rather
    # than pumping them into the local vars.
    dict_updates = {key: config_from_yaml.pop(key, None) for key in DICT_UPDATE_KEYS}

    for key, value in list(dict_updates.items()):
        if value:
            vars()[key].update(value)

    vars().update(config_from_yaml)

    # Handle FILE_STORAGE_BACKEND for Django >=5.2
    file_storage_backend = config_from_yaml.pop("FILE_STORAGE_BACKEND", None)
    if file_storage_backend:
        # Get backend dynamically from YAML
        backend = file_storage_backend.pop("DEFAULT_FILE_STORAGE", None)

        # Remove DEFAULT_FILE_STORAGE (clean Django <5.2 remnants)
        if backend:
            STORAGES = {
                "default": {
                    "BACKEND": backend,
                    "OPTIONS": file_storage_backend,  # Remaining AWS_* options
                }
            }

        # Handle media root and URL
        media_root = file_storage_backend.pop("MEDIA_ROOT", None)
        media_url = file_storage_backend.pop("MEDIA_URL", None)

        if media_root:
            MEDIA_ROOT = media_root
        if media_url:
            MEDIA_URL = media_url

# make sure this happens after the configuration file overrides so format string can be overridden
LOGGING = get_logger_config(format_string=LOGGING_FORMAT_STRING)

if "EXTRA_APPS" in locals():
    INSTALLED_APPS += EXTRA_APPS

DB_OVERRIDES = dict(
    PASSWORD=environ.get("DB_MIGRATION_PASS", DATABASES["default"]["PASSWORD"]),
    ENGINE=environ.get("DB_MIGRATION_ENGINE", DATABASES["default"]["ENGINE"]),
    USER=environ.get("DB_MIGRATION_USER", DATABASES["default"]["USER"]),
    NAME=environ.get("DB_MIGRATION_NAME", DATABASES["default"]["NAME"]),
    HOST=environ.get("DB_MIGRATION_HOST", DATABASES["default"]["HOST"]),
    PORT=environ.get("DB_MIGRATION_PORT", DATABASES["default"]["PORT"]),
)

for override, value in DB_OVERRIDES.items():
    DATABASES["default"][override] = value
