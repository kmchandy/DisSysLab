def test_pipeline_dict_order():
    from dsl.block_lib.stream_generators import generate
    from dsl.block_lib.stream_transformers import transform
    from dsl.block_lib.stream_recorders import record
    from dsl.block_lib.graph_structures import pipeline

    net = pipeline({
        "src": generate(["one", "two"]),
        "caps": transform(str.upper),
        "sink": record()
    })

    net.compile_and_run()
    assert net.blocks["sink"].saved == ["ONE", "TWO"]


test_pipeline_dict_order()
