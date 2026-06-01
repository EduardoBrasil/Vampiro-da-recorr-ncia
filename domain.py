TERMS_VERSION = "LGPD-OF-2026.05"

BANKS = [
    {"id": "nubank", "name": "Nubank", "initials": "Nu", "class": "nubank", "color": "#8a05be"},
    {"id": "itau", "name": "Itau", "initials": "It", "class": "itau", "color": "#ff7900"},
    {"id": "bradesco", "name": "Bradesco", "initials": "Br", "class": "bradesco", "color": "#e40d35"},
    {"id": "inter", "name": "Inter", "initials": "In", "class": "inter", "color": "#ff7900"},
    {"id": "bb", "name": "Banco do Brasil", "initials": "BB", "class": "default", "color": "#f8cf2c"},
]

RAW_TRANSACTIONS = [
    {"id": "sub_001", "descriptor": "EBN*NETFLIX.COM", "amount": 44.90, "bank": "nubank", "status": "active", "cancel_url": "https://www.netflix.com/cancelplan", "category": "streaming", "next_billing": "2026-06-01"},
    {"id": "sub_002", "descriptor": "SPOTIFYAB*SPOTIFY", "amount": 34.90, "bank": "itau", "status": "active", "cancel_url": "https://www.spotify.com/br/account/subscription/cancel/", "category": "music", "next_billing": "2026-06-09"},
    {"id": "sub_004", "descriptor": "EBNCANVA*PRO_BR", "amount": 89.90, "bank": "nubank", "status": "trial", "cancel_url": "https://www.canva.com/settings/purchase-history", "category": "software", "next_billing": "2026-05-31"},
    {"id": "sub_009", "descriptor": "UNKNOWN*REC_7A9X", "amount": 29.90, "bank": "bradesco", "status": "processing", "cancel_url": None, "category": "unknown", "next_billing": "2026-06-18"},
    {"id": "sub_404", "descriptor": "LEGACY*GYMCLUB", "amount": 79.90, "bank": "inter", "status": "active", "cancel_url": "broken", "category": "fitness", "next_billing": "2026-06-03"},
]

BRAND_RULES = [
    (r"NETFLIX", "Netflix", "netflix", "N"),
    (r"SPOTIFY", "Spotify Premium", "spotify", "S"),
    (r"CANVA", "Canva Pro", "canva", "C"),
    (r"GYMCLUB", "Gym Club", "default", "G"),
]
