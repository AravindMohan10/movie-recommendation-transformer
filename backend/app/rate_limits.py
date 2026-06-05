"""Production vs dev rate limit strings for expensive routes."""
import os

_ENV = os.getenv("ENV", "production").lower()
_IS_PROD = _ENV == "production"

# Personalized / heavy endpoints (per user when token present)
RECOMMENDATIONS = "12/hour" if _IS_PROD else "60/minute"
HIDDEN_GEMS = "10/hour" if _IS_PROD else "30/minute"
SURPRISE_ME = "10/hour" if _IS_PROD else "30/minute"
MOOD = "8/hour" if _IS_PROD else "30/minute"
INTERACTIONS = "90/minute" if _IS_PROD else "120/minute"

# Public catalog (per IP)
MOVIES_RANDOM = "20/hour" if _IS_PROD else "60/minute"
MOVIES_BY_GENRE = "30/hour" if _IS_PROD else "60/minute"
MOVIES_SEARCH = "30/hour" if _IS_PROD else "60/minute"
MOVIES_JOURNEY = "15/hour" if _IS_PROD else "30/minute"
MOVIES_DETAIL = "120/hour" if _IS_PROD else "120/minute"
MOVIES_GENRES = "60/hour" if _IS_PROD else "120/minute"

# Auth
LOGIN = "8/minute"
SIGNUP = "4/minute"
HEALTH = "120/hour"
