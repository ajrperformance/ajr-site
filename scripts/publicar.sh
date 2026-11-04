#!/usr/bin/env bash
# Publica as alterações da pasta do site na branch main do GitHub.
# Uso: scripts/publicar.sh "mensagem do commit"
set -euo pipefail

REPO="github.com/ajrperformance/ajr-site.git"
TOKEN_FILE=".github-token"

# Sempre trabalha a partir da raiz do repositório
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"

erro() { echo "ERRO: $*" >&2; exit 1; }

# 1. Mensagem do commit
[ $# -ge 1 ] && [ -n "$1" ] || erro 'informe a mensagem do commit. Ex.: scripts/publicar.sh "Atualiza agenda"'
MSG="$1"

# 2. Token
[ -f "$TOKEN_FILE" ] || erro "arquivo $TOKEN_FILE não encontrado na pasta do site ($(pwd)). Crie-o com o token pessoal do GitHub."
TOKEN="$(tr -d '[:space:]' < "$TOKEN_FILE")"
[ -n "$TOKEN" ] || erro "o arquivo $TOKEN_FILE está vazio."

# 3. Só publica a partir da main
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
[ "$BRANCH" = "main" ] || erro "você está na branch '$BRANCH'. Mude para a main antes de publicar (git checkout main)."

# 4. Prepara o commit
git add -A

# 5. Trava de segurança: o token nunca pode ir para o repositório
if git diff --cached --name-only | grep -qx "$TOKEN_FILE" || git ls-files --error-unmatch "$TOKEN_FILE" >/dev/null 2>&1; then
  git reset -q -- "$TOKEN_FILE" 2>/dev/null || true
  erro "$TOKEN_FILE está no stage/versionado. Envio cancelado. Confira o .gitignore e rode: git rm --cached $TOKEN_FILE"
fi

if git diff --cached --quiet; then
  echo "Nenhuma alteração nova para commitar; só vou enviar commits pendentes (se houver)."
else
  git commit -m "$MSG"
fi

# 6. Push com o token só na linha de comando deste push:
#    - não é gravado no .git/config (não usamos 'git remote set-url');
#    - credential.helper vazio impede que o Keychain do Mac guarde o token;
#    - qualquer ocorrência do token na saída é mascarada.
echo "Enviando para a main…"
set +e
git -c credential.helper= push "https://x-access-token:${TOKEN}@${REPO}" main:main 2>&1 \
  | sed "s/${TOKEN}/***/g"
STATUS=${PIPESTATUS[0]}
set -e
unset TOKEN

if [ "$STATUS" -ne 0 ]; then
  erro "o push falhou. Se a main do GitHub tem alterações que você não tem, rode 'git pull origin main' e tente de novo."
fi

# Mantém a referência local origin/main atualizada
git update-ref refs/remotes/origin/main HEAD 2>/dev/null || true

echo "Publicado! O GitHub Pages leva cerca de 1 minuto para atualizar https://ajrperformance.com.br"
