from __future__ import annotations

import hashlib
import hmac
import secrets
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.orm import Session

from teste_streamlit.database import setting
from teste_streamlit.models import User

PASSWORD_ITERATIONS = 600_000
RESET_TOKEN_LIFETIME = timedelta(minutes=30)
DEFAULT_TEACHER_DOMAINS = {"ifc.edu.br"}
DEFAULT_STUDENT_DOMAINS = {"estudantes.ifc.edu.br"}


class AuthenticationError(ValueError):
    pass


def _domains(setting_name: str, defaults: set[str]) -> set[str]:
    configured = setting(setting_name)
    if configured is None:
        return defaults
    return {domain.strip().lower() for domain in configured.split(",") if domain.strip()}


def role_for_email(email: str, requested_role: str | None = None) -> str:
    normalized = email.strip().lower()
    if normalized.count("@") != 1:
        raise AuthenticationError("Informe um e-mail institucional válido.")
    local_part, domain = normalized.rsplit("@", 1)
    allowed_local_characters = "._+-!#$%&'*=?^`{|}~/"
    if (
        len(normalized) > 254
        or not local_part
        or not domain
        or local_part.startswith(".")
        or local_part.endswith(".")
        or ".." in local_part
        or any(
            not character.isalnum() and character not in allowed_local_characters
            for character in local_part
        )
    ):
        raise AuthenticationError("Informe um e-mail institucional válido.")
    if domain in _domains("STUDENT_EMAIL_DOMAINS", DEFAULT_STUDENT_DOMAINS):
        email_role = "student"
    elif domain in _domains("TEACHER_EMAIL_DOMAINS", DEFAULT_TEACHER_DOMAINS):
        email_role = "teacher"
    else:
        raise AuthenticationError("Use um e-mail institucional do IFC.")
    if requested_role is not None and requested_role != email_role:
        raise AuthenticationError(
            "O e-mail institucional informado não corresponde ao perfil selecionado."
        )
    return email_role


def hash_password(password: str) -> str:
    if len(password) < 10:
        raise AuthenticationError("A senha deve ter pelo menos 10 caracteres.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def register_user(
    session: Session,
    full_name: str,
    email: str,
    password: str,
    role: str | None = None,
) -> User:
    name = full_name.strip()
    normalized_email = email.strip().lower()
    if not name:
        raise AuthenticationError("Informe seu nome.")
    verified_role = role_for_email(normalized_email, role)
    if session.scalar(select(User).where(User.email == normalized_email)):
        raise AuthenticationError("Já existe uma conta para este e-mail.")

    user = User(
        full_name=name,
        email=normalized_email,
        role=verified_role,
        password_hash=hash_password(password),
    )
    session.add(user)
    session.flush()
    return user


def authenticate(session: Session, email: str, password: str) -> User:
    user = session.scalar(
        select(User).where(User.email == email.strip().lower())
    )
    if user is None or not verify_password(password, user.password_hash):
        raise AuthenticationError("E-mail ou senha incorretos.")
    return user


def _send_email(recipient: str, subject: str, body: str) -> None:
    host = setting("SMTP_HOST")
    sender = setting("SMTP_FROM_EMAIL") or setting("SMTP_USERNAME")
    if not host or not sender:
        raise RuntimeError("Configure SMTP_HOST e SMTP_FROM_EMAIL para enviar e-mails.")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message.set_content(body)

    port = int(setting("SMTP_PORT", "587") or "587")
    username = setting("SMTP_USERNAME")
    password = setting("SMTP_PASSWORD")
    use_tls = (setting("SMTP_USE_TLS", "true") or "true").lower() in {
        "1",
        "true",
        "yes",
    }
    with smtplib.SMTP(host, port, timeout=15) as server:
        if use_tls:
            server.starttls(context=ssl.create_default_context())
        if username and password:
            server.login(username, password)
        server.send_message(message)


def request_password_reset(session: Session, email: str) -> bool:
    normalized_email = email.strip().lower()
    user = session.scalar(select(User).where(User.email == normalized_email))
    if user is None:
        return False

    token = secrets.token_urlsafe(32)
    user.reset_token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    user.reset_expires_at = datetime.now(timezone.utc) + RESET_TOKEN_LIFETIME
    session.flush()
    _send_email(
        user.email,
        "Redefinição de senha - Organizador de Laboratório",
        "Recebemos uma solicitação para redefinir sua senha.\n\n"
        f"Seu código de redefinição é:\n{token}\n\n"
        "Na tela de recuperação do Organizador de Laboratório, informe este código. "
        "Ele expira em 30 minutos. Se você não solicitou a troca, ignore esta mensagem.",
    )
    return True


def reset_password(
    session: Session, email: str, token: str, new_password: str
) -> User:
    normalized_email = email.strip().lower()
    user = session.scalar(select(User).where(User.email == normalized_email))
    if (
        user is None
        or user.reset_token_hash is None
        or user.reset_expires_at is None
    ):
        raise AuthenticationError("Código inválido ou expirado.")

    expires_at = user.reset_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    supplied_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    if (
        datetime.now(timezone.utc) > expires_at
        or not hmac.compare_digest(supplied_hash, user.reset_token_hash)
    ):
        raise AuthenticationError("Código inválido ou expirado.")

    user.password_hash = hash_password(new_password)
    user.reset_token_hash = None
    user.reset_expires_at = None
    session.flush()
    return user
