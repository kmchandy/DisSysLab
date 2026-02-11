from components.sources.bluesky_source import BlueSkySource

# Replace with your credentials
source = BlueSkySource(
    handle="kmchandy.bsky.social",  # Your handle
    app_password="juio-jg5k-hrc2-7vp6"  # Your app password
)

# Test: Fetch one post
print("Testing BlueSky connection...")
post = source.run()
if post:
    print(f"✓ Success! Got post from @{post['author']}")
    print(f"  Text: {post['text'][:60]}...")
else:
    print("✗ No posts found (your timeline might be empty)")
