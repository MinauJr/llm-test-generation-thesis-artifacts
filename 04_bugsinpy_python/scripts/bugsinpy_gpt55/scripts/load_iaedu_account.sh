#!/usr/bin/env bash
set -Eeuo pipefail
set +H 2>/dev/null || true

ACCOUNT_DIR="/home/jpaiva/projetos/_iaedu_accounts_clean/current/gpt55"

if [[ -z "${IAEDU_SECRETS_FILE:-}" ]]; then
    echo "[ACCOUNT_ERROR] IAEDU_SECRETS_FILE não foi definido." >&2
    exit 70
fi

case "$IAEDU_SECRETS_FILE" in
    "$ACCOUNT_DIR/account1.env"|\
    "$ACCOUNT_DIR/account2.env"|\
    "$ACCOUNT_DIR/account3.env")
        ;;
    *)
        echo "[ACCOUNT_ERROR] Ficheiro de conta não autorizado." >&2
        exit 71
        ;;
esac

if [[ ! -f "$IAEDU_SECRETS_FILE" ]]; then
    echo "[ACCOUNT_ERROR] Ficheiro de conta inexistente." >&2
    exit 72
fi

PERMS="$(stat -c '%a' "$IAEDU_SECRETS_FILE" 2>/dev/null || true)"

if [[ "$PERMS" != "600" ]]; then
    echo "[ACCOUNT_ERROR] Permissões esperadas=600 encontradas=$PERMS" >&2
    exit 73
fi

# Impede a herança silenciosa de outra conta.
unset IAEDU_ENDPOINT
unset IAEDU_CHANNEL_ID
unset IAEDU_API_KEY

set -a
# shellcheck disable=SC1090
source "$IAEDU_SECRETS_FILE"
set +a

for REQUIRED_NAME in \
    IAEDU_ENDPOINT \
    IAEDU_CHANNEL_ID \
    IAEDU_API_KEY
do
    if [[ -z "${!REQUIRED_NAME:-}" ]]; then
        echo "[ACCOUNT_ERROR] Variável obrigatória vazia: $REQUIRED_NAME" >&2
        exit 74
    fi
done

IAEDU_ACCOUNT_LABEL="$(basename "$IAEDU_SECRETS_FILE" .env)"

export IAEDU_ACCOUNT_LABEL
export IAEDU_SECRETS_FILE
export IAEDU_ENDPOINT
export IAEDU_CHANNEL_ID
export IAEDU_API_KEY

# Nunca mostrar endpoint, channel ou key.
echo \
    "[ACCOUNT_OK] label=$IAEDU_ACCOUNT_LABEL file=$IAEDU_SECRETS_FILE" \
    >&2
