"""
Join Pattern - Multiple Sources Merge into One Processor

Pattern: Multiple independent sources send to a single processor.

Topology:
    camera_1 ─┐
    camera_2 ─┤→ processor → collector
    camera_3 ─┘

Use case: Aggregate data from multiple independent sources for unified processing.

Example: Multiple cameras feeding images to one processor.
"""

from dsl import network
from components.sources import ListSource
from dsl.blocks import Source, Transform, Sink

# ==============================================================================
# STEP 1: Write Ordinary Python Functions Independent of DSL
# ==============================================================================

# Three independent image sources (different cameras/folders)
camera_1_images = ListSource(items=["cam1_photo1.jpg", "cam1_photo2.jpg"])
camera_2_images = ListSource(items=["cam2_photo1.jpg", "cam2_photo2.jpg"])
camera_3_images = ListSource(items=["cam3_photo1.jpg", "cam3_photo2.jpg"])


def process_image(filename):
    """
    Process any image regardless of source.
    Extracts camera and photo info from filename.
    """
    parts = filename.replace('.jpg', '').split('_')
    camera = parts[0]
    photo = parts[1]

    return {
        "filename": filename,
        "camera": camera,
        "photo": photo,
        "processed": True
    }


# ==============================================================================
# STEP 2: Specify nodes of the network by wrapping the functions
# ==============================================================================

# Three source nodes (three cameras)
source_camera_1 = Source(
    fn=camera_1_images.run,
    name="camera_1"
)

source_camera_2 = Source(
    fn=camera_2_images.run,
    name="camera_2"
)

source_camera_3 = Source(
    fn=camera_3_images.run,
    name="camera_3"
)

# Single processor handles images from ALL cameras
processor = Transform(
    fn=process_image,
    name="image_processor"
)

# Single collector receives all processed results
results = []
collector = Sink(
    fn=results.append,
    name="collector"
)


# ==============================================================================
# STEP 3: Build and Run the Network - Join Pattern
# ==============================================================================

g = network([
    # All three cameras send to same processor (FANIN/JOIN)
    (source_camera_1, processor),
    (source_camera_2, processor),
    (source_camera_3, processor),

    # Processor sends to collector
    (processor, collector)
])

g.run_network()


# ==============================================================================
# Verify Results
# ==============================================================================
if __name__ == "__main__":
    print("Join Pattern Results")
    print("=" * 50)
    print("Processed images:")
    for result in results:
        print(f"  {result}")

    # Should have 6 total images (2 from each camera)
    assert len(results) == 6, f"Expected 6 images, got {len(results)}"

    # Check we got images from all cameras
    cameras = set(r['camera'] for r in results)
    assert cameras == {'cam1', 'cam2',
                       'cam3'}, "Should have images from all 3 cameras"

    print(f"\n✓ Join pattern completed successfully!")
    print(f"  Camera 1: 2 images")
    print(f"  Camera 2: 2 images")
    print(f"  Camera 3: 2 images")
    print(f"  Total processed: 6 images")
    print(f"  Note: Processing order is non-deterministic (depends on camera timing)")
