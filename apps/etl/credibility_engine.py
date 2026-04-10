"""
Credibility Scoring Engine

Assigns a credibility score in [0.1, 0.99] to a message author based on
source-specific signals and content analysis. The score is used as a weight
when computing credibility-weighted sentiment averages in the aggregation engine.

Scoring logic:
  Base score: 0.5
  Content penalties:
    - Each spam keyword found:  -0.1
    - Excessive emoji count:    -0.1 (if > 5 non-word characters)
  Reddit bonuses:
    - Post score > 10:          +0.1
    - Post score > 100:         +0.2
  Telegram adjustments:
    - Named username present:   +0.1
    - Identified as bot:        set to 0.1 (overrides all other signals)
  Final value clamped to [0.1, 0.99].
"""

import re


def calculate_credibility(source, metadata, content):
    """
    Computes a credibility score for a message based on source and content signals.

    Args:
        source (str): Data source — 'reddit' or 'telegram'.
        metadata (dict): Source-specific metadata:
            For Reddit:   {'score': int, 'id': str, 'url': str}
            For Telegram: {'username': str, 'is_bot': bool, 'sender_id': int, 'channel_id': int}
        content (str): The raw text content of the post or message.

    Returns:
        float: A credibility score clamped to [0.1, 0.99].
    """
    score = 0.5  # Base score

    # 1. Content Analysis (Spam Detection)
    spam_keywords = ['giveaway', 'free', 'dm me', 'whatsapp', 'pump', '100x', 'guaranteed']
    content_lower = content.lower()

    for word in spam_keywords:
        if word in content_lower:
            score -= 0.1

    # Too many emojis?
    emoji_count = len(re.findall(r'[^\w\s,.]', content))
    if emoji_count > 5:
        score -= 0.1

    # 2. Source Specific Logic
    if source == 'reddit':
        # Karma / Account Age heuristic
        # We might not have this in CSV but if we do...
        score += 0.1 if metadata.get('score', 0) > 10 else 0
        score += 0.2 if metadata.get('score', 0) > 100 else 0

    elif source == 'telegram':
        # User vs Bot
        if metadata.get('username'):
            score += 0.1
        if metadata.get('is_bot', False):
            score = 0.1  # Bots are low credibility

    # Clamp to valid range
    return max(0.1, min(0.99, score))
