import json
import os
import sys
import logging
from typing import Optional
import requests

logger = logging.getLogger("superoffer.notifier")


def send_webhook(url: Optional[str], results_path: str, summary_text: str):
    if not url:
        return
    payload = {"text": summary_text, "results_file": results_path}
    if results_path and os.path.exists(results_path):
        try:
            with open(results_path, encoding="utf-8") as f:
                data = json.load(f)
            payload["superofertas"] = data.get("metadata", {}).get("superofertas_detectadas", 0)
            payload["total_productos"] = data.get("metadata", {}).get("total_productos", 0)
        except Exception:
            pass
    try:
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
        resp.raise_for_status()
        logger.info("Notificacion webhook enviada")
    except requests.RequestException as e:
        logger.warning("No se pudo enviar webhook: %s", e)


def send_telegram(token: str, chat_id: str, text: str):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=10)
        resp.raise_for_status()
        logger.info("Notificacion Telegram enviada")
    except requests.RequestException as e:
        logger.warning("No se pudo enviar Telegram: %s", e)


def send_discord(webhook_url: str, text: str, embeds: Optional[list] = None):
    payload = {"content": text}
    if embeds:
        payload["embeds"] = embeds
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("Notificacion Discord enviada")
    except requests.RequestException as e:
        logger.warning("No se pudo enviar Discord: %s", e)


def send_whatsapp(api_url: str, token: str, to: str, text: str):
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        resp = requests.post(api_url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        logger.info("Notificacion WhatsApp enviada")
    except requests.RequestException as e:
        logger.warning("No se pudo enviar WhatsApp: %s", e)


def send_notification(config: dict, results_path: str, summary_text: str, results_data: dict):
    notifiers = config.get("notifiers", {})
    text = summary_text
    if notifiers.get("telegram"):
        send_telegram(notifiers["telegram_token"], notifiers["telegram"], text)
    if notifiers.get("discord"):
        super_count = results_data.get("metadata", {}).get("superofertas_detectadas", 0)
        embed = {
            "title": "SuperOffer Resultados",
            "description": text,
            "color": 0xE74C3C if super_count > 0 else 0x3498DB,
            "fields": [
                {"name": "Super Ofertas", "value": str(super_count), "inline": True},
                {"name": "Productos", "value": str(results_data.get("metadata", {}).get("total_productos", 0)), "inline": True},
            ],
        }
        send_discord(notifiers["discord"], "", embeds=[embed])
    if notifiers.get("whatsapp"):
        send_whatsapp(notifiers["whatsapp_api_url"], notifiers["whatsapp_token"], notifiers["whatsapp"], text)
    webhook = config.get("defaults", {}).get("webhook") or os.environ.get("WEBHOOK_URL")
    if webhook:
        send_webhook(webhook, results_path, summary_text)
