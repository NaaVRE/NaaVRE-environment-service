import os

ROOT_PATH: str = os.getenv('ROOT_PATH', '/NaaVRE-workflow-service')
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
VERIFY_SSL: bool = (os.environ.get("VERIFY_SSL", "true").lower()
                    != "false")

BINDER_URL: str = os.environ["BINDER_URL"].rstrip("/")
# This API token can be configured by adding the following to the binderhub
# helm chart values:
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
#
# It is exposed through the NaaVRE-helm values at
# global.secrets.naavreEnvironmentService.jupyterhubApiToken
BINDER_API_TOKEN: str = os.environ["BINDER_API_TOKEN"]
CATALOGUE_URL: str = os.environ["CATALOGUE_URL"].rstrip("/")
# This API token is created by the catalogue service helm chart.
# It is exposed through the NaaVRE-helm values at
# global.secrets.naavreCatalogueService.auth.naavreEnvironmentSaToken
CATALOGUE_API_TOKEN: str = os.environ["CATALOGUE_API_TOKEN"]

CONFIG_FILE_PATH = os.getenv(
    'CONFIG_FILE_PATH',
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'configuration.json'
        )
    )
