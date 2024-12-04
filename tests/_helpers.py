# NOTE: This file is not used in the project.
import warnings

warnings.warn(
    "This file shouldn't be used in the runtime. Only for testing", ImportWarning
)

from jsonschema.validators import RefResolver

import requests

current_url = ""


def expand_json_schema(schema):
    # Create a resolver to resolve references
    resolver = RefResolver.from_schema(schema)

    def expand_refs(refs):
        global current_url
        # Recursive function to expand references
        if isinstance(refs, dict):
            if "$ref" in refs:
                ref = refs["$ref"]
                if ref.startswith("http://") or ref.startswith("https://"):
                    # Fetch the remote reference and expand it recursively
                    current_url = ref
                    resolved = resolver.resolve(ref)
                    return expand_refs(resolved)
                elif ref.startswith("#"):
                    # Resolve the reference and expand it recursively
                    ref = (
                        current_url.split("#")[0] + ref
                        if "#" in current_url
                        else current_url + ref
                    )
                    resolved = resolver.resolve(ref)
                    return expand_refs(resolved[1])
                else:
                    # Resolve the reference and expand it recursively
                    resolved = resolver.resolve(ref)
                    return expand_refs(resolved[1])
            else:
                # Expand references in each value of the dictionary
                return {key: expand_refs(value) for key, value in refs.items()}
        elif isinstance(refs, list):
            # Expand references in each item of the list
            return [expand_refs(item) for item in refs]
        else:
            return refs

    # Expand references in the top-level schema
    expanded_schema = expand_refs(schema)

    return expanded_schema


def fetch_remote_schema(uri):
    # Fetch the remote JSON schema
    response = requests.get(uri)
    remote_schema = response.json()
    return remote_schema


def get_all_keys(json_schema):
    keys = []
    required_keys = []

    def traverse(schema):
        nonlocal keys, required_keys

        if isinstance(schema, dict):
            if "properties" in schema:
                for key, value in schema["properties"].items():
                    keys.append(key)
                    if "required" in schema and key in schema["required"]:
                        required_keys.append(key)
                    traverse(value)
            if "items" in schema:
                traverse(schema["items"])
            if "oneOf" in schema:
                for item in schema["oneOf"]:
                    traverse(item)
            if "allOf" in schema:
                for item in schema["allOf"]:
                    traverse(item)

    traverse(json_schema)

    return keys, required_keys


# Expand the schema
# expanded_schema = expand_json_schema(schema)
# keys, required = extract_data_keys(expanded_schema)
#
# with open("schema.json", "w") as f:
#     json.dump(expanded_schema, f, indent=4)
