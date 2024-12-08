from os import environ

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY: str = environ.get("SECRET_KEY")
GEOCODING_KEY: str = environ.get("GEOCODING_KEY")
URL_CONFIG: str = environ.get("URL_CONFIG")

if not GEOCODING_KEY:
    raise ValueError("GEOCODING_KEY is not set")

if not SECRET_KEY:
    raise ValueError("SECRET_KEY is not set")

if not URL_CONFIG:
    raise ValueError("FILE_PATH is not set")
