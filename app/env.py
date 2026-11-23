import json
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
        filename = os.getenv(
            'CONFIG_FILE_PATH',
            './configuration.json'
            )
        if not os.path.isabs(filename):
            filename = os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                filename
                )
        return filename

    @property
    def IMAGE_PULLER_NAMESPACE(self) -> str:
        return os.environ["IMAGE_PULLER_NAMESPACE"]

    @property
    def IMAGE_PULLER_NAME(self) -> str:
        return os.environ["IMAGE_PULLER_NAME"]

    @property
    def IMAGE_PULLER_PAUSE_IMAGE(self) -> str:
        return os.environ["IMAGE_PULLER_PAUSE_IMAGE"]

    @property
    def IMAGE_PULL_SECRETS(self) -> list[str]:
        image_pull_secrets = json.loads(
            os.getenv("IMAGE_PULL_SECRETS", "[]")
            )
        if (not isinstance(image_pull_secrets, list)
                or not all(
                    isinstance(secret, dict)
                    and isinstance(secret.get("name"), str)
                    for secret in image_pull_secrets
                    )):
            raise ValueError(
                "IMAGE_PULL_SECRETS must be a JSON array of objects "
                "with a string 'name' field"
                )
        return [secret["name"] for secret in image_pull_secrets]

    @property
    def IMAGE_PULLER_MATCH_NODE_PURPOSE(self) -> str:
        match_node_purpose = os.getenv(
            "IMAGE_PULLER_MATCH_NODE_PURPOSE", "prefer"
            )
        if match_node_purpose not in {"ignore", "prefer", "require"}:
            raise ValueError(
                "IMAGE_PULLER_MATCH_NODE_PURPOSE must be one of "
                "'ignore', 'prefer', or 'require'"
                )
        return match_node_purpose

    @property
    def IMAGE_REBUILDER_SERVICE_URL(self) -> str:
        """ URL of the environment service, as reached by the image
        rebuilder job (e.g. the in-cluster service URL) """
        return os.environ["IMAGE_REBUILDER_SERVICE_URL"].rstrip("/")

    @property
    def IMAGE_REBUILDER_TOKEN(self) -> str:
        """ Token used by the image rebuilder job to call the build route """
        return os.environ["IMAGE_REBUILDER_TOKEN"]

    @property
    def IMAGE_REBUILDER_WAIT_TIMEOUT(self) -> float:
        """ Time (in seconds) to wait for the catalogue and the environment
        service to become available """
        return float(os.getenv("IMAGE_REBUILDER_WAIT_TIMEOUT", "600"))

    @property
    def IMAGE_REBUILDER_WAIT_RETRY_INTERVAL(self) -> float:
        """ Interval (in seconds) between attempts to reach the catalogue and
        environment service """
        return float(os.getenv("IMAGE_REBUILDER_WAIT_RETRY_INTERVAL", "10"))

    @property
    def IMAGE_REBUILDER_BUILD_ATTEMPTS(self) -> int:
        """ Number of attempts for each build, in case the build stream is
        interrupted (builds reported as failed by Binder are not retried) """
        attempts = int(os.getenv("IMAGE_REBUILDER_BUILD_ATTEMPTS", "3"))
        if attempts < 1:
            raise ValueError("IMAGE_REBUILDER_BUILD_ATTEMPTS must be >= 1")
        return attempts
