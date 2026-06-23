import os

ROOT_PATH: str = os.getenv('ROOT_PATH', '/NaaVRE-workflow-service')
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
VERIFY_SSL: bool = os.environ.get("VERIFY_SSL", "true").lower() != "false"

BINDER_URL: str = os.environ["BINDER_URL"].rstrip("/")
# This API token can be configured by adding the following to the binderhub helm chart values:
# jupyterhub:
#   hub:
#     services
#       environment-service:
#         apiToken: <api token>
#     loadRoles:
#         binder-api-user:
#           services:
#             - environment-service
#           scopes:
#             - "access:services!service=binder"
BINDER_API_TOKEN: str = os.environ["BINDER_API_TOKEN"]
CATALOGUE_URL: str  = os.environ["CATALOGUE_URL"].rstrip("/")
