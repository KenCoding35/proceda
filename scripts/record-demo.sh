#!/usr/bin/env bash
# Record a terminal demo of proceda running the toy-greeting example.
# Requires: asciinema (install via `uvx asciinema`), ANTHROPIC_API_KEY set.
#
# Usage:
#   ./scripts/record-demo.sh
#
# Output: demo.cast in repo root (upload to asciinema.org or convert to GIF/SVG)

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "Error: ANTHROPIC_API_KEY is not set"
    exit 1
fi

echo "Recording demo... Run 'proceda run ./examples/toy-greeting' in the shell."
echo "Approve when prompted, then exit with Ctrl-D when done."
echo ""

uvx asciinema rec demo.cast \
    --title "Proceda: SOP → Agent in seconds" \
    --idle-time-limit 3 \
    --command "uv run proceda run ./examples/toy-greeting --config examples/toy-greeting/proceda.yaml"
