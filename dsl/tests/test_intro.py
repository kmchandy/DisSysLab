def test_pipeline_dict_order():
    '''
    Tests the graph_structure called pipeline.
    Using pipeline means you don't have to specify connections
    when you create a linear network.
    The order of blocks in the pipeline matters.
    '''
    from dsl.block_lib.stream_generators import GenerateFromList
    from dsl.block_lib.stream_transformers import TransformerFunction
    from dsl.block_lib.stream_recorders import RecordToList
    from dsl.block_lib.graph_structures import pipeline

    saved_list = []

    def f(msg):
        return msg.upper()

    net = pipeline({
        "src": GenerateFromList(items=["one", "two"]),
        "caps": TransformerFunction(func=f),
        "sink": RecordToList(target_list=saved_list)
    })

    net.compile_and_run()
    assert saved_list == ["ONE", "TWO"]


test_pipeline_dict_order()
