"""Auditoria de boas práticas de configuração para MikroTik e Huawei.

A auditoria roda sobre o backup mais recente de cada device (texto de
configuração já coletado por backup.py), então não exige nova conexão SSH.
Cada regra verifica presença/ausência de um padrão e recebe uma severidade.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("mkhw_toolkit.audit")


@dataclass
class Rule:
    rule_id: str
    description: str
    severity: str  # "alta" | "media" | "baixa"
    pattern: str
    expect_present: bool  # True = falha se o padrão NÃO existir; False = falha se existir


MIKROTIK_RULES = [
    Rule(
        "MK-01",
        "Serviço Telnet deve estar desabilitado (usar apenas SSH/Winbox seguro)",
        "alta",
        r"/ip service[\s\S]*?set telnet disabled=no",
        expect_present=False,
    ),
    Rule(
        "MK-02",
        "Serviço FTP deve estar desabilitado se não for utilizado",
        "media",
        r"/ip service[\s\S]*?set ftp disabled=no",
        expect_present=False,
    ),
    Rule(
        "MK-03",
        "Cliente NTP deve estar habilitado para garantir horário correto (logs, certificados)",
        "media",
        r"/system ntp client[\s\S]*?set enabled=yes",
        expect_present=True,
    ),
    Rule(
        "MK-04",
        "SNMP não deve usar community padrão 'public'",
        "alta",
        r'/snmp community[\s\S]*?name="public"',
        expect_present=False,
    ),
    Rule(
        "MK-05",
        "Logging remoto (remote syslog) deve estar configurado para correlação centralizada",
        "baixa",
        r"/system logging action[\s\S]*?remote",
        expect_present=True,
    ),
    Rule(
        "MK-06",
        "API service (porta 8728/8729) não deve estar aberto sem restrição de endereço",
        "media",
        r"/ip service[\s\S]*?set api disabled=no address=0\.0\.0\.0/0",
        expect_present=False,
    ),
]

HUAWEI_RULES = [
    Rule(
        "HW-01",
        "Telnet deve estar desabilitado em favor de STelnet (SSH)",
        "alta",
        r"user-interface vty[\s\S]*?protocol inbound telnet",
        expect_present=False,
    ),
    Rule(
        "HW-02",
        "NTP deve estar configurado para sincronização de horário",
        "media",
        r"^ntp-service unicast-server",
        expect_present=True,
    ),
    Rule(
        "HW-03",
        "SNMP não deve usar community padrão 'public'/'private'",
        "alta",
        r"snmp-agent community (read|write) public",
        expect_present=False,
    ),
    Rule(
        "HW-04",
        "Info-center (logging) deve estar habilitado",
        "baixa",
        r"info-center enable",
        expect_present=True,
    ),
    Rule(
        "HW-05",
        "VTY deve ter ACL aplicada para restringir acesso de gerência",
        "media",
        r"user-interface vty[\s\S]*?acl \d+ inbound",
        expect_present=True,
    ),
]

RULES_BY_VENDOR = {
    "mikrotik": MIKROTIK_RULES,
    "huawei": HUAWEI_RULES,
}


def _latest_backup(device_name: str, backup_dir: str | Path) -> Path | None:
    device_dir = Path(backup_dir) / device_name
    if not device_dir.exists():
        return None
    files = sorted(device_dir.glob(f"{device_name}_*.cfg"), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def audit_device(device: dict, backup_dir: str | Path) -> list[dict]:
    """Roda as regras de auditoria contra o backup mais recente do device.
    Retorna lista de findings (dicts) — apenas as regras que falharam.
    """
    name = device["name"]
    vendor = device["vendor"].lower()
    rules = RULES_BY_VENDOR.get(vendor)
    if rules is None:
        logger.warning("[%s] sem regras de auditoria para vendor '%s'", name, vendor)
        return []

    backup_path = _latest_backup(name, backup_dir)
    if backup_path is None:
        logger.warning("[%s] nenhum backup encontrado — rode 'backup' antes de 'audit'", name)
        return []

    text = backup_path.read_text(encoding="utf-8")
    findings = []
    for rule in rules:
        found = re.search(rule.pattern, text, re.MULTILINE) is not None
        failed = (rule.expect_present and not found) or (not rule.expect_present and found)
        if failed:
            findings.append(
                {
                    "device": name,
                    "rule_id": rule.rule_id,
                    "description": rule.description,
                    "severity": rule.severity,
                }
            )
    return findings


def audit_all(config: dict) -> list[dict]:
    """Executa auditoria em todos os devices e grava um relatório consolidado."""
    settings = config.get("settings", {})
    backup_dir = settings.get("backup_dir", "backups")
    reports_dir = Path(settings.get("reports_dir", "reports"))
    reports_dir.mkdir(parents=True, exist_ok=True)

    all_findings = []
    for device in config.get("devices", []):
        all_findings.extend(audit_device(device, backup_dir))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = reports_dir / f"audit_{timestamp}.md"

    lines = [f"# Relatório de auditoria — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
    if not all_findings:
        lines.append("Nenhum problema encontrado. ✅\n")
    else:
        severity_order = {"alta": 0, "media": 1, "baixa": 2}
        for finding in sorted(all_findings, key=lambda f: severity_order.get(f["severity"], 9)):
            lines.append(
                f"- **[{finding['severity'].upper()}]** `{finding['device']}` "
                f"({finding['rule_id']}): {finding['description']}"
            )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Relatório de auditoria salvo em %s (%d achado(s))", out_path, len(all_findings))

    return all_findings
