# components/transformers/prompts.py

"""
Prompt Library for AI-Powered Transforms

Simple constants for easy import and use with IDE autocomplete.

Usage:
    from components.transformers.prompts import SENTIMENT_ANALYZER
    from components.transformers.ai_agent import AI_function
    from dsl.blocks import Transform
    
    # Use a prompt constant
    analyzer = Transform(
        fn=AI_function(SENTIMENT_ANALYZER),
        name="sentiment"
    )
"""

# ============================================================================
# TEXT ANALYSIS
# ============================================================================

SENTIMENT_ANALYZER = """Analyze the sentiment of the given text.

Determine if the text expresses positive, negative, or neutral sentiment.
Provide a score from -1.0 (very negative) to +1.0 (very positive).

Return JSON format:
{
    "sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL",
    "score": -1.0 to +1.0,
    "reasoning": "brief explanation of the sentiment"
}"""

EMOTION_DETECTOR = """Detect emotions in the given text.

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

TONE_ANALYZER = """Analyze the tone of the given text.

Determine the overall tone: formal, casual, professional, friendly, aggressive, sarcastic, humorous, serious.

Return JSON format:
{
    "tone": "formal" | "casual" | "professional" | "friendly" | "aggressive" | "sarcastic" | "humorous" | "serious",
    "confidence": 0.0-1.0,
    "formality_score": 0.0-1.0,
    "reasoning": "brief explanation"
}"""

READABILITY_ANALYZER = """Analyze the readability of the given text.

Assess reading difficulty, complexity, and target audience level.

Return JSON format:
{
    "reading_level": "elementary" | "middle_school" | "high_school" | "college" | "graduate" | "expert",
    "complexity_score": 0.0-1.0,
    "estimated_grade": 1-16,
    "issues": ["long sentences", "complex vocabulary", etc],
    "reasoning": "brief explanation"
}"""

# ============================================================================
# CONTENT FILTERING & MODERATION
# ============================================================================

SPAM_DETECTOR = """Analyze if the given text is spam.

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

URGENCY_DETECTOR = """Analyze the urgency level of the given text.

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

TOXICITY_DETECTOR = """Analyze if the given text contains toxic or inappropriate content.

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

PROFANITY_FILTER = """Detect profanity in the given text.

Return JSON format:
{
    "contains_profanity": true/false,
    "severity": "none" | "mild" | "moderate" | "severe",
    "count": 0-N,
    "types": ["mild_profanity", "strong_profanity", "sexual", etc]
}"""

# ============================================================================
# CLASSIFICATION
# ============================================================================

TOPIC_CLASSIFIER = """Classify the given text into topic categories.

Categories: technology, business, science, health, sports, entertainment, politics, education, finance, other

Return JSON format:
{
    "primary_topic": "category name",
    "confidence": 0.0-1.0,
    "all_topics": ["topic1", "topic2"],
    "reasoning": "brief explanation"
}"""

LANGUAGE_DETECTOR = """Detect the language of the given text.

Return JSON format:
{
    "language": "en" | "es" | "fr" | "de" | "zh" | "ja" | etc,
    "language_name": "English" | "Spanish" | "French" | etc,
    "confidence": 0.0-1.0
}"""

INTENT_CLASSIFIER = """Classify the intent of the given text.

Intent types: question, command, statement, complaint, request, greeting, thanks, other

Return JSON format:
{
    "intent": "question" | "command" | "statement" | "complaint" | "request" | "greeting" | "thanks" | "other",
    "confidence": 0.0-1.0,
    "sub_intent": "specific type if applicable",
    "reasoning": "brief explanation"
}"""

PRIORITY_CLASSIFIER = """Classify the priority of the given text.

Consider urgency, importance, deadlines, and impact.

Return JSON format:
{
    "priority": "critical" | "high" | "medium" | "low",
    "urgency": 0-10,
    "importance": 0-10,
    "reasoning": "brief explanation"
}"""

# ============================================================================
# EXTRACTION
# ============================================================================

ENTITY_EXTRACTOR = """Extract named entities from the given text.

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

KEY_PHRASE_EXTRACTOR = """Extract key phrases from the given text.

Identify the most important phrases, terms, and concepts.

Return JSON format:
{
    "key_phrases": [
        {"phrase": "...", "importance": 0.0-1.0},
        {"phrase": "...", "importance": 0.0-1.0}
    ],
    "main_topics": ["topic1", "topic2"]
}"""

CONTACT_EXTRACTOR = """Extract contact information from the given text.

Identify email addresses, phone numbers, physical addresses, and websites.

Return JSON format:
{
    "emails": ["email1@example.com", "email2@example.com"],
    "phones": ["+1-555-0100", "555-0101"],
    "addresses": ["123 Main St, City, State"],
    "websites": ["https://example.com"],
    "social_media": ["@username", "@handle"]
}"""

DATE_TIME_EXTRACTOR = """Extract dates, times, and durations from the given text.

Identify and normalize all temporal references.

Return JSON format:
{
    "dates": ["2025-02-02", "2025-03-15"],
    "times": ["14:30", "09:00"],
    "durations": ["2 hours", "3 days"],
    "relative_times": ["tomorrow", "next week"],
    "deadlines": ["by Friday", "before noon"]
}"""

# ============================================================================
# SUMMARIZATION & TRANSFORMATION
# ============================================================================

TEXT_SUMMARIZER = """Summarize the given text concisely.

Create a brief summary capturing the main points.

Return JSON format:
{
    "summary": "concise summary in 2-3 sentences",
    "key_points": ["point1", "point2", "point3"],
    "word_count_original": N,
    "word_count_summary": M
}"""

BULLET_POINT_CREATOR = """Convert the given text into bullet points.

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

TITLE_GENERATOR = """Generate compelling titles for the given text.

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

QUESTION_GENERATOR = """Generate questions that are answered by the given text.

Create 3-5 questions that help understand the content.

Return JSON format:
{
    "questions": [
        "Question 1?",
        "Question 2?",
        "Question 3?"
    ]
}"""

# ============================================================================
# QUALITY & GRAMMAR
# ============================================================================

GRAMMAR_CHECKER = """Check the given text for grammar, spelling, and punctuation errors.

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

STYLE_CHECKER = """Analyze the writing style of the given text.

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

PLAGIARISM_INDICATOR = """Analyze the given text for indicators of plagiarism or copied content.

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

# ============================================================================
# COMPARISON & SIMILARITY
# ============================================================================

DUPLICATE_DETECTOR = """Compare the two texts separated by "---SEPARATOR---".

Determine if they are duplicates, near-duplicates, or distinct.

Return JSON format:
{
    "is_duplicate": true/false,
    "similarity_score": 0.0-1.0,
    "duplicate_type": "exact" | "near" | "paraphrase" | "distinct",
    "reasoning": "brief explanation"
}"""

CONTRADICTION_DETECTOR = """Compare the two statements separated by "---SEPARATOR---".

Determine if they contradict each other, agree, or are unrelated.

Return JSON format:
{
    "relationship": "contradiction" | "agreement" | "neutral" | "unrelated",
    "confidence": 0.0-1.0,
    "explanation": "detailed explanation of the relationship"
}"""

# ============================================================================
# SPECIALIZED ANALYSIS
# ============================================================================

FACT_CHECKER = """Identify factual claims in the given text.

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

BIAS_DETECTOR = """Analyze the given text for potential bias.

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

CALL_TO_ACTION_DETECTOR = """Identify calls-to-action in the given text.

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

SARCASM_DETECTOR = """Detect sarcasm or irony in the given text.

Return JSON format:
{
    "is_sarcastic": true/false,
    "confidence": 0.0-1.0,
    "sarcasm_type": "verbal_irony" | "overstatement" | "understatement" | "none",
    "indicators": ["excessive enthusiasm", "contradictory tone"],
    "literal_meaning": "what it says",
    "intended_meaning": "what it means"
}"""


# ============================================================================
# Quick Reference
# ============================================================================

if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                        PROMPT LIBRARY - CONSTANTS                          ║
╚════════════════════════════════════════════════════════════════════════════╝

USAGE:
    from components.transformers.prompts import SENTIMENT_ANALYZER
    from components.transformers.ai_agent import AI_function
    from dsl.blocks import Transform
    
    analyzer = Transform(fn=AI_function(SENTIMENT_ANALYZER), name="sentiment")

AVAILABLE PROMPTS:

📊 TEXT ANALYSIS
   • SENTIMENT_ANALYZER - Positive/negative/neutral sentiment
   • EMOTION_DETECTOR - Joy, anger, sadness, fear, surprise
   • TONE_ANALYZER - Formal, casual, professional, friendly
   • READABILITY_ANALYZER - Reading difficulty level

🛡️  CONTENT FILTERING & MODERATION
   • SPAM_DETECTOR - Spam, phishing, scam detection
   • URGENCY_DETECTOR - Time-sensitive content detection
   • TOXICITY_DETECTOR - Inappropriate content flagging
   • PROFANITY_FILTER - Profane language detection

🏷️  CLASSIFICATION
   • TOPIC_CLASSIFIER - Technology, business, science, etc.
   • LANGUAGE_DETECTOR - Identify text language
   • INTENT_CLASSIFIER - Question, command, complaint, etc.
   • PRIORITY_CLASSIFIER - Critical, high, medium, low

🔍 EXTRACTION
   • ENTITY_EXTRACTOR - People, places, organizations
   • KEY_PHRASE_EXTRACTOR - Important terms and concepts
   • CONTACT_EXTRACTOR - Emails, phones, addresses
   • DATE_TIME_EXTRACTOR - Dates, times, durations

📝 SUMMARIZATION & TRANSFORMATION
   • TEXT_SUMMARIZER - Concise summaries
   • BULLET_POINT_CREATOR - Convert to bullet points
   • TITLE_GENERATOR - Generate titles/headlines
   • QUESTION_GENERATOR - Generate comprehension questions

✅ QUALITY & GRAMMAR
   • GRAMMAR_CHECKER - Grammar, spelling, punctuation
   • STYLE_CHECKER - Writing style analysis
   • PLAGIARISM_INDICATOR - Copied content detection

🔄 COMPARISON & SIMILARITY
   • DUPLICATE_DETECTOR - Find duplicate content
   • CONTRADICTION_DETECTOR - Find contradictions

🎯 SPECIALIZED ANALYSIS
   • FACT_CHECKER - Identify factual claims
   • BIAS_DETECTOR - Political/ideological bias
   • CALL_TO_ACTION_DETECTOR - Marketing CTAs
   • SARCASM_DETECTOR - Sarcasm and irony

════════════════════════════════════════════════════════════════════════════

💡 TIP: Type "from components.transformers.prompts import " in your IDE
         and use autocomplete to see all available prompts!

════════════════════════════════════════════════════════════════════════════
""")