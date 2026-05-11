#!/usr/bin/env bash
#
# DisSysLab one-line installer for Pat.
#
# Usage:
#     curl -sSf https://raw.githubusercontent.com/kmchandy/DisSysLab/main/install.sh | bash
#
# Or download and run locally:
#     bash install.sh
#
# Flags:
#     --no-modify-rc   Don't touch your shell rc; print the export
#                      lines and let you copy them yourself.
#
# What it does, in order:
#   1. Check Python 3.10+ is on PATH.
#   2. Install Ollama (homebrew on Mac, official installer on Linux).
#   3. Start the Ollama service if it isn't running.
#   4. Pull qwen3:30b (the recommended local model, ~19 GB one-time).
#   5. Create a Python venv at ~/.dissyslab/venv.
#   6. pip install dissyslab into it.
#   7. Append PATH + DSL_BACKEND to your shell rc (~/.zshrc or
#      ~/.bashrc, depending on $SHELL). A backup is written next to
#      the rc file before any edit. Pass --no-modify-rc to skip.
#
# What it does NOT do:
#   - Configure paid LLM backends. Default is free local Qwen via
#     Ollama. To use Claude or another paid model later, see
#     docs/LANGUAGE_MODELS.md.
#
# Tested on: macOS (Apple Silicon and Intel) and Ubuntu 22.04+.
# Probably works on other Linuxes; ymmv.
#

set -euo pipefail

# ── Parse flags ──────────────────────────────────────────────────────

MODIFY_RC=1
for arg in "$@"; do
    case "$arg" in
        --no-modify-rc) MODIFY_RC=0 ;;
        *) ;;
    esac
done

# ── Cosmetic helpers ─────────────────────────────────────────────────

bold()   { printf '\033[1m%s\033[0m\n'    "$*"; }
green()  { printf '\033[32m✓ %s\033[0m\n' "$*"; }
yellow() { printf '\033[33m! %s\033[0m\n' "$*"; }
red()    { printf '\033[31m✗ %s\033[0m\n' "$*"; }
header() { echo; bold "── $* ─────────────────────────"; }

die() {
    red "$*"
    echo
    echo "Installation aborted. Open an issue at"
    echo "  https://github.com/kmchandy/DisSysLab/issues"
    echo "with the message above and your OS details."
    exit 1
}

# ── 0. Banner ────────────────────────────────────────────────────────

bold "DisSysLab installer"
echo "Free AI assistants that do your information work — on your laptop."
echo

# ── 1. Detect OS ─────────────────────────────────────────────────────

header "Step 1/7: Detect OS"

OS="$(uname -s)"
case "$OS" in
    Darwin) PLATFORM="mac";   green "Detected macOS";;
    Linux)  PLATFORM="linux"; green "Detected Linux";;
    *)      die "Unsupported OS: $OS. We currently support macOS and Linux. Windows users: please install manually via the docs.";;
esac

# ── 2. Check Python 3.10+ ────────────────────────────────────────────

header "Step 2/7: Check Python 3.10+"

if ! command -v python3 >/dev/null 2>&1; then
    die "python3 not found. Install Python 3.10 or newer from https://www.python.org/downloads/ then re-run this installer."
fi

PYV="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PYMAJ="${PYV%%.*}"
PYMIN="${PYV##*.}"
if [ "$PYMAJ" -lt 3 ] || { [ "$PYMAJ" -eq 3 ] && [ "$PYMIN" -lt 10 ]; }; then
    die "Found Python $PYV but DisSysLab needs Python 3.10+. Upgrade Python from https://www.python.org/downloads/ then re-run."
fi
green "Python $PYV is fine"

# ── 3. Install Ollama ────────────────────────────────────────────────

header "Step 3/7: Install Ollama (free local AI runtime)"

if command -v ollama >/dev/null 2>&1; then
    green "Ollama is already installed"
else
    if [ "$PLATFORM" = "mac" ]; then
        if ! command -v brew >/dev/null 2>&1; then
            die "Homebrew is not installed. The simplest install path on Mac is:
  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"
Run that, then re-run this installer. (Or install Ollama manually from https://ollama.com/download.)"
        fi
        bold "Installing Ollama via homebrew..."
        brew install ollama
    else
        bold "Installing Ollama via the official Linux installer..."
        curl -fsSL https://ollama.com/install.sh | sh
    fi
    green "Ollama installed"
fi

# ── 4. Start Ollama service ──────────────────────────────────────────

header "Step 4/7: Verify Ollama is running"

if ! curl -sSf -o /dev/null http://127.0.0.1:11434/api/version 2>/dev/null; then
    yellow "Ollama service is not running. Starting it..."
    if [ "$PLATFORM" = "mac" ]; then
        # On Mac, the brew-installed ollama runs as a foreground command.
        # Start it in the background; user can launch the app manually
        # for persistence after this install.
        ollama serve >/tmp/ollama.log 2>&1 &
        sleep 2
    else
        # On Linux the official installer registers a systemd unit.
        if command -v systemctl >/dev/null 2>&1; then
            sudo systemctl start ollama || true
            sleep 2
        else
            ollama serve >/tmp/ollama.log 2>&1 &
            sleep 2
        fi
    fi
fi

if curl -sSf -o /dev/null http://127.0.0.1:11434/api/version 2>/dev/null; then
    green "Ollama is responding on port 11434"
else
    die "Ollama service did not start. Try running 'ollama serve' in another terminal and re-run this installer."
fi

# ── 5. Pull the recommended model ────────────────────────────────────

header "Step 5/7: Pull Qwen3:30b model"

if ollama list 2>/dev/null | grep -q '^qwen3:30b'; then
    green "qwen3:30b is already downloaded"
else
    yellow "Downloading qwen3:30b — about 19 GB, takes 20–40 minutes on a typical home connection."
    yellow "This is a one-time cost. Pat gets free AI forever after this."
    echo
    ollama pull qwen3:30b
    green "qwen3:30b downloaded"
fi

# ── 6. Install DisSysLab ─────────────────────────────────────────────

header "Step 6/7: Install DisSysLab into a venv"

DSL_HOME="${DSL_HOME:-$HOME/.dissyslab}"
mkdir -p "$DSL_HOME"

if [ ! -d "$DSL_HOME/venv" ]; then
    python3 -m venv "$DSL_HOME/venv"
fi

"$DSL_HOME/venv/bin/pip" install --upgrade pip >/dev/null
"$DSL_HOME/venv/bin/pip" install --upgrade dissyslab

green "DisSysLab installed at $DSL_HOME/venv"

# ── 7. Update shell config ──────────────────────────────────────────

header "Step 7/7: Update your shell config"

# Detect the right rc file from $SHELL. Mac users mostly run zsh
# (Apple's default since macOS 10.15); Linux users mostly run bash.
# We deliberately do NOT fall through to .profile or .bash_profile
# without confirmation — those interact with login-shell semantics
# in ways that are easy to break.
RC_FILE=""
case "${SHELL:-}" in
    */zsh)  RC_FILE="$HOME/.zshrc" ;;
    */bash)
        if [ "$PLATFORM" = "mac" ] && [ -f "$HOME/.bash_profile" ]; then
            RC_FILE="$HOME/.bash_profile"
        else
            RC_FILE="$HOME/.bashrc"
        fi
        ;;
    */fish) RC_FILE="$HOME/.config/fish/config.fish" ;;
    *) RC_FILE="" ;;
esac

# Marker the installer uses to recognise its own block on re-runs.
MARKER="# Added by DisSysLab installer"

print_export_lines() {
    bold "       export PATH=\"$DSL_HOME/venv/bin:\$PATH\""
    bold "       export DSL_BACKEND=ollama"
}

print_manual_instructions() {
    echo
    yellow "Add this to your shell config and restart your terminal:"
    echo
    print_export_lines
    echo
}

if [ "$MODIFY_RC" -eq 0 ]; then
    yellow "Skipping shell config update (--no-modify-rc)."
    print_manual_instructions
elif [ -z "$RC_FILE" ]; then
    yellow "Couldn't detect your shell from \$SHELL=${SHELL:-(unset)}."
    print_manual_instructions
elif [ -f "$RC_FILE" ] && grep -qF "$MARKER" "$RC_FILE"; then
    green "Shell config already has DisSysLab lines — skipping ($RC_FILE)"
elif [ "${RC_FILE##*/}" = "config.fish" ]; then
    # fish uses a different export syntax; surface manual instructions
    # rather than guess.
    yellow "Detected fish shell — please add this to $RC_FILE:"
    echo
    bold "       set -gx PATH $DSL_HOME/venv/bin \$PATH"
    bold "       set -gx DSL_BACKEND ollama"
    echo
else
    # Back up first so a paranoid Pat can compare.
    if [ -f "$RC_FILE" ]; then
        cp "$RC_FILE" "$RC_FILE.dissyslab-backup"
        yellow "Backed up $RC_FILE to $RC_FILE.dissyslab-backup"
    fi
    {
        echo ""
        echo "$MARKER"
        echo "export PATH=\"$DSL_HOME/venv/bin:\$PATH\""
        echo "export DSL_BACKEND=ollama"
    } >> "$RC_FILE"
    green "Appended PATH + DSL_BACKEND to $RC_FILE"
fi

# ── Done ─────────────────────────────────────────────────────────────

header "All set"

# A tiny banner emphasising the one step Pat is most likely to miss.
# The PATH change in ~/.zshrc does NOT apply to the terminal that
# just ran install.sh — only to terminals opened (or re-sourced)
# afterwards. Pat tends to try `dsl run` immediately and bounce on
# "command not found", so we shout this step.

if [ "$MODIFY_RC" -eq 1 ] && [ -n "${RC_FILE:-}" ] && \
   [ -f "$RC_FILE" ] && grep -qF "$MARKER" "$RC_FILE"; then
    echo
    yellow "──────────────────────────────────────────────────────────────"
    yellow "  ONE MORE STEP — pick either (A) or (B):"
    yellow ""
    yellow "  (A) Run this in THIS terminal:"
    bold   "        source $RC_FILE"
    yellow ""
    yellow "  (B) Or close this terminal and open a brand new one."
    yellow ""
    yellow "  Why: install.sh added PATH to $RC_FILE, but this"
    yellow "  terminal won't see it until you do (A) or (B)."
    yellow "──────────────────────────────────────────────────────────────"
    echo
fi

echo "Then try your first office:"
echo
bold "       dsl run dissyslab/gallery/apps/periodic_brief/"
echo
echo "Read the situation_room walkthrough to see what an office is and"
echo "how to make one your own:"
bold "       https://github.com/kmchandy/DisSysLab/blob/main/dissyslab/gallery/apps/situation_room/README.md"
echo
echo "Welcome to free AI."
echo
