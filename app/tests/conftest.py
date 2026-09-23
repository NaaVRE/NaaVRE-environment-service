import os

os.environ.setdefault("BINDER_URL", "https://binder.test")
os.environ.setdefault("BINDER_API_TOKEN", "binder-test-token")
os.environ.setdefault("CATALOGUE_URL", "https://catalogue.test")
os.environ.setdefault("CATALOGUE_API_TOKEN", "catalogue-test-token")
os.environ.setdefault("VERIFY_SSL", "false")
os.environ.setdefault("ROOT_PATH", "")

os.environ.setdefault(
    'CONFIG_FILE_PATH',
    os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "./configurations/one-token.json"
            )
        )

    )
