import re

def calculate_credibility(source, metadata, content):
    """
    Calculates a credibility score (0.0 to 1.0) based on source metadata and content.
    
    Args:
        source (str): 'reddit' or 'telegram'
        metadata (dict): Dictionary containing user/post metadata
        content (str): The raw text content
        
    Returns:
        float: A score between 0.0 and 1.0
    """
    score = 0.5 # Base score
    
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
            score = 0.1 # Bots are low credibility
            
    # Clamp
    return max(0.1, min(0.99, score))
