"""Backup automático de configurações MikroTik e Huawei via SSH (netmiko).

Cada device é conectado via SSH, o comando de exportação de configuração é
executado, e o resultado é salvo em backups/<device>/<device>_<timestamp>.cfg.

Backups antigos são rotacionados conforme `settings.keep_last_n_backups`
no devices.yaml.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException

from .utils import ensure_dir, netmiko_device_type

logger = logging.getLogger("mkhw_toolkit.backup")

# Comando de export de configuração por vendor
EXPORT_COMMANDS = {
    "mikrotik": "/export verbose",
    "huawei": "display current-configuration",
}


def _connect_kwargs(device: dict) -> dict:
    return {
        "device_type": netmiko_device_type(device["vendor"]),
        "host": device["host"],
        "port": device.get("port", 22),
        "username": device["username"],
        "password": device["password"],
        "timeout": device.get("timeout", 20),
        "fast_cli": False,
    }


def backup_device(device: dict, backup_dir: str | Path) -> Path | None:
    """Conecta em um device e salva sua configuração atual. Retorna o Path salvo ou None em erro."""
    name = device["name"]
    vendor = device["vendor"].lower()
    command = EXPORT_COMMANDS.get(vendor)
    if command is None:
        logger.error("[%s] vendor '%s' sem comando de export definido", name, vendor)
        return None

    logger.info("[%s] conectando via SSH (%s)...", name, device["host"])
    try:
        with ConnectHandler(**_connect_kwargs(device)) as conn:
            output = conn.send_command(command, read_timeout=60)
    except NetmikoAuthenticationException:
        logger.error("[%s] falha de autenticação — verifique usuário/senha", name)
        return None
    except NetmikoTimeoutException:
        logger.error("[%s] timeout de conexão — dispositivo inacessível?", name)
        return None
    except Exception as exc:  # noqa: BLE001 - queremos logar qualquer falha e seguir para o próximo device
        logger.error("[%s] erro inesperado: %s", name, exc)
        return None

    device_dir = ensure_dir(Path(backup_dir) / name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = device_dir / f"{name}_{timestamp}.cfg"
    out_path.write_text(output, encoding="utf-8")
    logger.info("[%s] backup salvo em %s", name, out_path)
    return out_path


def rotate_backups(device_name: str, backup_dir: str | Path, keep_last_n: int) -> int:
    """Remove backups mais antigos que os `keep_last_n` mais recentes. Retorna quantos foram removidos."""
    device_dir = Path(backup_dir) / device_name
    if not device_dir.exists():
        return 0
    files = sorted(device_dir.glob(f"{device_name}_*.cfg"), key=lambda p: p.stat().st_mtime, reverse=True)
    to_remove = files[keep_last_n:]
    for f in to_remove:
        f.unlink()
        logger.debug("[%s] backup antigo removido: %s", device_name, f)
    return len(to_remove)


def backup_all(config: dict) -> list[Path]:
    """Executa backup de todos os devices definidos no config. Retorna lista de arquivos salvos."""
    settings = config.get("settings", {})
    backup_dir = ensure_dir(settings.get("backup_dir", "backups"))
    keep_last_n = settings.get("keep_last_n_backups", 30)

    saved = []
    for device in config.get("devices", []):
        result = backup_device(device, backup_dir)
        if result:
            saved.append(result)
            rotate_backups(device["name"], backup_dir, keep_last_n)
    return saved
