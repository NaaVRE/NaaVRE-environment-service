# NaaVRE-environment-service

## Running locally

TODO: describe the following dev setup:

- Setup https://github.com/NaaVRE/NaaVRE-dev-vm
- Deploy https://github.com/NaaVRE/NaaVRE-helm/tree/poc_binderhub with custom prefix and access token for `binderhub.registry`

Install dependencies:

```shell
virtualenv venv
. venv/bin/activate
pip install -r requirements.txt
```

Run the dev server

```shell
while read env; do export $env; done < .env.dev
fastapi dev app/main.py
```

## Build Docker image

```shell
docker build . -t naavre-environment-service:dev
```

To run it:

```shell
docker run -p 127.0.0.1:8000:8000 naavre-environment-service:dev
```

and open http://127.0.0.1:8000/docs

## Deployment

We use Helm for the deployment:

```shell
helm -n naavre-environment-service upgrade --install --create-namespace naavre-environment-service ./helm/naavre-environment-service -f my-values.yaml
```

`my-values.yaml` should contain ingress configuration (checkout [./helm/naavre-environment-service/values-example.yaml](./helm/naavre-environment-service/values-example.yaml)).
