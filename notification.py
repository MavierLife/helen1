# ——— Configuración de Telegram ———
TELEGRAM_BOT_TOKEN = "8175238557:AAGXVzpknh0YrEJD288pBvX4CY4Yw-uNwH4"
TELEGRAM_CHAT_IDS = [
    "8167962334",
    "2010458571",
    "6412001592"
]

import os
import requests
import socket
import platform
from datetime import datetime

class TelegramNotifier:
    """Cliente simple para enviar alertas a un chat de Telegram."""

    def __init__(self, token=None, chat_ids=None):
        # Si no se pasan explícitamente, toma de las constantes
        self.token    = token    or TELEGRAM_BOT_TOKEN
        self.chat_ids = chat_ids or TELEGRAM_CHAT_IDS
        if not self.token or not self.chat_ids:
            raise ValueError("Falta TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_IDS")

    def send(self, text: str):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        for chat_id in self.chat_ids:
            payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
            resp = requests.post(url, data=payload, timeout=10)
            resp.raise_for_status()

    def notify_system_start(self, config: dict):
        # Datos de contexto
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        host = socket.gethostname()
        pyver = platform.python_version()
        params = "\n".join(f"• *{k}*: `{v}`" for k,v in config.items())
        text = (
            "*🚀 SISTEMA INICIADO*\n"
            f"🕒 `{now}` | 🖥 `{host}` | 🐍 `Python {pyver}`\n\n"
            "*📋 Parámetros de configuración:*\n"
            f"{params}\n\n"
            "_¡Backup a toda máquina!_ 🚀"
        )
        self.send(text)

    def notify_backup_error(self, error_msg: str):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        text = (
            "*💥 FALLO EN BACKUP*\n"
            f"🕒 `{now}`\n"
            f"❗️ *Error*: ```{error_msg}```\n\n"
            "_Revisa logs y espacio disponible._"
        )
        self.send(text)

    def notify_nightly_start(self, split_time: str, max_size_gb: float):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        text = (
            "*🌙 PROCESADOR NOCTURNO ARRANCA*\n"
            f"🕒 `{now}`\n"
            f"⏱ *Corte a las*: `{split_time}`\n"
            f"📦 *Máx. tamaño*: `{max_size_gb} GB`\n\n"
            "_Preparando archivos para la madrugada…_"
        )
        self.send(text)