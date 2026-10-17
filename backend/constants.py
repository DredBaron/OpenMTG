CONDITION_MULTIPLIERS = {
    "NM":  1.0,
    "LP":  0.75,
    "MP":  0.50,
    "HP":  0.25,
    "DMG": 0.10,
}


VERSIONS = {
    "API_VERSION": "1.10.0",
    "APPLICATION_VERSION": "1.10.0",
}

API_RATES = {
    "RATE_LIMIT_RPS": "2",
    "RATE_LIMIT_GAP": "0.5",
    "ERROR_429_BACKOFF": "60",
    "CALLER_TIMEOUT": "30",
}

# Largest card photo upload. Keep in step with MAX_PHOTO_BYTES in frontend/src/constants.js and
# the photo upload client_max_body_size in nginx.conf (which adds room for the form encoding).
MAX_PHOTO_BYTES = 10 * 1024 * 1024
