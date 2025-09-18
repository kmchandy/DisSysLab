{
    "schema": "dsl.topology.v1",
    "title": "Pipeline",
    "blocks": [
        {"id": "src", "role": "source",    "ref": "block_0"},
        {"id": "tr",  "role": "transform", "ref": "block_1"},
        {"id": "snk", "role": "sink",      "ref": "block_2"}
    ],
    "connections": [
        ["src", "tr"],
        ["tr",  "snk"]
    ]
}
