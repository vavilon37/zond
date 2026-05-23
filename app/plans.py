from dataclasses import dataclass


@dataclass(frozen=True)
class Plan:
    id: str
    title: str
    days: int
    price_rub: int
    price_usdt: float


PLANS: list[Plan] = [
    Plan(id="1m", title="1 месяц", days=30, price_rub=200, price_usdt=2.0),
]


def get_plan(plan_id: str) -> Plan | None:
    return next((p for p in PLANS if p.id == plan_id), None)


TRIAL_DAYS = 3
REFERRAL_BONUS_DAYS = 3
