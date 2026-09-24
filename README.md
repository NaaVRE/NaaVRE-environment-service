# NaaVRE-environment-service

## Development setup

This service requires API access to other NaaVRE services. During development, these services should be run in minikube. To do so:

- Setup, or get access to a development VM ([NaaVRE-dev-vm](https://github.com/NaaVRE/NaaVRE-dev-vm))
- Deploy [NaaVRE-helm (use the poc_binderhub branch)](https://github.com/NaaVRE/NaaVRE-helm/tree/poc_binderhub). Optionally, to enable starting of images built by Binder Hub, deploy with  valuesu for `binderhub.registry.image_prefix`, `binderhub.registry.username`, and `binderhub.registry.password`.

How you run the environment service depends on what needs to be tested:
- For triggering builds, see [Runing locally](#running-locally)
- For interacting with the image-puller daemonset, see [Running in minikube](#running-in-minikube)

### Running locally

Install dependencies:

```shell
uv sync --locked --dev
```

Run the dev server

```shell
uv run --env-file ./dev/.env fastapi dev
```

Running tests and coverage

```shell
uv run coverage run -m pytest app/tests/ --log-cli-level=DEBUG
uv run coverage report
```

## Running in minikube

Build the image into minikube (refer to the minikube documentation for details):

```shell
eval $(minikube docker-env --ssh-host)
docker build . -f docker/Dockerfile -t naavre-environment-service:dev
```

Deploy to with helm:

```shell
helm --kube-context minikube -n naavre-environment-service upgrade --install --create-namespace naavre-environment-service ./helm/naavre-environment-service -f values-dev.yaml
```

## Build Docker image

```shell
docker build . -f docker/Dockerfile -t naavre-environment-service:dev
```

To run it:

```shell
docker run -p 127.0.0.1:8000:8000 --env-file ./dev/.env naavre-environment-service:dev
```

and open http://127.0.0.1:8000/docs

## Deployment

We use Helm for the deployment:

```shell
helm -n naavre-environment-service upgrade --install --create-namespace naavre-environment-service ./helm/naavre-environment-service -f my-values.yaml
```

`my-values.yaml` should contain ingress configuration (checkout [./helm/naavre-environment-service/values-example.yaml](./helm/naavre-environment-service/values-example.yaml)).
