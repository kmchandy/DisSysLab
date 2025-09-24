from dsl.kit.yaml_to_python import yaml_to_python

# Given validated pipeline.yaml:
# graph: [[src, snk]]
# bindings:
#   src: { id: ops:from_list, params: { items: ["hello","world"] } }
#   snk: { id: ops:to_list }

code = yaml_to_python(
    "/Users/kmchandy/Documents/DisSysLab/examples/simple_source_sink.yaml",
    out_path="/Users/kmchandy/Documents/DisSysLab/examples/pipeline_out.py")
print("Wrote pipeline_out.py")
