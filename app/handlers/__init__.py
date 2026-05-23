from . import admin, buy, common, pay_crypto, pay_sbp, promo, referral, subs

ROUTERS = [
    admin.router,
    common.router,
    buy.router,
    pay_crypto.router,
    pay_sbp.router,
    subs.router,
    referral.router,
    promo.router,
]
