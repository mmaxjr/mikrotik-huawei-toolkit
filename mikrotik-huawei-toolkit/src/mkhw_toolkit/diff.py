"""Diff entre as duas versões de backup mais recentes de um device."""

from __future__ import annotations

import difflib
import logging
from datetime import datetime
from pathlib import Path

from .utils import ensure_dir

logger = logging.getLogger("mkhw_toolkit.diff")


def _last_two_backups(device_name: str, backup_dir: str | Path) -> list[Path]:
    device_dir = Path(backup_dir) / device_name
    if not device_dir.exists():
        return []
    files = sorted(device_dir.glob(f"{device_name}_*.cfg"), key=lambda p: p.stat().st_mtime)
    return files[-2:]


def diff_device(device_name: str, backup_dir: str | Path, reports_dir: str | Path) -> Path | None:
    """Gera um relatório de diff (unified diff) entre os dois últimos backups de um device."""
    files = _last_two_backups(device_name, backup_dir)
    if len(files) < 2:
        logger.warning(
            "[%s] menos de 2 backups disponíveis — nada para comparar", device_name
        )
        return None

    old_path, new_path = files
    old_lines = old_path.read_text(encoding="utf-8").splitlines(keepends=True)
    new_lines = new_path.read_text(encoding="utf-8").splitlines(keepends=True)

    diff_lines = list(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=old_path.name,
            tofile=new_path.name,
        )
    )

    reports_path = ensure_dir(reports_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = reports_path / f"{device_name}_diff_{timestamp}.txt"

    if not diff_lines:
        out_path.write_text(
            f"Nenhuma diferença encontrada entre {old_path.name} e {new_path.name}.\n",
            encoding="utf-8",
        )
        logger.info("[%s] sem alterações desde o último backup", device_name)
    else:
        out_path.write_text("".join(diff_lines), encoding="utf-8")
        logger.info(
            "[%s] %d linha(s) alteradas — relatório em %s",
            device_name,
            sum(1 for l in diff_lines if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))),
            out_path,
        )

    return out_path


def diff_all(config: dict) -> list[Path]:
    """Gera diff para todos os devices configurados."""
    settings = config.get("settings", {})
    backup_dir = settings.get("backup_dir", "backups")
    reports_dir = settings.get("reports_dir", "reports")

    reports = []
    for device in config.get("devices", []):
        result = diff_device(device["name"], backup_dir, reports_dir)
        if result:
            reports.append(result)
    return reports
