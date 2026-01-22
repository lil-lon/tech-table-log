"""
Configuration constants for podcast agents.
"""

from pathlib import Path

LOG_DIR = Path("./logs")
AUDIO_DIR = Path("./audio")

# Output directories
OUTPUT_DIR = Path("./output")
TRANSCRIPTS_DIR = OUTPUT_DIR / "transcripts"
MODIFIED_TRANSCRIPTS_DIR = OUTPUT_DIR / "modified_transcripts"
REVIEWS_DIR = OUTPUT_DIR / "reviews"
PLANS_DIR = OUTPUT_DIR / "plans"
