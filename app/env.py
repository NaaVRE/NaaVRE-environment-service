import os

class Env:
    @property
    def ROOT_PATH(self) -> str:
        return os.getenv('ROOT_PATH', '/NaaVRE-workflow-service')
    @property
    def DEBUG(self) -> bool:
        return os.getenv("DEBUG", "false").lower() == "true"
    @property
    def VERIFY_SSL(self) -> bool:
        return (os.environ.get("VERIFY_SSL", "true").lower()
                        != "false")

    @property
    def BINDER_URL(self) -> str:
        return os.environ["BINDER_URL"].rstrip("/")
    @property
    def BINDER_API_TOKEN(self) -> str:
        """ This API token can be configured by adding the following to the
        binderhub helm chart values:
        jupyterhub:
          hub:
            services
              environment-service:
                apiToken: <api token>
            loadRoles:
                binder-api-user:
                  services:
                    - environment-service
                  scopes:
                    - "access:services!service=binder"

        It is exposed through the NaaVRE-helm values at
        global.secrets.naavreEnvironmentService.jupyterhubApiToken
        """
        return os.environ["BINDER_API_TOKEN"]
    @property
    def CATALOGUE_URL(self) -> str:
        return os.environ["CATALOGUE_URL"].rstrip("/")
    @property
    def CATALOGUE_API_TOKEN(self) -> str:
        """ This API token is created by the catalogue service helm chart.
        It is exposed through the NaaVRE-helm values at
        global.secrets.naavreCatalogueService.auth.naavreEnvironmentSaToken
        """
        return os.environ["CATALOGUE_API_TOKEN"]

    @property
    def CONFIG_FILE_PATH(self) -> str:
        return os.getenv(
        'CONFIG_FILE_PATH',
        os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'configuration.json'
            )
        )
