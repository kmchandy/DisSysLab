# components/transformers/prompts.py

"""
Prompt Library for AI-Powered Transforms

A searchable catalog of prompts for building AI-powered distributed systems.
Students can browse by category, search by keyword, or create custom prompts.

Usage:
    from components.transformers.prompts import get_prompt, PROMPTS
    from components.transformers.claude_agent import ClaudeAgent
    from dsl.blocks import Transform
    
    # Use a prompt by key
    analyzer = Transform(
        fn=ClaudeAgent(get_prompt("sentiment_analyzer")).run,
        name="sentiment"
    )
    
    # Browse available prompts
    from components.transformers.prompts import print_prompt_catalog
    print_prompt_catalog()
    
    # Search for prompts
    from components.transformers.prompts import search_prompts
    spam_prompts = search_prompts("spam")
"""

PROMPTS = {
    # ========================================================================
    # TEXT ANALYSIS
    # ========================================================================

    "sentiment_analyzer": {
        "category": "text_analysis",
        "description": "Analyzes positive/negative/neutral sentiment with confidence score",
        "input": "Text string",
        "output": "JSON with sentiment, score (-1 to +1), and reasoning",
        "prompt": """Analyze the sentiment of the given text.

Determine if the text expresses positive, negative, or neutral sentiment.
Provide a score from -1.0 (very negative) to +1.0 (very positive).

Return JSON format:
{
    "sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL",
    "score": -1.0 to +1.0,
    "reasoning": "brief explanation of the sentiment"
}"""
    },

    "emotion_detector": {
        "category": "text_analysis",
        "description": "Detects specific emotions (joy, anger, sadness, fear, surprise)",
        "input": "Text string",
        "output": "JSON with primary emotion and scores for each emotion",
        "prompt": """Detect emotions in the given text.

Identify the primary emotion and provide scores for: joy, anger, sadness, fear, surprise, disgust, neutral.

Return JSON format:
{
    "primary_emotion": "joy" | "anger" | "sadness" | "fear" | "surprise" | "disgust" | "neutral",
    "emotion_scores": {
        "joy": 0.0-1.0,
        "anger": 0.0-1.0,
        "sadness": 0.0-1.0,
        "fear": 0.0-1.0,
        "surprise": 0.0-1.0,
        "disgust": 0.0-1.0,
        "neutral": 0.0-1.0
    },
    "reasoning": "brief explanation"
}"""
    },

    "tone_analyzer": {
        "category": "text_analysis",
        "description": "Analyzes tone (formal, casual, professional, friendly, aggressive)",
        "input": "Text string",
        "output": "JSON with tone classification and confidence",
        "prompt": """Analyze the tone of the given text.

Determine the overall tone: formal, casual, professional, friendly, aggressive, sarcastic, humorous, serious.

Return JSON format:
{
    "tone": "formal" | "casual" | "professional" | "friendly" | "aggressive" | "sarcastic" | "humorous" | "serious",
    "confidence": 0.0-1.0,
    "formality_score": 0.0-1.0,
    "reasoning": "brief explanation"
}"""
    },

    "readability_analyzer": {
        "category": "text_analysis",
        "description": "Analyzes reading difficulty level and complexity",
        "input": "Text string",
        "output": "JSON with reading level and complexity metrics",
        "prompt": """Analyze the readability of the given text.

Assess reading difficulty, complexity, and target audience level.

Return JSON format:
{
    "reading_level": "elementary" | "middle_school" | "high_school" | "college" | "graduate" | "expert",
    "complexity_score": 0.0-1.0,
    "estimated_grade": 1-16,
    "issues": ["long sentences", "complex vocabulary", etc],
    "reasoning": "brief explanation"
}"""
    },

    # ========================================================================
    # CONTENT FILTERING & MODERATION
    # ========================================================================

    "spam_detector": {
        "category": "content_filtering",
        "description": "Detects spam, promotional content, and phishing attempts",
        "input": "Text string",
        "output": "JSON with is_spam (bool), confidence (0-1), and reason",
        "prompt": """Analyze if the given text is spam.

Spam indicators include:
- Promotional language (buy now, limited time, act now)
- Requests for money or personal information
- Suspicious links or offers
- Too-good-to-be-true claims
- Excessive urgency or pressure tactics

Return JSON format:
{
    "is_spam": true/false,
    "confidence": 0.0-1.0,
    "spam_type": "promotional" | "phishing" | "scam" | "legitimate",
    "reason": "brief explanation"
}"""
    },

    "urgency_detector": {
        "category": "content_filtering",
        "description": "Detects urgent or time-sensitive content requiring immediate attention",
        "input": "Text string",
        "output": "JSON with urgency level, metrics, and reasoning",
        "prompt": """Analyze the urgency level of the given text.

Urgency indicators include:
- Time-sensitive language (urgent, asap, immediately, now)
- Critical or emergency terms
- Deadlines or countdowns
- Exclamation marks and ALL CAPS
- Action-required language

Return JSON format:
{
    "urgency": "HIGH" | "MEDIUM" | "LOW",
    "metrics": {
        "urgency_score": 0-10,
        "time_sensitive": true/false,
        "requires_immediate_action": true/false
    },
    "reasoning": "brief explanation"
}"""
    },

    "toxicity_detector": {
        "category": "content_filtering",
        "description": "Detects toxic, offensive, or inappropriate content",
        "input": "Text string",
        "output": "JSON with toxicity classification and severity",
        "prompt": """Analyze if the given text contains toxic or inappropriate content.

Toxicity indicators include:
- Profanity or vulgar language
- Personal attacks or insults
- Hate speech or discrimination
- Threats or harassment
- Sexual or explicit content

Return JSON format:
{
    "is_toxic": true/false,
    "severity": "none" | "low" | "medium" | "high" | "severe",
    "toxicity_types": ["profanity", "insult", "threat", etc],
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}"""
    },

    "profanity_filter": {
        "category": "content_filtering",
        "description": "Detects and categorizes profane or vulgar language",
        "input": "Text string",
        "output": "JSON with profanity detection and severity",
        "prompt": """Detect profanity in the given text.

Return JSON format:
{
    "contains_profanity": true/false,
    "severity": "none" | "mild" | "moderate" | "severe",
    "count": 0-N,
    "types": ["mild_profanity", "strong_profanity", "sexual", etc]
}"""
    },

    # ========================================================================
    # CLASSIFICATION
    # ========================================================================

    "topic_classifier": {
        "category": "classification",
        "description": "Classifies text into predefined topic categories",
        "input": "Text string",
        "output": "JSON with primary_topic, confidence, and all_topics",
        "prompt": """Classify the given text into topic categories.

Categories: technology, business, science, health, sports, entertainment, politics, education, finance, other

Return JSON format:
{
    "primary_topic": "category name",
    "confidence": 0.0-1.0,
    "all_topics": ["topic1", "topic2"],
    "reasoning": "brief explanation"
}"""
    },

    "language_detector": {
        "category": "classification",
        "description": "Detects the language of the text",
        "input": "Text string",
        "output": "JSON with language code and confidence",
        "prompt": """Detect the language of the given text.

Return JSON format:
{
    "language": "en" | "es" | "fr" | "de" | "zh" | "ja" | etc,
    "language_name": "English" | "Spanish" | "French" | etc,
    "confidence": 0.0-1.0
}"""
    },

    "intent_classifier": {
        "category": "classification",
        "description": "Classifies user intent (question, command, statement, complaint)",
        "input": "Text string",
        "output": "JSON with intent type and confidence",
        "prompt": """Classify the intent of the given text.

Intent types: question, command, statement, complaint, request, greeting, thanks, other

Return JSON format:
{
    "intent": "question" | "command" | "statement" | "complaint" | "request" | "greeting" | "thanks" | "other",
    "confidence": 0.0-1.0,
    "sub_intent": "specific type if applicable",
    "reasoning": "brief explanation"
}"""
    },

    "priority_classifier": {
        "category": "classification",
        "description": "Classifies message priority for task management",
        "input": "Text string",
        "output": "JSON with priority level and reasoning",
        "prompt": """Classify the priority of the given text.

Consider urgency, importance, deadlines, and impact.

Return JSON format:
{
    "priority": "critical" | "high" | "medium" | "low",
    "urgency": 0-10,
    "importance": 0-10,
    "reasoning": "brief explanation"
}"""
    },

    # ========================================================================
    # EXTRACTION
    # ========================================================================

    "entity_extractor": {
        "category": "extraction",
        "description": "Extracts named entities (people, places, organizations, dates)",
        "input": "Text string",
        "output": "JSON with lists of entities by type",
        "prompt": """Extract named entities from the given text.

Identify people, organizations, locations, dates, and other important entities.

Return JSON format:
{
    "people": ["name1", "name2"],
    "organizations": ["org1", "org2"],
    "locations": ["place1", "place2"],
    "dates": ["date1", "date2"],
    "money": ["$100", "€50"],
    "other": ["entity1", "entity2"]
}"""
    },

    "key_phrase_extractor": {
        "category": "extraction",
        "description": "Extracts key phrases and important terms from text",
        "input": "Text string",
        "output": "JSON with list of key phrases and their importance scores",
        "prompt": """Extract key phrases from the given text.

Identify the most important phrases, terms, and concepts.

Return JSON format:
{
    "key_phrases": [
        {"phrase": "...", "importance": 0.0-1.0},
        {"phrase": "...", "importance": 0.0-1.0}
    ],
    "main_topics": ["topic1", "topic2"]
}"""
    },

    "contact_extractor": {
        "category": "extraction",
        "description": "Extracts contact information (emails, phones, addresses)",
        "input": "Text string",
        "output": "JSON with extracted contact details",
        "prompt": """Extract contact information from the given text.

Identify email addresses, phone numbers, physical addresses, and websites.

Return JSON format:
{
    "emails": ["email1@example.com", "email2@example.com"],
    "phones": ["+1-555-0100", "555-0101"],
    "addresses": ["123 Main St, City, State"],
    "websites": ["https://example.com"],
    "social_media": ["@username", "@handle"]
}"""
    },

    "date_time_extractor": {
        "category": "extraction",
        "description": "Extracts and normalizes dates, times, and durations",
        "input": "Text string",
        "output": "JSON with extracted temporal information",
        "prompt": """Extract dates, times, and durations from the given text.

Identify and normalize all temporal references.

Return JSON format:
{
    "dates": ["2025-02-02", "2025-03-15"],
    "times": ["14:30", "09:00"],
    "durations": ["2 hours", "3 days"],
    "relative_times": ["tomorrow", "next week"],
    "deadlines": ["by Friday", "before noon"]
}"""
    },

    # ========================================================================
    # SUMMARIZATION & TRANSFORMATION
    # ========================================================================

    "text_summarizer": {
        "category": "summarization",
        "description": "Creates concise summaries of longer text",
        "input": "Text string",
        "output": "JSON with summary and key points",
        "prompt": """Summarize the given text concisely.

Create a brief summary capturing the main points.

Return JSON format:
{
    "summary": "concise summary in 2-3 sentences",
    "key_points": ["point1", "point2", "point3"],
    "word_count_original": N,
    "word_count_summary": M
}"""
    },

    "bullet_point_creator": {
        "category": "summarization",
        "description": "Converts text into bullet point format",
        "input": "Text string",
        "output": "JSON with bullet points",
        "prompt": """Convert the given text into bullet points.

Extract the main ideas and format as clear, concise bullet points.

Return JSON format:
{
    "bullet_points": [
        "• First main point",
        "• Second main point",
        "• Third main point"
    ],
    "count": N
}"""
    },

    "title_generator": {
        "category": "summarization",
        "description": "Generates titles or headlines for text content",
        "input": "Text string",
        "output": "JSON with suggested titles",
        "prompt": """Generate compelling titles for the given text.

Create 3-5 title options that are concise, engaging, and accurate.

Return JSON format:
{
    "titles": [
        "Title Option 1",
        "Title Option 2",
        "Title Option 3"
    ],
    "recommended": "Title Option 1",
    "reasoning": "why this title is recommended"
}"""
    },

    "question_generator": {
        "category": "summarization",
        "description": "Generates questions that the text answers",
        "input": "Text string",
        "output": "JSON with generated questions",
        "prompt": """Generate questions that are answered by the given text.

Create 3-5 questions that help understand the content.

Return JSON format:
{
    "questions": [
        "Question 1?",
        "Question 2?",
        "Question 3?"
    ]
}"""
    },

    # ========================================================================
    # QUALITY & GRAMMAR
    # ========================================================================

    "grammar_checker": {
        "category": "quality",
        "description": "Detects grammar, spelling, and punctuation errors",
        "input": "Text string",
        "output": "JSON with errors and suggestions",
        "prompt": """Check the given text for grammar, spelling, and punctuation errors.

Return JSON format:
{
    "has_errors": true/false,
    "error_count": N,
    "errors": [
        {
            "type": "grammar" | "spelling" | "punctuation",
            "text": "problematic text",
            "suggestion": "corrected version",
            "explanation": "brief explanation"
        }
    ],
    "overall_quality": "excellent" | "good" | "fair" | "poor"
}"""
    },

    "style_checker": {
        "category": "quality",
        "description": "Checks writing style and suggests improvements",
        "input": "Text string",
        "output": "JSON with style issues and suggestions",
        "prompt": """Analyze the writing style of the given text.

Check for clarity, conciseness, consistency, and engagement.

Return JSON format:
{
    "clarity_score": 0.0-1.0,
    "conciseness_score": 0.0-1.0,
    "engagement_score": 0.0-1.0,
    "issues": [
        {
            "type": "passive_voice" | "wordiness" | "repetition" | "jargon",
            "text": "problematic text",
            "suggestion": "improved version"
        }
    ],
    "overall_assessment": "brief assessment"
}"""
    },

    "plagiarism_indicator": {
        "category": "quality",
        "description": "Indicates potential plagiarism or copied content patterns",
        "input": "Text string",
        "output": "JSON with plagiarism indicators",
        "prompt": """Analyze the given text for indicators of plagiarism or copied content.

Look for patterns that suggest copied text, lack of original thought, or citation issues.

Return JSON format:
{
    "risk_level": "low" | "medium" | "high",
    "indicators": [
        "inconsistent writing style",
        "lack of citations for factual claims",
        "overly formal or technical language shifts"
    ],
    "recommendation": "brief recommendation"
}"""
    },

    # ========================================================================
    # COMPARISON & SIMILARITY
    # ========================================================================

    "duplicate_detector": {
        "category": "comparison",
        "description": "Detects if text is a duplicate or near-duplicate",
        "input": "Two text strings (concatenated with separator)",
        "output": "JSON with similarity score and duplicate status",
        "prompt": """Compare the two texts separated by "---SEPARATOR---".

Determine if they are duplicates, near-duplicates, or distinct.

Return JSON format:
{
    "is_duplicate": true/false,
    "similarity_score": 0.0-1.0,
    "duplicate_type": "exact" | "near" | "paraphrase" | "distinct",
    "reasoning": "brief explanation"
}"""
    },

    "contradiction_detector": {
        "category": "comparison",
        "description": "Detects contradictions between two statements",
        "input": "Two text strings (concatenated with separator)",
        "output": "JSON with contradiction analysis",
        "prompt": """Compare the two statements separated by "---SEPARATOR---".

Determine if they contradict each other, agree, or are unrelated.

Return JSON format:
{
    "relationship": "contradiction" | "agreement" | "neutral" | "unrelated",
    "confidence": 0.0-1.0,
    "explanation": "detailed explanation of the relationship"
}"""
    },

    # ========================================================================
    # SPECIALIZED ANALYSIS
    # ========================================================================

    "fact_checker": {
        "category": "specialized",
        "description": "Identifies factual claims that can be verified",
        "input": "Text string",
        "output": "JSON with factual claims and verification status",
        "prompt": """Identify factual claims in the given text.

Extract claims that can potentially be fact-checked.

Return JSON format:
{
    "claims": [
        {
            "claim": "specific factual statement",
            "verifiable": true/false,
            "confidence": 0.0-1.0
        }
    ],
    "overall_factuality": "mostly_factual" | "mixed" | "mostly_opinion"
}"""
    },

    "bias_detector": {
        "category": "specialized",
        "description": "Detects potential bias in text",
        "input": "Text string",
        "output": "JSON with bias analysis",
        "prompt": """Analyze the given text for potential bias.

Identify political, ideological, or other biases in language and framing.

Return JSON format:
{
    "has_bias": true/false,
    "bias_types": ["political", "ideological", "confirmation", "selection"],
    "bias_direction": "left" | "right" | "center" | "unclear" | "multiple",
    "confidence": 0.0-1.0,
    "indicators": ["biased phrase 1", "loaded term 2"],
    "reasoning": "brief explanation"
}"""
    },

    "call_to_action_detector": {
        "category": "specialized",
        "description": "Identifies calls-to-action in marketing or persuasive text",
        "input": "Text string",
        "output": "JSON with CTAs and their characteristics",
        "prompt": """Identify calls-to-action in the given text.

Extract phrases that encourage or direct the reader to take action.

Return JSON format:
{
    "has_cta": true/false,
    "ctas": [
        {
            "text": "Click here now",
            "type": "button" | "link" | "instruction",
            "urgency": "high" | "medium" | "low",
            "action": "purchase" | "subscribe" | "download" | "share" | "other"
        }
    ],
    "count": N
}"""
    },

    "sarcasm_detector": {
        "category": "specialized",
        "description": "Detects sarcasm and irony in text",
        "input": "Text string",
        "output": "JSON with sarcasm detection",
        "prompt": """Detect sarcasm or irony in the given text.

Return JSON format:
{
    "is_sarcastic": true/false,
    "confidence": 0.0-1.0,
    "sarcasm_type": "verbal_irony" | "overstatement" | "understatement" | "none",
    "indicators": ["excessive enthusiasm", "contradictory tone"],
    "literal_meaning": "what it says",
    "intended_meaning": "what it means"
}"""
    },
}


# ============================================================================
# Helper Functions for Browsing/Searching
# ============================================================================

def get_prompt(key: str) -> str:
    """
    Get a prompt string by key.

    Args:
        key: Prompt identifier (e.g., "sentiment_analyzer")

    Returns:
        The prompt string

    Raises:
        KeyError: If prompt key doesn't exist

    Example:
        >>> from components.transformers.prompts import get_prompt
        >>> prompt = get_prompt("sentiment_analyzer")
    """
    if key not in PROMPTS:
        available = list(PROMPTS.keys())
        raise KeyError(
            f"Prompt '{key}' not found.\n"
            f"Available prompts: {available}\n"
            f"Use print_prompt_catalog() to browse all prompts."
        )
    return PROMPTS[key]["prompt"]


def get_prompts_by_category(category: str) -> dict:
    """
    Get all prompts in a category.

    Args:
        category: Category name (e.g., "text_analysis", "content_filtering")

    Returns:
        Dictionary of prompts in that category

    Example:
        >>> from components.transformers.prompts import get_prompts_by_category
        >>> analysis_prompts = get_prompts_by_category("text_analysis")
    """
    return {
        key: value for key, value in PROMPTS.items()
        if value["category"] == category
    }


def list_categories() -> list:
    """
    Get list of all available categories.

    Returns:
        Sorted list of category names

    Example:
        >>> from components.transformers.prompts import list_categories
        >>> categories = list_categories()
        >>> print(categories)
        ['classification', 'comparison', 'content_filtering', ...]
    """
    return sorted(set(p["category"] for p in PROMPTS.values()))


def search_prompts(search_term: str) -> dict:
    """
    Search prompts by keyword in description or prompt text.

    Args:
        search_term: Term to search for (case-insensitive)

    Returns:
        Dictionary of matching prompts with their metadata

    Example:
        >>> from components.transformers.prompts import search_prompts
        >>> spam_prompts = search_prompts("spam")
        >>> urgent_prompts = search_prompts("urgent")
    """
    term = search_term.lower()
    results = {}

    for key, value in PROMPTS.items():
        if (term in key.lower() or
            term in value["description"].lower() or
            term in value["prompt"].lower() or
                term in value["category"].lower()):
            results[key] = value

    return results


def print_prompt_catalog():
    """
    Print a readable catalog of all available prompts.

    Displays prompts organized by category with descriptions, inputs, and outputs.

    Example:
        >>> from components.transformers.prompts import print_prompt_catalog
        >>> print_prompt_catalog()
    """
    print("\n" + "=" * 80)
    print("PROMPT LIBRARY CATALOG")
    print("=" * 80)
    print(f"\nTotal prompts: {len(PROMPTS)}")
    print(f"Categories: {len(list_categories())}")

    for category in list_categories():
        print(f"\n{'─' * 80}")
        print(f"📁 {category.upper().replace('_', ' ')}")
        print(f"{'─' * 80}")

        prompts = get_prompts_by_category(category)
        for key, value in sorted(prompts.items()):
            print(f"\n  🔹 {key}")
            print(f"     {value['description']}")
            print(f"     Input:  {value['input']}")
            print(f"     Output: {value['output']}")

    print("\n" + "=" * 80)
    print("Usage:")
    print("  from components.transformers.prompts import get_prompt")
    print("  from components.transformers.claude_agent import ClaudeAgent")
    print("  ")
    print("  agent = ClaudeAgent(get_prompt('sentiment_analyzer'))")
    print("=" * 80 + "\n")


def print_prompt_details(key: str):
    """
    Print detailed information about a specific prompt.

    Args:
        key: Prompt identifier

    Example:
        >>> from components.transformers.prompts import print_prompt_details
        >>> print_prompt_details("sentiment_analyzer")
    """
    if key not in PROMPTS:
        print(f"❌ Prompt '{key}' not found.")
        print(f"Available prompts: {list(PROMPTS.keys())}")
        return

    p = PROMPTS[key]
    print("\n" + "=" * 80)
    print(f"PROMPT: {key}")
    print("=" * 80)
    print(f"Category:    {p['category']}")
    print(f"Description: {p['description']}")
    print(f"Input:       {p['input']}")
    print(f"Output:      {p['output']}")
    print("\n" + "─" * 80)
    print("PROMPT TEXT:")
    print("─" * 80)
    print(p['prompt'])
    print("=" * 80 + "\n")


# ============================================================================
# Quick Start Guide
# ============================================================================

def print_quick_start():
    """Print a quick start guide for using the prompt library."""
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                        PROMPT LIBRARY QUICK START                          ║
╚════════════════════════════════════════════════════════════════════════════╝

1️⃣  BROWSE ALL PROMPTS:
   >>> from components.transformers.prompts import print_prompt_catalog
   >>> print_prompt_catalog()

2️⃣  SEARCH FOR PROMPTS:
   >>> from components.transformers.prompts import search_prompts
   >>> spam_prompts = search_prompts("spam")
   >>> print(spam_prompts.keys())

3️⃣  VIEW PROMPT DETAILS:
   >>> from components.transformers.prompts import print_prompt_details
   >>> print_prompt_details("sentiment_analyzer")

4️⃣  USE A PROMPT IN YOUR NETWORK:
   >>> from components.transformers.prompts import get_prompt
   >>> from components.transformers.claude_agent import ClaudeAgent
   >>> from dsl.blocks import Transform
   >>> 
   >>> analyzer = Transform(
   ...     fn=ClaudeAgent(get_prompt("sentiment_analyzer")).run,
   ...     name="sentiment"
   ... )

5️⃣  LIST CATEGORIES:
   >>> from components.transformers.prompts import list_categories
   >>> print(list_categories())

6️⃣  GET ALL PROMPTS IN A CATEGORY:
   >>> from components.transformers.prompts import get_prompts_by_category
   >>> text_analysis = get_prompts_by_category("text_analysis")
   >>> print(text_analysis.keys())

════════════════════════════════════════════════════════════════════════════

💡 TIP: You can also create custom prompts!

   >>> MY_PROMPT = \"\"\"Your custom prompt here...\"\"\"
   >>> custom_agent = Transform(
   ...     fn=ClaudeAgent(MY_PROMPT).run,
   ...     name="custom"
   ... )

════════════════════════════════════════════════════════════════════════════
""")


if __name__ == "__main__":
    # When run directly, show the catalog
    print_quick_start()
    print_prompt_catalog()
