import asyncio
import hashlib
import logging
from typing import Literal, TypeAlias, TypedDict

from kubernetes import client, config

from app import env
from app.services.catalogue import BinderEnvironmentResponse

logger = logging.getLogger(__name__)

DaemonsetSyncOutcome: TypeAlias = Literal["created", "updated"]


class DaemonsetSyncResult(TypedDict):
    outcome: DaemonsetSyncOutcome
    image_count: int


def _load_kube_config() -> None:
    """ Load in-cluster config """
    config.load_incluster_config()


def _image_pull_container_name(binder_ref: str) -> str:
    """ Build a short, unique, DNS-1123-safe name for a binder_ref

    binder_ref values (e.g. `gh/org/repo/ref`) are not safe container
    names, so we hash them, similarly to how z2jh names its per-image
    init containers.
    """
    digest = hashlib.sha256(binder_ref.encode()).hexdigest()[:16]
    return f"image-pull-{digest}"


def _build_daemonset(
        environments: list[BinderEnvironmentResponse],
        ) -> client.V1DaemonSet:
    """
    Render the continuous-image-puller DaemonSet.

    This follows the same pattern as z2jh's continuous image puller: a
    DaemonSet whose pods run one init container per image to pull (each
    an `imagePullPolicy: Always` no-op that exits immediately once the
    image is present on the node) followed by a single long-lived
    "pause" container.
    """
    labels = {
        "app": env.IMAGE_PULLER_NAME,
        "component": "image-puller",
        }

    init_containers = [
        client.V1Container(
            name=_image_pull_container_name(environment.binder_ref),
            image=environment.container_image,
            command=['sh', '-c', 'echo "Pulling complete"'],
            image_pull_policy="Always",
            )
        for environment in environments
        if environment.container_image
        ]

    pod_spec = client.V1PodSpec(
        init_containers=init_containers,
        containers=[
            client.V1Container(
                name="pause",
                image=env.IMAGE_PULLER_PAUSE_IMAGE,
                image_pull_policy="IfNotPresent",
                ),
            ],
        # Pull images on every node
        # FIXME: this needs to be tunable in a way compliant with
        # https://z2jh.jupyter.org/en/stable/administrator/optimization.html#using-a-dedicated-node-pool-for-users
        tolerations=[
            client.V1Toleration(operator="Exists"),
            ],
        automount_service_account_token=False,
        termination_grace_period_seconds=0,
        )

    return client.V1DaemonSet(
        api_version="apps/v1",
        kind="DaemonSet",
        metadata=client.V1ObjectMeta(
            name=env.IMAGE_PULLER_NAME,
            namespace=env.IMAGE_PULLER_NAMESPACE,
            labels=labels,
            ),
        spec=client.V1DaemonSetSpec(
            selector=client.V1LabelSelector(match_labels=labels),
            update_strategy=client.V1DaemonSetUpdateStrategy(
                type="RollingUpdate",
                rolling_update=client.V1RollingUpdateDaemonSet(
                    max_unavailable="100%",
                    ),
                ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels=labels),
                spec=pod_spec,
                ),
            ),
        )


def _sync_daemonset(daemonset: client.V1DaemonSet) -> DaemonsetSyncOutcome:
    """ Synchronously create or replace the daemonset

    Returns True if the daemonset was created, False if it was updated.
    """
    _load_kube_config()
    apps_api = client.AppsV1Api()

    try:
        existing_daemonset = apps_api.read_namespaced_daemon_set(
            name=env.IMAGE_PULLER_NAME,
            namespace=env.IMAGE_PULLER_NAMESPACE,
            )
    except client.ApiException as exc:
        if exc.status != 404:
            raise
        apps_api.create_namespaced_daemon_set(
            namespace=env.IMAGE_PULLER_NAMESPACE,
            body=daemonset,
            )
        return 'created'
    else:
        daemonset.metadata.resource_version = (
            existing_daemonset.metadata.resource_version
        )
        apps_api.replace_namespaced_daemon_set(
            name=env.IMAGE_PULLER_NAME,
            namespace=env.IMAGE_PULLER_NAMESPACE,
            body=daemonset,
            )
        return 'updated'


async def sync_image_puller_daemonset(
        environments: list[BinderEnvironmentResponse],
        ) -> DaemonsetSyncResult:
    """ Create or update the continuous image-puller DaemonSet so that it
    pulls the images for the input `environments`
    """
    daemonset = _build_daemonset(environments)

    try:
        sync_outcome = await asyncio.to_thread(
            _sync_daemonset, daemonset
            )
    except client.ApiException, config.ConfigException:
        logger.exception("Failed to sync image-puller daemonset")
        raise

    logger.info(
        f"{sync_outcome.capitalize()} {env.IMAGE_PULLER_NAME} daemonset ",
        f"with {len(daemonset.spec.template.spec.init_containers)} "
        "image(s) to pre-pull"
        )

    return {
        "outcome": sync_outcome,
        "image_count": len(daemonset.spec.template.spec.init_containers)
        }
