#!/bin/bash
# Скрипт для запуска бэктеста в контейнере
# Использование: ./run_backtest.sh [symbol] [strategy] [balance]

SYMBOL=${1:-BTCUSDT}
STRATEGY=${2:-MACDX}
BALANCE=${3:-1000}

echo "🚀 Запуск бэктеста для $SYMBOL стратегии $STRATEGY с балансом $BALANCE"

# Запуск в podman контейнере
# --security-opt label=disable: отключает SELinux для контейнера (решает проблему pasta/udmabuf)
# --userns=keep-id: маппинг UID хоста → тот же UID внутри контейнера (права на файлы)
# --env-file .env: передаёт API ключи в контейнер для загрузки данных с биржи
ENV_FILE_OPT=""
if [ -f .env ]; then
    ENV_FILE_OPT="--env-file .env"
fi

podman run --rm \
    --userns=keep-id \
    --security-opt label=disable \
    $ENV_FILE_OPT \
    -v .:/app \
    -w /app \
    python:3.12-slim sh -c "
pip install -q requests pandas matplotlib &&
python -m scripts.run_backtest --symbol $SYMBOL --strategy $STRATEGY --balance $BALANCE
"
