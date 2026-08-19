#!/usr/bin/env bash
# G-S27 LIVE execution: 8 source-ready scenarios against production Socrates
set -uo pipefail
DIR=/tmp/gs27_live
rm -rf $DIR
mkdir -p $DIR
E=http://127.0.0.1:8085/api/socrates/run

post() {
  local name="$1"; local payload="$2"
  curl -sS --max-time 180 -o $DIR/$name.json \
    -w "http=%{http_code} $name bytes=" \
    -H "Content-Type: application/json" -X POST "$E" -d "$payload"
  wc -c < $DIR/$name.json
}

# Queries extracted from PRIMARY_10_TWIN_SCREEN corpus.
# S03 (NORM_APPLICABILITY) and S04 (VOID_CONTRACT) source-blocked per manifest.

echo "=== S01 COST_REDUCTION ==="
post S01_socrates '{"text":"Почему локализация производства снизила себестоимость?","execution_mode":"LIVE"}'

echo "=== S02 LOCALIZATION_MODELS ==="
post S02_socrates '{"text":"Сравни две модели локализации","execution_mode":"LIVE"}'

echo "=== S05 SAME_INDICATOR ==="
post S05_socrates '{"text":"Возьми тот же показатель, что в прошлой главе, и посчитай за этот год","execution_mode":"LIVE"}'

echo "=== S06 AUTHOR_PROBLEM ==="
post S06_socrates '{"text":"Восстанови, какую проблему решал автор этой статьи","execution_mode":"LIVE"}'

echo "=== S07 EXTRACT_CONCEPTS ==="
post S07_socrates '{"text":"Выдели концепты из этого текста","execution_mode":"LIVE"}'

echo "=== S08 INTELLIGENCE_SECTION ==="
post S08_socrates '{"text":"Напиши раздел про интеллект этой системы","execution_mode":"LIVE"}'

echo "=== S09 AS_WE_AGREED ==="
post S09_socrates '{"text":"Как мы договорились, считаем по сценарию полной локализации — продолжай","execution_mode":"LIVE"}'

echo "=== S10 TOPIC_CHOICE ==="
post S10_socrates '{"text":"Какую тему брать для курсовой — локализацию или регулирование платформ?","execution_mode":"LIVE"}'

echo "===DONE==="
ls -la $DIR | grep -v total | wc -l
