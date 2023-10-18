from os import environ

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = environ.get("SECRET_KEY")
GEOCODING_KEY = environ.get("GEOCODING_KEY")
FILE_PAHT = environ.get("FILE_PAHT")

if not GEOCODING_KEY:
    raise ValueError("GEOCODING_KEY is not set")

if not SECRET_KEY:
    raise ValueError("SECRET_KEY is not set")

if not FILE_PAHT:
    raise ValueError("FILE_PAHT is not set")
