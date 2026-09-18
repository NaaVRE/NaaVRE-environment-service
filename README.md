# NaaVRE-environment-service

## Running locally

TODO: describe the following dev setup:

- Setup https://github.com/NaaVRE/NaaVRE-dev-vm
- Deploy https://github.com/NaaVRE/NaaVRE-helm/tree/poc_binderhub with custom prefix and access token for `binderhub.registry`

Install dependencies:

```shell
uv sync --locked --dev
```

Run the dev server

```shell
uv run --env-file .env.dev fastapi dev
```

Running tests and coverage

```shell
uv run coverage run -m pytest app/tests/ --log-cli-level=DEBUG
uv run coverage report
```

## Build Docker image

```shell
docker build . -f docker/Dockerfile -t naavre-environment-service:dev
```

To run it:

```shell
docker run -p 127.0.0.1:8000:8000 --env-file .env.dev naavre-environment-service:dev
```

and open http://127.0.0.1:8000/docs

## Deployment

We use Helm for the deployment:

```shell
helm -n naavre-environment-service upgrade --install --create-namespace naavre-environment-service ./helm/naavre-environment-service -f my-values.yaml
```

`my-values.yaml` should contain ingress configuration (checkout [./helm/naavre-environment-service/values-example.yaml](./helm/naavre-environment-service/values-example.yaml)).
