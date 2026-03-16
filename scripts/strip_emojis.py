#!/usr/bin/env python3
"""Remove all emojis from markdown file for PDF generation."""

import sys
import re

def remove_emojis(text):
    """Remove all emoji characters from text."""
    # Emoji pattern (covers most emoji ranges)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"  # enclosed characters
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U0001FA00-\U0001FA6F"  # extended symbols
        "]+", 
        flags=re.UNICODE
    )
    return emoji_pattern.sub('', text)

if __name__ == "__main__":
    # Read from stdin or file
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        text = sys.stdin.read()
    
    # Remove emojis and print
    clean_text = remove_emojis(text)
    print(clean_text)
