from pathlib import Path

from decouple import Config, Csv, RepositoryEnv

from settings.constants import ENV_ID_VARIABLE, LOCAL_ENV

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / "settings" / ".env"
config = Config(RepositoryEnv(str(ENV_FILE)))

ENV_ID = config(ENV_ID_VARIABLE, default=LOCAL_ENV)
SECRET_KEY = config("BLOG_SECRET_KEY")
ALLOWED_HOSTS = config("BLOG_ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())
DB_NAME = config("BLOG_DB_NAME", default="blog")
DB_USER = config("BLOG_DB_USER", default="postgres")
DB_PASSWORD = config("BLOG_DB_PASSWORD", default="")
DB_HOST = config("BLOG_DB_HOST", default="localhost")
DB_PORT = config("BLOG_DB_PORT", default="5432")
