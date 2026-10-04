import os
import sys
from pathlib import Path

from decouple import Config, RepositoryEnv

from django.core.management import execute_from_command_line

from settings.constants import ENV_ID_VARIABLE, LOCAL_ENV, SETTINGS_MODULES


def main() -> None:
    env_file = Path(__file__).resolve().parent / "settings" / ".env"
    env_config = Config(RepositoryEnv(str(env_file)))
    env_id = env_config(ENV_ID_VARIABLE, default=LOCAL_ENV)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", SETTINGS_MODULES[env_id])
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
