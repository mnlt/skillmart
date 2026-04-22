#!/usr/bin/env bash
# teleport-setup installer
# Usage:  curl -sL https://raw.githubusercontent.com/mnlt/teleport/main/setup/install.sh | bash

set -e

VENV="${TELEPORT_VENV:-$HOME/.teleport-venv}"
BIN_DIR="${TELEPORT_BIN_DIR:-$HOME/.local/bin}"

echo "▸ searching for a working python3 with functional venv + ensurepip"
PY=""
for candidate in python3.12 python3.11 python3.13 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -m venv --help >/dev/null 2>&1 && "$candidate" -c "import ensurepip" 2>/dev/null; then
      # Actually try creating a throwaway venv to catch python3.14-style breakage
      tmp_test=$(mktemp -d)
      if "$candidate" -m venv "$tmp_test/test" >/dev/null 2>&1; then
        PY="$candidate"
        rm -rf "$tmp_test"
        break
      fi
      rm -rf "$tmp_test"
    fi
  fi
done

if [ -z "$PY" ]; then
  echo "error: no working python3 with venv found. Tried: python3.12, python3.11, python3.13, python3.10, python3."
  echo "       on macOS: brew install python@3.12"
  exit 1
fi
echo "  using $PY ($(${PY} --version))"

echo "▸ creating isolated venv at $VENV"
"$PY" -m venv "$VENV"

echo "▸ installing teleport-setup from github.com/mnlt/teleport"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet "git+https://github.com/mnlt/teleport.git#subdirectory=setup"

mkdir -p "$BIN_DIR"
ln -sf "$VENV/bin/teleport-setup" "$BIN_DIR/teleport-setup"

SKILL_DIR="$HOME/.claude/skills/teleport"
echo "▸ installing meta-skill to $SKILL_DIR"
mkdir -p "$SKILL_DIR"
if command -v curl >/dev/null 2>&1; then
  curl -fsSL https://raw.githubusercontent.com/mnlt/teleport/main/meta-skill/SKILL.md -o "$SKILL_DIR/SKILL.md"
else
  echo "  warning: curl not found, skipping meta-skill install"
  echo "  download manually: https://raw.githubusercontent.com/mnlt/teleport/main/meta-skill/SKILL.md"
fi

echo ""
echo "✓ teleport-setup installed"
echo "  CLI:        $BIN_DIR/teleport-setup"
echo "  meta-skill: $SKILL_DIR/SKILL.md"
echo ""

if ! echo ":$PATH:" | grep -q ":$BIN_DIR:"; then
  echo "⚠  $BIN_DIR is not on your PATH. Add this to ~/.zshrc or ~/.bashrc:"
  echo ""
  echo "     export PATH=\"\$HOME/.local/bin:\$PATH\""
  echo ""
  echo "  then restart the shell, or run: export PATH=\"\$HOME/.local/bin:\$PATH\""
  echo ""
fi

echo "run:  teleport-setup"
echo ""
echo "uninstall later:  rm -rf $VENV $BIN_DIR/teleport-setup"

# Anonymous install counter (no PII, no IP stored).
# Opt out: TELEPORT_NO_TELEMETRY=1
if [ "${TELEPORT_NO_TELEMETRY:-}" != "1" ]; then
  curl -sL -o /dev/null -m 3 -A "teleport-setup/0.7.1" "https://teleport.goatcounter.com/count?p=/install-completed&t=0.7.1" 2>/dev/null || true
fi
