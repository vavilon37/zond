import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    bot_token: str
    admin_ids: list[int]
    # 3X-UI panel
    xui_url: str
    xui_base_path: str
    xui_api_token: str
    xui_inbound_id: int
    xui_sub_base_url: str
    xui_sub_path: str
    # Payments
    cryptobot_token: str
    sbp_phone: str
    sbp_bank: str
    sbp_name: str
    # Storage
    db_path: str


def load_config() -> Config:
    admin_ids_raw = os.environ.get("ADMIN_IDS", "").strip()
    admin_ids = [int(x.strip()) for x in admin_ids_raw.split(",") if x.strip()]
    return Config(
        bot_token=os.environ["BOT_TOKEN"],
        admin_ids=admin_ids,
        xui_url=os.environ["XUI_URL"].rstrip("/"),
        xui_base_path=os.environ["XUI_BASE_PATH"],
        xui_api_token=os.environ["XUI_API_TOKEN"],
        xui_inbound_id=int(os.environ.get("XUI_INBOUND_ID", "1")),
        xui_sub_base_url=os.environ["XUI_SUB_BASE_URL"].rstrip("/"),
        xui_sub_path=os.environ["XUI_SUB_PATH"],
        cryptobot_token=os.environ["CRYPTOBOT_TOKEN"],
        sbp_phone=os.environ.get("SBP_PHONE", ""),
        sbp_bank=os.environ.get("SBP_BANK", ""),
        sbp_name=os.environ.get("SBP_NAME", ""),
        db_path=os.environ.get("DB_PATH", "data.sqlite3"),
    )
