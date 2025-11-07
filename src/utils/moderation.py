# utils/moderation.py
import openai
from typing import Dict, Optional
import os

def moderate_content(text: str, api_key: Optional[str] = None) -> Dict:
    """
    Check if content violates OpenAI's usage policies.
    
    Args:
        text: Content to moderate
        api_key: OpenAI API key (uses env var if not provided)
    
    Returns:
        Dict with:
            - is_safe: bool
            - flagged_categories: list of violated categories
            - scores: dict of category scores
    """
    if not text or not text.strip():
        return {
            "is_safe": True,
            "flagged_categories": [],
            "scores": {}
        }
    
    try:
        # Get API key
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            print("[MODERATION] Warning: No API key found, skipping moderation")
            return {
                "is_safe": True,
                "flagged_categories": [],
                "scores": {},
                "error": "No API key"
            }
        
        # Call moderation API
        client = openai.OpenAI(api_key=key)
        response = client.moderations.create(input=text)
        
        result = response.results[0]
        
        # Extract flagged categories
        flagged = [
            category for category, flagged in result.categories.model_dump().items()
            if flagged
        ]
        
        print(f"[MODERATION] Content check - Flagged: {flagged if flagged else 'None'}")
        
        return {
            "is_safe": not result.flagged,
            "flagged_categories": flagged,
            "scores": result.category_scores.model_dump()
        }
        
    except Exception as e:
        print(f"[MODERATION] Error: {e}")
        # On error, allow content through (fail open) but log it
        return {
            "is_safe": True,
            "flagged_categories": [],
            "scores": {},
            "error": str(e)
        }


def get_moderation_message(flagged_categories: list) -> str:
    """
    Generate a user-friendly message for flagged content.
    """
    if not flagged_categories:
        return ""
    
    category_messages = {
        "hate": "hate speech or discrimination",
        "harassment": "harassment or bullying",
        "self-harm": "self-harm content",
        "sexual": "sexual content",
        "violence": "violent content",
        "hate/threatening": "threatening hate speech",
        "harassment/threatening": "threatening harassment",
        "self-harm/intent": "intent to self-harm",
        "self-harm/instructions": "self-harm instructions",
        "sexual/minors": "sexual content involving minors",
        "violence/graphic": "graphic violence"
    }
    
    issues = [category_messages.get(cat, cat) for cat in flagged_categories]
    
    if len(issues) == 1:
        return f"Your message was flagged for containing {issues[0]}."
    else:
        return f"Your message was flagged for containing: {', '.join(issues)}."