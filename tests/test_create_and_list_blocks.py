from dsl.user_interaction.interaction import (
    network, create_block, set_block_function, connect_blocks,
    list_blocks, export_to_yaml
)
from dsl.user_interaction.export_to_yaml import load_from_yaml, validate_network


def test_create_and_list_blocks():
    create_block("gen", "generate")
    output = list_blocks()
    assert "gen" in output


def test_set_block_function():
    create_block("xf", "transform")
    result = set_block_function(
        "xf", "GPT_Prompt", {"template": "sentiment_analysis"})
    assert "GPT_Prompt" in result


def test_connect_blocks():
    create_block("gen", "generate")
    create_block("rec", "record")
    # Assuming default ports exist
    result = connect_blocks("gen", "rec", "out", "in")
    assert "Connected" in result


def test_export_and_load_yaml():
    yaml_str = export_to_yaml(network)
    loaded = load_from_yaml(yaml_text=yaml_str)
    assert "blocks" in loaded


def test_validate_network():
    errs = validate_network(network)
    assert isinstance(errs, list)
