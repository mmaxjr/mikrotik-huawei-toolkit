"""Funções utilitárias compartilhadas: leitura de config, logging e helpers de arquivo."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

import yaml

ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z0-9_]+)\}")


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configura logging básico para toda a aplicação."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger("mkhw_toolkit")


def _expand_env(value: Any) -> Any:
    """Substitui recursivamente placeholders ${VAR} por variáveis de ambiente."""
    if isinstance(value, str):
        def replace(match: re.Match) -> str:
            var_name = match.group(1)
            return os.environ.get(var_name, "")

        return ENV_VAR_PATTERN.sub(replace, value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def load_config(config_path: str | Path = "config/devices.yaml") -> dict:
    """Carrega o YAML de configuração e expande variáveis de ambiente (senhas, tokens)."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Arquivo de configuração não encontrado: {path}. "
            "Copie config/devices.example.yaml para config/devices.yaml e preencha os dados."
        )
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return _expand_env(raw)


def ensure_dir(path: str | Path) -> Path:
    """Garante que um diretório exista e retorna o Path correspondente."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def netmiko_device_type(vendor: str) -> str:
    """Mapeia o vendor do devices.yaml para o device_type esperado pelo netmiko."""
    mapping = {
        "mikrotik": "mikrotik_routeros",
        "huawei": "huawei",
    }
    vendor_key = vendor.lower().strip()
    if vendor_key not in mapping:
        raise ValueError(
            f"Vendor '{vendor}' não suportado. Use um de: {', '.join(mapping)}"
        )
    return mapping[vendor_key]
