CATALOGUE_URL = "https://catalogue.test"
CATALOGUE_API_TOKEN = "catalogue-test-token"


def catalogue_list_response(*, results: list[dict]) -> dict:
    return {
        "count": len(results),
        "next": None,
        "previous": None,
        "results": results,
        }
