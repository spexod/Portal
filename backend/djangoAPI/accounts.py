"""
Email address confirmation for new accounts, and the mails registration sends.

The confirmation link carries a signed, time-limited token (django.core.signing, no table): the user's id and
address. POST /api/users/verify-email/ with the token activates the account (views.VerifyEmailView).
Registration answers the same way whether or not the address has an account (views.RegisterView): the
address's owner learns the difference from the mail, nobody else does.
"""
import logging
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.mail import send_mail

SALT = 'djangoAPI.email-verification'
log = logging.getLogger(__name__)


def verification_token(user) -> str:
    return signing.dumps({'user': user.pk, 'email': user.email}, salt=SALT)


def user_from_token(token: str):
    """The user a confirmation token names, or None when the token is invalid, expired or stale."""
    try:
        data = signing.loads(str(token), salt=SALT, max_age=settings.EMAIL_VERIFICATION_MAX_AGE)
    except signing.BadSignature:
        return None
    if not isinstance(data, dict):
        return None
    return get_user_model().objects.filter(pk=data.get('user'), email=data.get('email')).first()


def _send(subject: str, message: str, to: str) -> None:
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [to])
    except Exception:
        # a mail failure must not turn into an error response: that would reveal which addresses have accounts
        log.exception("Could not send the mail '%s'", subject)


def send_verification_mail(user) -> None:
    link = f"{settings.PUBLIC_SITE_URL}/VerifyEmail?token={quote(verification_token(user), safe='')}"
    days = settings.EMAIL_VERIFICATION_MAX_AGE.days
    _send("Confirm your email address for SpExoDisks",
          f"Welcome to SpExoDisks, {user.first_name}.\n\n"
          f"Open this link to confirm your email address and activate your account (it works for {days} days):\n"
          f"{link}\n\n"
          "If you did not register at SpExoDisks, ignore this mail: the account stays inactive.",
          user.email)


def send_existing_account_mail(user) -> None:
    _send("Your SpExoDisks account",
          f"Hello {user.first_name},\n\n"
          "someone, probably you, tried to register at SpExoDisks with this email address, which already has an "
          "account. You can log in with your password, or set a new one here:\n"
          f"{settings.PUBLIC_SITE_URL}/ResetPasswordRequest\n\n"
          "If this was not you, no action is needed: nothing about your account has changed.",
          user.email)
