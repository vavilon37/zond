import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    bot_token: str
    admin_ids: list[int]
    marzban_url: str
    marzban_username: str
    marzban_password: str
    marzban_inbound_tag: str
    cryptobot_token: str
    sbp_phone: str
    sbp_bank: str
    sbp_name: str
    db_path: str


def load_config() -> Config:
    admin_ids_raw = os.environ.get("ADMIN_IDS", "").strip()
    admin_ids = [int(x.strip()) for x in admin_ids_raw.split(",") if x.strip()]
    return Config(
        bot_token=os.environ["BOT_TOKEN"],
        admin_ids=admin_ids,
        marzban_url=os.environ["MARZBAN_URL"].rstrip("/"),
        marzban_username=os.environ["MARZBAN_USERNAME"],
        marzban_password=os.environ["MARZBAN_PASSWORD"],
        marzban_inbound_tag=os.environ.get("MARZBAN_INBOUND_TAG", "VLESS Reality"),
        cryptobot_token=os.environ["CRYPTOBOT_TOKEN"],
        sbp_phone=os.environ.get("SBP_PHONE", ""),
        sbp_bank=os.environ.get("SBP_BANK", ""),
        sbp_name=os.environ.get("SBP_NAME", ""),
        db_path=os.environ.get("DB_PATH", "data.sqlite3"),
    )
