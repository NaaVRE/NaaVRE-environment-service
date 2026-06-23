import os

ROOT_PATH = os.getenv('ROOT_PATH', '/NaaVRE-workflow-service')
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
VERIFY_SSL = os.environ.get("VERIFY_SSL", "true").lower() != "false"

BINDER_URL = os.environ["BINDER_URL"].rstrip("/")
CATALOGUE_URL = os.environ["CATALOGUE_URL"].rstrip("/")
