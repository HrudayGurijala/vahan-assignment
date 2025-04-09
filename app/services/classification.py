from typing import List, Dict, Any
import re

def classify_paper(text: str, user_topics: List[str]) -> List[str]:
    """
    Classify paper text according to user-provided topics
    
    Args:
        text: Full text content of the paper
        user_topics: List of topics provided by the user
        
    Returns:
        List of matched topics
    """
    if not user_topics:
        return []
        
    # Convert text and topics to lowercase for case-insensitive matching
    text_lower = text.lower()
    
    # Count occurrences of each topic in the text
    topic_counts = {}
    for topic in user_topics:
        topic_lower = topic.lower()
        # Use word boundary to avoid partial matches
        pattern = r'\b' + re.escape(topic_lower) + r'\b'
        count = len(re.findall(pattern, text_lower))
        topic_counts[topic] = count
    
    # Filter topics that appear at least once
    matched_topics = [topic for topic, count in topic_counts.items() if count > 0]
    
    return matched_topics