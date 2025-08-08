# --- demo_sentiment.py in examples/ ---

def demo_sentiment(create_block, set_block_function, connect_blocks, summarize_network):
    """Run a guided sentiment analysis pipeline demo.

    This demo is designed for beginners and can be included in a short tutorial
    or README.md to illustrate the basic steps of building a distributed
    application with AL.

    Sections:
      FIRST: Make the blocks (generator, transformer, recorder)
      SECOND: Connect the blocks
      THIRD: Run (here: show the summary)
    """
    print("\n🎬 Demo: Sentiment Pipeline")

    # FIRST: Make the blocks
    print("\nFIRST: MAKE BLOCKS")
    print("Step 1: Create generator block 'gen'")
    print(create_block("gen", "generator"))
    print(set_block_function("gen", "GenerateFromList", {
        "values": ["hello", "world", "how are you?"]
    }))

    print("\nStep 2: Create transformer block 'xf' for sentiment analysis")
    print(create_block("xf", "transform"))
    print(set_block_function("xf", "GPT_Prompt", {
        "template": "sentiment_analysis",
        "input_key": "text",
        "output_key": "sentiment"
    }))

    print("\nStep 3: Create recorder block 'rec'")
    print(create_block("rec", "record"))
    print(set_block_function("rec", "RecordToFile", {
        "filename": "results.json"
    }))

    # SECOND: Connect the blocks
    print("\nSECOND: CONNECT BLOCKS")
    print("Step 4: Connect 'gen' to 'xf'")
    print(connect_blocks("gen", "xf"))
    print("Step 5: Connect 'xf' to 'rec'")
    print(connect_blocks("xf", "rec"))

    # THIRD: Run (show summary)
    print("\nTHIRD: RUN NETWORK")
    print("Step 6: Show network summary")
    print(summarize_network())
