{
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DisSysLab Bindings v1",
    "type": "object",
    "additionalProperties": false,
    "required": ["schema", "bindings"],
    "properties": {
        "schema": {"const": "dsl.bindings.v1"},
        "catalog_version": {"type": "string", "description": "Optional catalog/registry version or hash used to resolve `fn` names."},
        "bindings": {
            "type": "object",
            "description": "Map of topology `ref` → binding entry.",
            "additionalProperties": {"$ref": "#/definitions/binding"}
        }
    },
    "definitions": {
        "binding": {
            "type": "object",
            "additionalProperties": false,
            "required": ["fn", "params"],
            "properties": {
                "fn": {
                    "type": "string",
                    "pattern": "^[A-Za-z][A-Za-z0-9_./-]*$",
                    "description": "Catalog function name resolved in the Python registry (e.g., 'gen_list', 'add_sentiment', 'to_console')."
                },
                "params": {
                    "type": "object",
                    "description": "JSON-serializable kwargs to pass when instantiating the callable."
                },
                "label":  {"type": "string", "description": "Optional human-friendly name for UIs."},
                "version": {"type": "string", "description": "Optional per-binding version tag."},
                "kind": {
                    "type": "string",
                    "enum": ["source", "transform", "sink"],
                    "description": "Optional guard; when present, must match the block role in the topology."
                }
            }
        }
    }
}
