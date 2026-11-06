# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "jsonschema==4.26.0",
#   "pyyaml==6.0.3",
#   "rfc3339-validator==0.1.4",  # without it, date-time isn't checked
# ]
# ///
"""Check that every example in the OpenAPI spec matches its schema."""

import sys

import yaml
from jsonschema import Draft202012Validator

SPEC = "api/openapi.yaml"


def media_types(node, path=""):
    """Yield (path, media type) for every object that has a schema and examples."""
    if isinstance(node, dict):
        if "schema" in node and "examples" in node:
            yield path, node
        for key, value in node.items():
            yield from media_types(value, f"{path}/{key}")


def main() -> int:
    with open(SPEC) as f:
        doc = yaml.safe_load(f)
    checked = failed = 0
    for path, media in media_types(doc):
        # Adding the components lets $refs such as '#/components/schemas/X' resolve.
        schema = {**media["schema"], "components": doc["components"]}
        validator = Draft202012Validator(
            schema, format_checker=Draft202012Validator.FORMAT_CHECKER
        )
        for name, example in media["examples"].items():
            errors = [e.message for e in validator.iter_errors(example["value"])]
            checked += 1
            failed += bool(errors)
            print(
                f"{'FAIL' if errors else 'ok  '} {path} {name}",
                *errors,
                sep="\n     " if errors else " ",
            )
    print(f"{checked} examples checked, {failed} failed")
    return 1 if failed or not checked else 0


if __name__ == "__main__":
    sys.exit(main())
