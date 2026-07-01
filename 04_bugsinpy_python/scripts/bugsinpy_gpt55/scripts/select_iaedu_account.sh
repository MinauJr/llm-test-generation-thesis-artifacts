#!/usr/bin/env bash
set -Eeuo pipefail
set +H 2>/dev/null || true

ACCOUNT_DIR="/home/jpaiva/projetos/_iaedu_accounts_clean/current/gpt55"

if [[ -z "${IAEDU_SECRETS_FILE:-}" ]]; then
    echo "[ACCOUNT_ERROR] IAEDU_SECRETS_FILE não foi definido." >&2
    exit 70
fi

case "$IAEDU_SECRETS_FILE" in
    "$ACCOUNT_DIR/account1.env")
        IAEDU_ACCOUNT_LABEL="account1"
        ;;
    "$ACCOUNT_DIR/account2.env")
        IAEDU_ACCOUNT_LABEL="account2"
        ;;
    "$ACCOUNT_DIR/account3.env")
        IAEDU_ACCOUNT_LABEL="account3"
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

if [[ "$(stat -c '%a' "$IAEDU_SECRETS_FILE")" != "600" ]]; then
    echo "[ACCOUNT_ERROR] O ficheiro da conta não tem permissões 600." >&2
    exit 73
fi

export IAEDU_SECRETS_FILE
export IAEDU_ACCOUNT_LABEL

echo \
    "[ACCOUNT_SELECTED] label=$IAEDU_ACCOUNT_LABEL file=$IAEDU_SECRETS_FILE" \
    >&2
