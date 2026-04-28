import os
import json
import stripe
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.subscription import Subscription
from app.routes.api.auth import get_current_user

from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
IS_DEV = os.getenv("APP_ENV", "development") == "development"

PLAN_PRICE_MAP: dict[str, str] = {
    "smart":   os.getenv("STRIPE_PRICE_SMART", ""),
    "pro":     os.getenv("STRIPE_PRICE_PRO", ""),
    "premium": os.getenv("STRIPE_PRICE_PREMIUM", ""),
}
PRICE_PLAN_MAP: dict[str, str] = {v: k for k, v in PLAN_PRICE_MAP.items() if v}

router = APIRouter()


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_or_create_customer(user: User, db: Session) -> str:
    if user.stripe_customer_id:
        return user.stripe_customer_id
    customer = stripe.Customer.create(email=user.email, name=user.name)
    user.stripe_customer_id = customer.id
    db.commit()
    return customer.id


def _get_plan_id(plan_slug: str, db: Session):
    from sqlalchemy import text
    row = db.execute(
        text("SELECT id FROM plans WHERE slug = :slug LIMIT 1"),
        {"slug": plan_slug}
    ).fetchone()
    return row[0] if row else None


def _upsert_subscription(
    db: Session,
    user: User,
    stripe_subscription_id: str,
    plan_slug: str,
    status: str,
    started_at: datetime | None = None,
    expires_at: datetime | None = None,
):
    plan_id = _get_plan_id(plan_slug, db)

    existing = db.query(Subscription).filter(
        Subscription.gateway_subscription_id == stripe_subscription_id
    ).first()

    if existing:
        existing.status = status
        if expires_at:
            existing.expires_at = expires_at
        if plan_id:
            existing.plan_id = plan_id
    else:
        sub = Subscription(
            user_id=user.id,
            plan_id=plan_id,
            gateway="stripe",
            gateway_subscription_id=stripe_subscription_id,
            status=status,
            started_at=started_at or datetime.utcnow(),
            expires_at=expires_at,
        )
        db.add(sub)

    db.commit()


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.post("/create-checkout")
def create_checkout_session(
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan_key = (data.get("plan") or "").lower()
    price_id = PLAN_PRICE_MAP.get(plan_key)
    if not price_id:
        raise HTTPException(400, f"Plano '{plan_key}' inválido ou sem price_id configurado")

    customer_id = _get_or_create_customer(user, db)

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        subscription_data={"metadata": {"user_id": str(user.id), "plan": plan_key}},
        success_url=f"{FRONTEND_URL}/plans?success=1&plan={plan_key}&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{FRONTEND_URL}/plans?canceled=1",
        metadata={"user_id": str(user.id), "plan": plan_key},
    )
    return {"checkout_url": session.url}


@router.post("/verify-checkout")
def verify_checkout(
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session_id = data.get("session_id")
    if not session_id:
        raise HTTPException(400, "session_id é obrigatório")

    try:
        session = stripe.checkout.Session.retrieve(session_id, expand=["subscription"])
    except Exception as e:
        raise HTTPException(400, f"Erro ao consultar Stripe: {str(e)}")

    if session.payment_status != "paid":
        return {"status": "pending"}

    plan = (session.metadata or {}).get("plan") or (data.get("plan") or "").lower()
    if not plan:
        raise HTTPException(400, "Plano não identificado na sessão")

    if session.customer and not user.stripe_customer_id:
        user.stripe_customer_id = str(session.customer)

    sub = session.subscription
    sub_id = sub.id if hasattr(sub, "id") else (str(sub) if sub else None)

    # Datas do período
    started_at = datetime.utcfromtimestamp(sub.current_period_start) if hasattr(sub, "current_period_start") and sub.current_period_start else None
    expires_at  = datetime.utcfromtimestamp(sub.current_period_end)   if hasattr(sub, "current_period_end")   and sub.current_period_end   else None

    # Atualiza users
    user.plan = plan
    user.subscription_status = "active"
    if sub_id:
        user.stripe_subscription_id = sub_id

    # Grava / atualiza na tabela subscriptions
    if sub_id:
        _upsert_subscription(db, user, sub_id, plan, "active", started_at, expires_at)
    else:
        db.commit()

    return {"status": "success", "plan": plan}


@router.get("/portal")
def customer_portal(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user.stripe_customer_id:
        raise HTTPException(400, "Usuário sem assinatura ativa")

    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{FRONTEND_URL}/plans",
    )
    return {"portal_url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError as e:
        if IS_DEV:
            try:
                event = json.loads(payload)
                print(f"AVISO dev: assinatura ignorada. ({e})")
            except Exception:
                raise HTTPException(400, "Payload inválido")
        else:
            raise HTTPException(400, "Assinatura inválida")

    etype = event["type"]
    obj   = event["data"]["object"]
    print(f"Stripe webhook: {etype}")

    if etype == "checkout.session.completed":
        _handle_checkout_completed(obj, db)
    elif etype in ("customer.subscription.updated", "customer.subscription.created"):
        _handle_subscription_updated(obj, db)
    elif etype == "customer.subscription.deleted":
        _handle_subscription_deleted(obj, db)
    elif etype == "invoice.payment_failed":
        _handle_payment_failed(obj, db)

    return {"received": True}


# ── webhook handlers ──────────────────────────────────────────────────────────

def _handle_checkout_completed(session: dict, db: Session):
    user_id = (session.get("metadata") or {}).get("user_id")
    plan    = (session.get("metadata") or {}).get("plan")
    sub_id  = session.get("subscription")

    print(f"checkout.completed → user={user_id} plan={plan} sub={sub_id}")
    if not user_id or not plan:
        return

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return

    user.plan = plan
    user.stripe_subscription_id = sub_id
    user.subscription_status = "active"

    if sub_id:
        _upsert_subscription(db, user, sub_id, plan, "active")
    else:
        db.commit()


def _handle_subscription_updated(subscription: dict, db: Session):
    customer_id = subscription.get("customer")
    status      = subscription.get("status")
    sub_id      = subscription.get("id")

    items    = (subscription.get("items") or {}).get("data", [])
    price_id = items[0]["price"]["id"] if items else None
    plan     = PRICE_PLAN_MAP.get(price_id) if price_id else None

    started_at = datetime.utcfromtimestamp(subscription["current_period_start"]) if subscription.get("current_period_start") else None
    expires_at  = datetime.utcfromtimestamp(subscription["current_period_end"])   if subscription.get("current_period_end")   else None

    print(f"subscription.updated → customer={customer_id} status={status} plan={plan}")

    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if not user:
        return

    user.stripe_subscription_id = sub_id
    user.subscription_status = status
    if plan:
        user.plan = plan if status == "active" else "free"

    if sub_id and plan:
        _upsert_subscription(db, user, sub_id, plan if status == "active" else "free", status, started_at, expires_at)
    else:
        db.commit()


def _handle_subscription_deleted(subscription: dict, db: Session):
    customer_id = subscription.get("customer")
    sub_id      = subscription.get("id")

    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if not user:
        return

    user.plan = "free"
    user.stripe_subscription_id = None
    user.subscription_status = "canceled"

    if sub_id:
        existing = db.query(Subscription).filter(
            Subscription.gateway_subscription_id == sub_id
        ).first()
        if existing:
            existing.status = "canceled"
            existing.expires_at = datetime.utcnow()

    db.commit()


def _handle_payment_failed(invoice: dict, db: Session):
    customer_id = invoice.get("customer")
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if not user:
        return

    user.subscription_status = "past_due"
    sub_id = user.stripe_subscription_id
    if sub_id:
        existing = db.query(Subscription).filter(
            Subscription.gateway_subscription_id == sub_id
        ).first()
        if existing:
            existing.status = "past_due"

    db.commit()
