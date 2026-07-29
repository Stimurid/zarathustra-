# TINKUY — DEPLOYMENT RUNBOOK

**Живёт на `tinkuy.mindkampf.ru`. Прод-инстанс `v0.4.x`.**

Этот документ должен быть достаточен для чистой сессии (Codex / Claude / Kimi / любой другой агент), чтобы обновить, отладить или расширить деплой без пере-открытия окружения.

---

## 1. Сервер

| Что | Значение |
|---|---|
| VM | `81.26.176.248` (hostname `moderbober-prod-01`, Ubuntu 22.04+) |
| SSH user | `deploy` (ключ `~/.ssh/id_ed25519`, sudo без пароля) |
| Пример команды | `ssh deploy@81.26.176.248` |
| DNS | `tinkuy.mindkampf.ru → 81.26.176.248` (A-запись уже настроена) |
| Соседи в `/opt/` | `dedalum, kairoskopion, litops, mindfield, moderbober, paideia, quinta, whitecrow, tinkuy` |

## 2. Раскладка на сервере

```
/opt/tinkuy/                       — root, owner tinkuy:tinkuy
├── app/                           — распакованный проект (CALIFORNIAN_ID + runtime_assets + docs)
│   ├── .venv/                     — Python venv (python 3.12)
│   ├── CALIFORNIAN_ID/            — Python package (editable install)
│   ├── runtime_assets/            — persona layer v0.2 (8 personas + registry + retrieval)
│   ├── docs/                      — persona layer docs
│   └── README.md
├── (более ничего)

/etc/tinkuy/                       — root:tinkuy
└── tinkuy.env                     — env-переменные (chmod 600, provider + api keys)

/srv/tinkuy/                       — tinkuy:tinkuy (writable для сервиса)
└── runs/                          — trace-выходы прогонов

/etc/systemd/system/tinkuy-web.service   — systemd unit (root:root, chmod 644)

/opt/moderbober/Caddyfile                — общий Caddy config (root)
```

## 3. Systemd unit (`/etc/systemd/system/tinkuy-web.service`)

Ключевое (полный файл в `CALIFORNIAN_ID/deploy/tinkuy.service` в репе):

```
User=tinkuy
Group=tinkuy
WorkingDirectory=/opt/tinkuy/app/CALIFORNIAN_ID
EnvironmentFile=/etc/tinkuy/tinkuy.env
Environment=PYTHONPATH=/opt/tinkuy/app/CALIFORNIAN_ID/src
Environment=CALIFORNIAN_ID_DATA_DIR=/opt/tinkuy/app/CALIFORNIAN_ID/src/californian_id/data
Environment=CALIFORNIAN_ID_RUNS_DIR=/srv/tinkuy/runs
Environment=PERSONA_LAYER_ROOT=/opt/tinkuy/app/runtime_assets/personas/v0.2
ExecStart=/opt/tinkuy/app/.venv/bin/python -m californian_id web-ui \
    --host 0.0.0.0 \
    --port 8085
Restart=on-failure
```

**Внимание:** `--host 0.0.0.0` обязательно (не 127.0.0.1) — иначе Caddy из docker-контейнера не достучится через bridge (172.17.0.1).

Управление:
```bash
sudo systemctl status tinkuy-web
sudo systemctl restart tinkuy-web
sudo journalctl -u tinkuy-web -n 100 --no-pager
```

## 4. Firewall (UFW)

Правило открыто для docker bridge Caddy → host:

```bash
sudo ufw allow proto tcp from 172.18.0.0/16 to any port 8085 comment "tinkuy: caddy->host"
```

Правила соседей смотреть: `sudo ufw status numbered`.

## 5. Caddy (reverse proxy)

Caddy живёт в контейнере `moderbober-caddy` (docker-compose в `/opt/moderbober/docker-compose.yml`).
Конфиг — `/opt/moderbober/Caddyfile`, монтируется в контейнер read-only.
`host.docker.internal` работает через `extra_hosts: ["host.docker.internal:host-gateway"]`.

**Блок для tinkuy** (`/opt/moderbober/Caddyfile`):

```caddy
tinkuy.mindkampf.ru {
    request_body {
        max_size 25MB
    }

    reverse_proxy host.docker.internal:8085 {
        transport http {
            read_timeout 300s
            write_timeout 300s
            dial_timeout 10s
        }
    }
}
```

Reload после правки:
```bash
sudo docker exec moderbober-caddy caddy validate --config /etc/caddy/Caddyfile
sudo docker exec moderbober-caddy caddy reload --config /etc/caddy/Caddyfile
```

## 6. Обновление кода (регулярный workflow)

С локальной машины (`C:\projects\zarathustra-push` или где лежит свежий репо):

```bash
# 1. tarball из репо (свежий v0.4.x)
cd C:\projects\zarathustra-push
tar --exclude='.git' --exclude='__pycache__' --exclude='.pytest_cache' \
    --exclude='CALIFORNIAN_ID/runs' --exclude='runs' \
    --exclude='CALIFORNIAN_ID/src/californian_id/data/corpus/zarathustra/normalized/*.txt' \
    --exclude='runtime_assets/personas/v0.2/retrieval/build' \
    --exclude='_tmp_remote_patch.py' --exclude='zarathustra_ui_20260728.tar.gz' \
    --exclude='.venv' \
    -czf /tmp/tinkuy-deploy.tar.gz \
    CALIFORNIAN_ID runtime_assets docs README.md

# 2. scp
scp /tmp/tinkuy-deploy.tar.gz deploy@81.26.176.248:/tmp/

# 3. install (идемпотентно — обновляет код + перезапускает сервис)
ssh deploy@81.26.176.248 "sudo INSTANCE=tinkuy PORT=8085 DOMAIN=tinkuy.mindkampf.ru bash /opt/tinkuy/app/CALIFORNIAN_ID/deploy/install_on_vm.sh"
```

Скрипт `install_on_vm.sh` — идемпотентный: сохраняет `.venv/` (не переустанавливает pip-пакеты кроме editable), сохраняет `/etc/tinkuy/tinkuy.env` (не перезаписывает), рестартит `tinkuy-web`, делает health-check на `http://127.0.0.1:8085/`.

## 7. LLM провайдер

### Дефолт (v0.4.4+): 302.ai с fallback chain

**Основной провайдер — 302.ai (агрегатор с claude-sonnet-4.5, gpt-4o, gemini-1.5-pro, deepseek).**
Fallback-цепочка при ошибке или недоступности primary модели:
1. 302.ai + claude-sonnet-4-5 (primary)
2. 302.ai + gpt-4o
3. 302.ai + gemini-1.5-pro
4. 302.ai + deepseek-chat

Ключ:
```
/etc/tinkuy/tinkuy.env:
CALIFORNIAN_ID_PROVIDER=302ai
API_302AI_KEY=sk-...     # (не коммитить, chmod 600)
```

Смена ключа/провайдера:
```bash
ssh deploy@81.26.176.248
sudo nano /etc/tinkuy/tinkuy.env
sudo systemctl restart tinkuy-web
```

### Возможные значения `CALIFORNIAN_ID_PROVIDER`:
- `mock` — offline, шаблонные ответы. Для тестов.
- `302ai` — 302.ai агрегатор (дефолт). Требует `API_302AI_KEY`.
- `anthropic` — прямой Anthropic. Требует `ANTHROPIC_API_KEY`.
- `openai` — прямой OpenAI. Требует `OPENAI_API_KEY`.

### Дополнительные ключи (для fallback-цепочки):
- `ANTHROPIC_API_KEY` — если 302.ai временно недоступен, тогда fallback падает сюда
- `OPENAI_API_KEY` — то же
Если этих ключей нет в env, соответствующие ступени fallback просто пропускаются.

## 8. basic_auth (закрыть публичный доступ)

По умолчанию сейчас без auth (после снятия невалидного хеша от Codex).

Чтобы включить:

```bash
ssh deploy@81.26.176.248
# 1. сгенерировать bcrypt
sudo docker exec moderbober-caddy caddy hash-password --plaintext 'ВАШПАРОЛЬ'
# выведет: $2a$14$....

# 2. добавить блок в /opt/moderbober/Caddyfile ВНУТРИ tinkuy.mindkampf.ru {}
sudo nano /opt/moderbober/Caddyfile
# сразу после `tinkuy.mindkampf.ru {`:
#     basic_auth {
#         timur $2a$14$....
#     }

# 3. reload
sudo docker exec moderbober-caddy caddy validate --config /etc/caddy/Caddyfile
sudo docker exec moderbober-caddy caddy reload --config /etc/caddy/Caddyfile
```

## 9. Проверка живости

```bash
# из вне
curl -sk -o /dev/null -w '%{http_code}\n' https://tinkuy.mindkampf.ru/         # ожидание 200 (или 401 если basic_auth)

# API smoke (Python, чтобы utf-8 отправка была правильной)
python -c "
import urllib.request, json, ssl
body = json.dumps({'text':'Стоит ли ускорять развитие AGI?', 'mode':'fast'}, ensure_ascii=False).encode('utf-8')
req = urllib.request.Request('https://tinkuy.mindkampf.ru/api/run',
    data=body, headers={'Content-Type':'application/json; charset=utf-8'}, method='POST')
r = urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=90)
print(json.loads(r.read().decode('utf-8'))['completion']['form'])
"

# внутри сервера
ssh deploy@81.26.176.248 "curl -s http://127.0.0.1:8085/ | head -c 200"

# соседи не сломаны:
for h in dedalum paideia litops kairoskop mindfield whitecrow; do
    curl -sk -o /dev/null -w "$h: %{http_code}\n" https://$h.mindkampf.ru/
done
```

## 10. Troubleshooting

| Симптом | Диагноз |
|---|---|
| `HTTP 502` от Caddy | смотри `sudo docker logs moderbober-caddy --tail 50`. Скорее всего reverse_proxy dial timeout — проверь `sudo ss -tlnp \| grep 8085` (должно быть `0.0.0.0:8085`, не `127.0.0.1:8085`) и `sudo ufw status \| grep 8085` |
| `HTTP 503` / долгий ответ | LLM провайдер тормозит; проверь `/etc/tinkuy/tinkuy.env` — правильный ключ? упал ли fallback? `sudo journalctl -u tinkuy-web -n 50` |
| Сервис не стартует | `sudo systemctl status tinkuy-web`, `sudo journalctl -u tinkuy-web -n 100 --no-pager`. Часто — сломан .env, отсутствует пакет в venv, или порт занят |
| `curl` из терминала выдаёт `utf-8 codec can't decode byte 0xd1` | Известное: Windows Git-Bash отправляет cp1251. Тестируй через `python -c "urllib.request..."` (см. §9) |
| Изменения в код-репе не подхватываются | скрипт `install_on_vm.sh` использует `pip install -e .` — editable, так что достаточно обновить файлы и `systemctl restart tinkuy-web`. Если trouble — `pip install --force-reinstall -e /opt/tinkuy/app/CALIFORNIAN_ID` |

## 11. Артефакты в репозитории

- `CALIFORNIAN_ID/deploy/tinkuy.service` — эталонный systemd unit
- `CALIFORNIAN_ID/deploy/tinkuy.env.template` — эталонный env-файл (без ключей)
- `CALIFORNIAN_ID/deploy/caddy_snippet.txt` — эталонный Caddy-блок
- `CALIFORNIAN_ID/deploy/install_on_vm.sh` — идемпотентный установщик
- `CALIFORNIAN_ID/_work/DEPLOYMENT_RUNBOOK.md` — **этот файл** (актуальное состояние прода)
- `CALIFORNIAN_ID/_work/BACKLOG.md` — что осталось из TODO

## 12. История критических инцидентов (для будущих сессий)

- **2026-07-29:** Первый деплой. Три пункта отладки:
  1. Caddy отверг конфиг: невалидный bcrypt-хеш в basic_auth (плейсхолдер от Codex). Убрал блок — auth сейчас OFF.
  2. HTTP 502: сервис слушал на 127.0.0.1:8085 — Caddy из docker bridge не достучался. Сменил на 0.0.0.0.
  3. HTTP 502 после fix: UFW блокировал 8085. Добавил rule для 172.18.0.0/16 (по образцу соседей).
- **2026-07-29 (v0.4.2 → v0.4.3):** Removed persona-layer заточка (ROUTING_KEYWORDS, FULL_COUNCIL_KEYWORDS, NEMO8_TRIGGER_KEYWORDS Python constants) → перенесено в data (`registry/routing_policy.yaml`, per-persona `manifest.yaml::routing.topics.{en,ru}`). Bilingual (EN+RU) matching.

## 13. Важные принципы (не нарушать)

1. **Ключи никогда не в git.** Только в `/etc/tinkuy/tinkuy.env` (chmod 600).
2. **Секреты не логировать.** `_send_json` замазывает; не добавлять новые endpoints без sanitization.
3. **Не менять порт 8085 без апдейта UFW + Caddyfile + systemd unit одновременно.**
4. **Не удалять `.venv/`** во время обновления (это в `install_on_vm.sh` уже учтено).
5. **Соседи не трогать.** dedalum/paideia/litops — отдельные проекты. При любых правках Caddyfile/UFW — не задевать их правила.
6. **Заточку не восстанавливать.** Русский текст должен работать наравне с английским (см. v0.4.2 CHANGELOG).
