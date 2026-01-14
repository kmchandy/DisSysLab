# components/transforms/__init__.py

"""
Transforms: Processing nodes that modify or analyze messages.

Available transforms:
- ClaudeAgent: AI-powered analysis using Claude API (real, Module 9)
- MockClaudeAgent: Keyword-based analysis for testing (mock, Module 2)
"""

from .claude_agent import ClaudeAgent
from .mock_claude_agent import MockClaudeAgent
from .mock_AI_sentiment_analyzer import MockAISentimentAnalyzer
from .mock_AI_spam_filter import MockAISpamFilter
from .mock_AI_non_urgent_filter import MockAINonUrgentFilter

__all__ = ['ClaudeAgent', 'MockClaudeAgent', 'MockAISentimentAnalyzer',
           'MockAISpamFilter', 'MockAINonUrgentFilter']
