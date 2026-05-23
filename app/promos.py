PROMOS: dict[str, int] = {
    "zondvpn": 7,
}


def get_promo_days(code: str) -> int | None:
    return PROMOS.get(code.strip().lower())
