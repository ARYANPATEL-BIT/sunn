"""docs/API.md, with docs/TRAININGS_CONTRACT.md for Trainings, is the contract the app is built
against: every route they list exists, every route is in one of them, every example in it is exactly what its schema gives, and the stubs answer
their schema."""
import json
import re
from pathlib import Path
from typing import get_args

from fastapi.routing import APIRoute
from pydantic import BaseModel, TypeAdapter

import schemas

ROOT = Path(__file__).resolve().parent.parent
HEADING = re.compile(r"^### `(GET|POST|PATCH|DELETE) (\S+)` · (real|stub)$", re.M)
EXAMPLE = re.compile(r"```json\n(.*?)\n```", re.S)


def documented():
    """{(method, path): (real or stub, the example response or None)} from both docs."""
    endpoints = {}
    for doc in ("docs/API.md", "docs/TRAININGS_CONTRACT.md"):
        parts = HEADING.split((ROOT / doc).read_text(encoding="utf-8"))[1:]
        for method, path, status, section in zip(*[iter(parts)] * 4):
            example = EXAMPLE.search(section)
            assert (method, path) not in endpoints, (method, path)
            endpoints[method, path] = status, example and json.loads(example.group(1))
    return endpoints


def routes():
    import api  # here, not at the top: the env fixture has moved into a folder of its own
    import trainings

    # FastAPI keeps an included router whole, so its routes are listed from the router itself.
    return {(method, route.path): route for route in [*api.app.routes, *trainings.router.routes]
            if isinstance(route, APIRoute) for method in route.methods}


def same_after_schema(model, example, **dump):
    adapter = TypeAdapter(model)
    return adapter.dump_python(adapter.validate_python(example), mode="json", **dump) == example


def test_every_documented_route_exists_and_every_route_is_documented(env):
    assert documented().keys() == routes().keys()


def test_examples_match_their_schema_exactly(env):
    """Validating and dumping an example gives it back unchanged: no field missing, extra or of
    the wrong type. /speak answers audio, so it has no JSON example."""
    found = routes()
    for endpoint, (_, example) in documented().items():
        model = found[endpoint].response_model
        assert (example is None) == (model is None), endpoint
        if model is not None:
            assert same_after_schema(model, example), endpoint
    for model in vars(schemas).values():
        if isinstance(model, type) and issubclass(model, BaseModel) and model.model_config.get("json_schema_extra"):
            # exclude_unset: Error's example leaves out the fields its code doesn't use.
            example = model.model_config["json_schema_extra"]["examples"][0]
            assert same_after_schema(model, example, exclude_unset=True), model


def test_stubs_answer_their_schema(env):
    client, found = env.signup(), routes()
    # The ones that take no input; tests/test_trainings.py calls the rest with theirs.
    stubs = [(method, path) for (method, path), (status, _) in documented().items()
             if status == "stub" and method == "GET" and "{" not in path]
    for method, path in stubs:
        response = client.request(method, path)
        assert response.status_code == 200, (method, path, response.text)
        TypeAdapter(found[method, path].response_model).validate_python(response.json())


def test_every_error_has_one_shape(env):
    client = env.signup()
    assert client.get("/nowhere").json() == {"error": "not_found", "message": "not found"}
    refused = client.post("/me/phrases", json={})
    assert refused.status_code == 422 and refused.json() == {"error": "invalid_input", "message": "text: Field required"}
    assert env.client().get("/me/phrases").json()["error"] == "not_logged_in"


def test_every_error_code_the_api_sends_is_in_the_schema():
    sent = set()
    for name in ("api.py", "gnani.py", "trainings.py"):
        sent |= set(re.findall(r'(?:Refused\(\d+|GnaniError\()\s*,?\s*"(\w+)"', (ROOT / "src" / name).read_text("utf-8")))
    assert sent and sent <= set(get_args(schemas.ErrorCode)), sent - set(get_args(schemas.ErrorCode))
