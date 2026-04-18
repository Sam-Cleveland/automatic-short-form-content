"""Text substitution dictionaries used by the cleaner.

Kept separate from the cleaner so they can be tweaked or swapped without touching
logic. Order matters for `SLANG`: longer keys first so `AITAH` expands before
`AITA` can match its prefix.
"""

# Display-time profanity censoring. Substring-matched (no word boundary) so
# `asshole` → `a**hole` also covers `assholes` → `a**holes`.
CENSOR: dict[str, str] = {
    "asshole": "a**hole",
    "porn": "p*rn",
    "fuck": "f***",
    "shit": "sh**",
    "damn": "d*mn",
    "bitch": "b*tch",
    "cunt": "c*nt",
    "dick": "d***",
    "weed": "w***",
    "sex": "s*x",
    "suicid": "suic*d",
    "penis": "pen*s",
    "cum": "c*m",
    "horny": "h*rny",
    "jizz": "j*zz",
}

# Reddit-isms and acronyms expanded for TTS. Word-boundary-matched,
# case-insensitive. Order matters (longer keys first).
SLANG: dict[str, str] = {
    "AITAH": "Am I the A-hole here",
    "AITA": "Am I the A-hole",
    "PP": "Post Partum",
    "SIL": "Sister-in-law",
    "MIL": "Mother-in-law",
    "FIL": "Father-in-law",
    "DIL": "Daughter-in-law",
    "[NF]": "",
    "NF": "",
    "TIFU": "Today I Effed Up",
}

# Raw regex → replacement. Applied before TTS synthesis to improve prosody.
TTS_FIXES: dict[str, str] = {
    r"\.\.[\.]*": ",",  # runs of ellipses → a single comma-pause
}
