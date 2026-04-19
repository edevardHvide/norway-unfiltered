#!/usr/bin/env bash
# Install SSB companion skills from TRY (ssb-api, ssb-dataviz) into ~/.claude/skills/
set -euo pipefail

BASE_URL="https://tools.try.no/ssb-mcp"
DEST="${HOME}/.claude/skills"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

install_skill() {
  local name="$1"
  local zip_url="${BASE_URL}/${name}-skill.zip"
  echo "Downloading ${name}..."
  curl -sfL -o "${TMP}/${name}.zip" "${zip_url}"
  mkdir -p "${TMP}/${name}"
  unzip -q -o "${TMP}/${name}.zip" -d "${TMP}/${name}"
  mkdir -p "${DEST}/${name}"
  cp -R "${TMP}/${name}/." "${DEST}/${name}/"
  echo "Installed ${name} -> ${DEST}/${name}"
}

install_skill "ssb-api"
install_skill "ssb-dataviz"

echo
echo "Done. Skills available at:"
echo "  ${DEST}/ssb-api/SKILL.md"
echo "  ${DEST}/ssb-dataviz/SKILL.md"
