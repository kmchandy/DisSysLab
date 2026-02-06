"""
Fork Pattern - Parallel Processing with Separate Collection

Pattern: One source broadcasts to multiple processors, each with its own collector.

Topology:
        ┌→ thumbnail_creator → collector_thumbnails
source ─┤
        └→ metadata_extractor → collector_metadata

Use case: Process the same data in multiple different ways simultaneously,
keeping results organized separately.

Example: Process images to create thumbnails AND extract metadata in parallel.
"""

from dsl import network
from components.sources import ListSource
from dsl.blocks import Source, Transform, Sink

# ==============================================================================
# STEP 1: Write Ordinary Python Functions Independent of DSL
# ==============================================================================

image_files = ListSource(items=["photo1.jpg", "photo2.jpg", "photo3.jpg"])


def create_thumbnail(filename):
    """
    Simulate creating a thumbnail.
    In real implementation, would use PIL/Pillow to resize image.
    """
    base = filename.replace('.jpg', '')
    return f"{base}_thumb.jpg"


def extract_metadata(filename):
    """
    Simulate extracting image metadata.
    In real implementation, would use PIL/Pillow to get actual dimensions.
    """
    return {
        "file": filename,
        "format": "JPEG",
        "size": "1920x1080"
    }


# ==============================================================================
# STEP 2: Specify nodes of the network by wrapping the functions
# ==============================================================================

source = Source(
    fn=image_files.run,
    name="image_source"
)

thumbnail_creator = Transform(
    fn=create_thumbnail,
    name="thumbnail_creator"
)

metadata_extractor = Transform(
    fn=extract_metadata,
    name="metadata_extractor"
)

# Separate collectors for each processing path
thumbnail_results = []
collector_thumbnails = Sink(
    fn=thumbnail_results.append,
    name="collector_thumbnails"
)

metadata_results = []
collector_metadata = Sink(
    fn=metadata_results.append,
    name="collector_metadata"
)


# ==============================================================================
# STEP 3: Build and Run the Network - Fork Pattern
# ==============================================================================

g = network([
    # Fanout: source sends to BOTH processors
    (source, thumbnail_creator),
    (source, metadata_extractor),

    # Each processor sends to its own collector
    (thumbnail_creator, collector_thumbnails),
    (metadata_extractor, collector_metadata)
])

g.run_network()


# ==============================================================================
# Verify Results
# ==============================================================================
if __name__ == "__main__":
    print("Fork Pattern Results")
    print("=" * 50)
    print("Thumbnail results:", thumbnail_results)
    print("Metadata results:", metadata_results)

    expected_thumbnails = ["photo1_thumb.jpg",
                           "photo2_thumb.jpg", "photo3_thumb.jpg"]
    assert thumbnail_results == expected_thumbnails
    assert len(metadata_results) == 3

    print("\n✓ Fork pattern completed successfully!")
    print(f"  Input: 3 image files")
    print(f"  Path 1 (thumbnails): {len(thumbnail_results)} results")
    print(f"  Path 2 (metadata): {len(metadata_results)} results")
    print(f"  Both paths processed all images in parallel!")
