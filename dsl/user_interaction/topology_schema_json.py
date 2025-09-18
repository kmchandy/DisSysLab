{
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DisSysLab Topology v1",
    "type": "object",
    "additionalProperties": false,
    "required": ["schema", "blocks", "connections"],
    "properties": {
        "schema": {"const": "dsl.topology.v1"},
        "title":  {"type": "string"},
        "description": {"type": "string"},
        "registry_version": {"type": "string", "description": "Optional hint to bind against a specific registry version/hash."},
        "blocks": {
            "type": "array",
            "minItems": 1,
            "items": {"$ref": "#/definitions/block"}
        },
        "connections": {
            "type": "array",
            "items": {"$ref": "#/definitions/connection"}
        }
    },
    "definitions": {
        "identifier": {
            "type": "string",
            "pattern": "^[A-Za-z][A-Za-z0-9_]*$",
            "description": "Graph-local id (e.g., src, tr0, snk)."
        },
        "role": {
            "type": "string",
            "enum": ["source", "transform", "sink"],
            "description": "Determines default factory & default single-port shape."
        },
        "portName": {
            "type": "string",
            "pattern": "^[A-Za-z][A-Za-z0-9_]*$"
        },
        "portIndex": {
            "type": "integer",
            "minimum": 0
        },
        "ports": {
            "oneOf": [
                {"type": "integer", "minimum": 0,
                 "description": "Port count; default names are in0/in1..., out0/out1..."},
                {"type": "array", "minItems": 1, "uniqueItems": true, "items": {"$ref": "#/definitions/portName"},
                 "description": "Explicit port names (indices 0..N-1 also valid aliases)."}
            ]
        },
        "shape": {
            "type": "object",
            "additionalProperties": false,
            "properties": {
                "in":  {"$ref": "#/definitions/ports"},
                "out": {"$ref": "#/definitions/ports"}
            },
            "description": "Optional per-block port shape. If omitted, defaults by role apply: source(in=0,out=1), transform(1,1), sink(1,0)."
        },
        "block": {
            "type": "object",
            "additionalProperties": false,
            "required": ["id", "role", "ref"],
            "properties": {
                "id":   {"$ref": "#/definitions/identifier"},
                "role": {"$ref": "#/definitions/role"},
                "ref":  {"type": "string", "description": "Binding key resolved in the bindings YAML."},
                "shape": {"$ref": "#/definitions/shape"},
                "meta": {"type": "object", "description": "Freeform annotations for UIs (ignored by runtime)."}
            }
        },
        "connection": {
            "oneOf": [
                {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 2,
                    "items": [
                      {"$ref": "#/definitions/identifier"},
                      {"$ref": "#/definitions/identifier"}
                    ],
                    "description": "Pair form: [srcId, dstId] — normalized to [src,'out',dst,'in'] (valid only if both endpoints are single-port)."
                },
                {
                    "type": "object",
                    "additionalProperties": false,
                    "required": ["from", "out", "to", "in"],
                    "properties": {
                        "from": {"$ref": "#/definitions/identifier"},
                        "out":  {"oneOf": [{"$ref": "#/definitions/portName"}, {"$ref": "#/definitions/portIndex"}]},
                        "to":   {"$ref": "#/definitions/identifier"},
                        "in":   {"oneOf": [{"$ref": "#/definitions/portName"}, {"$ref": "#/definitions/portIndex"}]}
                    },
                    "description": "Explicit port form: { from, out, to, in } — names or 0-based indices."
                }
            ]
        }
    }
}
