"""Notificação via Telegram quando a auditoria encontra problemas."""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger("mkhw_toolkit.notifier")

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def send_telegram_message(bot_token: str, chat_id: str, text: str) -> bool:
    """Envia uma mensagem de texto via Telegram Bot API. Retorna True em caso de sucesso."""
    if not bot_token or not chat_id:
        logger.warning("Telegram não configurado (bot_token/chat_id ausentes) — notificação ignorada")
        return False

    url = TELEGRAM_API_URL.format(token=bot_token)
    try:
        resp = requests.post(
            url,
            data={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except requests.RequestException as exc:
        logger.error("Falha ao enviar notificação Telegram: %s", exc)
        return False


def notify_audit_findings(config: dict, findings: list[dict]) -> None:
    """Formata e envia os achados de auditoria via Telegram, se habilitado no config."""
    telegram_cfg = config.get("telegram", {})
    if not telegram_cfg.get("enabled", False):
        return
    if not findings:
        return

    severity_emoji = {"alta": "🔴", "media": "🟡", "baixa": "🔵"}
    lines = [f"*Auditoria mkhw-toolkit* — {len(findings)} achado(s)\n"]
    for f in findings:
        emoji = severity_emoji.get(f["severity"], "⚪")
        lines.append(f"{emoji} `{f['device']}` ({f['rule_id']}): {f['description']}")

    text = "\n".join(lines)
    send_telegram_message(
        bot_token=telegram_cfg.get("bot_token", ""),
        chat_id=telegram_cfg.get("chat_id", ""),
        text=text,
    )
