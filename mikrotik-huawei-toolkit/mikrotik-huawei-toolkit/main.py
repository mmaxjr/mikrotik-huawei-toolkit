#!/usr/bin/env python3
"""CLI unificada do mkhw-toolkit.

Uso:
    python main.py backup                # backup de todos os devices
    python main.py diff                  # diff contra o backup anterior
    python main.py audit                 # auditoria de boas práticas
    python main.py run-all               # backup + diff + audit + notificação
    python main.py --config outro.yaml backup
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from mkhw_toolkit.audit import audit_all  # noqa: E402
from mkhw_toolkit.backup import backup_all  # noqa: E402
from mkhw_toolkit.diff import diff_all  # noqa: E402
from mkhw_toolkit.notifier import notify_audit_findings  # noqa: E402
from mkhw_toolkit.utils import load_config, setup_logging  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Toolkit de automação MikroTik/Huawei")
    parser.add_argument(
        "--config", default="config/devices.yaml", help="Caminho para o devices.yaml"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Log em modo debug")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("backup", help="Executa backup de todos os devices")
    subparsers.add_parser("diff", help="Compara os 2 últimos backups de cada device")
    subparsers.add_parser("audit", help="Roda checklist de boas práticas")
    subparsers.add_parser("run-all", help="backup + diff + audit + notificação Telegram")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    logger = setup_logging(args.verbose)

    try:
        config = load_config(args.config)
    except FileNotFoundError as exc:
        logger.error(str(exc))
        return 1

    if args.command == "backup":
        saved = backup_all(config)
        logger.info("Backup concluído: %d device(s) processado(s)", len(saved))

    elif args.command == "diff":
        reports = diff_all(config)
        logger.info("Diff concluído: %d relatório(s) gerado(s)", len(reports))

    elif args.command == "audit":
        findings = audit_all(config)
        notify_audit_findings(config, findings)
        logger.info("Auditoria concluída: %d achado(s)", len(findings))

    elif args.command == "run-all":
        backup_all(config)
        diff_all(config)
        findings = audit_all(config)
        notify_audit_findings(config, findings)
        logger.info("run-all concluído: %d achado(s) de auditoria", len(findings))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
