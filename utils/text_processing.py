"""Text processing utilities for response formatting."""

import re
from typing import Any


def remove_think_tags(text: str) -> str:
    """
    Remove <think>...</think> tags and their content from text.
    
    This function is used to clean up responses from models like sonar-reasoning
    that include reasoning content wrapped in think tags.
    
    Args:
        text: The input text that may contain think tags
        
    Returns:
        Clean text with think tags and their content removed
        
    Examples:
        >>> text = "<think>reasoning here</think>\\n\\nActual response"
        >>> remove_think_tags(text)
        "Actual response"
        
        >>> text = "Response without think tags"
        >>> remove_think_tags(text)
        "Response without think tags"
    """
    # Pattern to match <think>...</think> tags including content within them
    # Using DOTALL flag to match newlines within the tags
    think_pattern = r'<think>.*?</think>\s*'
    
    # Remove all think tag blocks
    cleaned_text = re.sub(think_pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Strip any leading/trailing whitespace that might be left
    return cleaned_text.strip()


def clean_perplexity_response(response: Any) -> Any:
    """
    Clean Perplexity API response by removing think tags from the content.
    
    This function handles the complete response object and cleans the content
    while preserving the rest of the response structure.
    
    Args:
        response: Perplexity API response object
        
    Returns:
        Response object with cleaned content
    """
    if not hasattr(response, 'choices') or not response.choices:
        return response
    
    # Clean the content in each choice
    for choice in response.choices:
        if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
            choice.message.content = remove_think_tags(choice.message.content)
    
    return response
