"""The backend matcher's normalize (Devanagari -> ITRANS Latin, lower-cased, letters only),
imported from src/matcher.py so the model and the app always compare text the same way."""
import os
import sys

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
sys.path.insert(0, SRC)

from matcher import has_devanagari, normalize  # noqa: E402

__all__ = ["SRC", "has_devanagari", "normalize"]
