# mikrotik-huawei-toolkit


# mikrotik-huawei-toolkit

Toolkit de automação para redes com MikroTik e Huawei: backup automático de
configurações via SSH, diff entre versões e auditoria de boas práticas —
tudo via linha de comando, pronto para rodar agendado (cron/systemd).

Feito para quem administra NOC/rede de verdade e quer parar de puxar backup
na mão ou descobrir mudança de config só quando algo já quebrou.

## Funcionalidades

- **Backup automático** — conecta via SSH (netmiko) em roteadores MikroTik
  (`/export verbose`) e switches/routers Huawei (`display current-configuration`),
  salva com timestamp e rotaciona backups antigos automaticamente.
- **Diff entre versões** — compara os dois últimos backups de cada device e
  gera um relatório unified diff, mostrando exatamente o que mudou.
- **Auditoria de boas práticas** — checklist de segurança/config rodando
  sobre o backup coletado: Telnet/FTP habilitados, SNMP com community padrão,
  NTP não configurado, ausência de logging remoto, ACL de VTY, entre outros.
- **Agendamento pronto** — exemplos de `systemd timer` e `cron` para rodar
  tudo automaticamente todo dia.
- **Notificação via Telegram** — alerta automático quando a auditoria encontra
  problemas de severidade alta/média.

## Estrutura do projeto

```
mikrotik-huawei-toolkit/
├── main.py                      # CLI unificada (backup / diff / audit / run-all)
├── requirements.txt
├── config/
│   └── devices.example.yaml     # copie para devices.yaml e preencha
├── src/mkhw_toolkit/
│   ├── backup.py                # coleta de config via netmiko
│   ├── diff.py                  # unified diff entre backups
│   ├── audit.py                 # regras de boas práticas por vendor
│   ├── notifier.py              # notificação via Telegram
│   └── utils.py                 # config loader + helpers
├── deploy/
│   ├── systemd/                 # mkhw-backup.service + .timer
│   └── cron/                    # crontab.example
├── backups/                     # gerado em runtime (gitignored)
└── reports/                     # gerado em runtime (gitignored)
```

## Instalação

```bash
git clone https://github.com/<seu-usuario>/mikrotik-huawei-toolkit.git
cd mikrotik-huawei-toolkit
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuração

1. Copie o arquivo de exemplo:

   ```bash
   cp config/devices.example.yaml config/devices.yaml
   ```

2. Preencha os devices no `config/devices.yaml`. Use variáveis de ambiente
   para senhas (nunca deixe senha em texto puro no arquivo):

   ```bash
   export MKHW_PASS_CORE_MIKROTIK_01='sua-senha-aqui'
   export MKHW_PASS_EDGE_HUAWEI_01='outra-senha'
   ```

3. (Opcional) Habilite notificação Telegram no mesmo arquivo, configurando
   `telegram.enabled: true` e exportando `MKHW_TELEGRAM_BOT_TOKEN` e
   `MKHW_TELEGRAM_CHAT_ID`.

## Uso

```bash
# Backup de todos os devices
python main.py backup

# Diff entre os 2 últimos backups de cada device
python main.py diff

# Auditoria de boas práticas (gera relatório em reports/)
python main.py audit

# Tudo de uma vez: backup + diff + audit + notificação
python main.py run-all

# Usar outro arquivo de config e log em modo debug
python main.py --config config/outro.yaml -v run-all
```

## Agendamento

**systemd (recomendado em servidores Linux):**

```bash
sudo cp deploy/systemd/mkhw-backup.service /etc/systemd/system/
sudo cp deploy/systemd/mkhw-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mkhw-backup.timer
```

**cron (alternativa simples):** veja `deploy/cron/crontab.example`.

## Regras de auditoria incluídas

| Vendor   | ID    | Verificação                                      | Severidade |
|----------|-------|---------------------------------------------------|------------|
| MikroTik | MK-01 | Telnet desabilitado                               | Alta       |
| MikroTik | MK-02 | FTP desabilitado                                  | Média      |
| MikroTik | MK-03 | Cliente NTP habilitado                            | Média      |
| MikroTik | MK-04 | SNMP sem community "public"                       | Alta       |
| MikroTik | MK-05 | Logging remoto configurado                        | Baixa      |
| MikroTik | MK-06 | API service não exposto sem restrição             | Média      |
| Huawei   | HW-01 | Telnet desabilitado (usar STelnet/SSH)            | Alta       |
| Huawei   | HW-02 | NTP configurado                                   | Média      |
| Huawei   | HW-03 | SNMP sem community "public"/"private"             | Alta       |
| Huawei   | HW-04 | Info-center (logging) habilitado                  | Baixa      |
| Huawei   | HW-05 | ACL aplicada nas VTY                               | Média      |

Novas regras podem ser adicionadas em `src/mkhw_toolkit/audit.py` (listas
`MIKROTIK_RULES` / `HUAWEI_RULES`), sem tocar no resto do código.

## Roadmap

- [ ] Suporte a backup via API nativa (librouteros / Huawei NETCONF), sem depender de SSH
- [ ] Exportar relatório de auditoria em HTML/PDF
- [ ] Suporte a outros vendors (Cisco, Juniper)
- [ ] Testes automatizados com mocks de dispositivo (sem hardware real)

## Licença

MIT — veja [LICENSE](LICENSE).
