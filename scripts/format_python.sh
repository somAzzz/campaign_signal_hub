#!/usr/bin/env bash
set -euo pipefail

uv run --extra dev --extra data ruff check backend scripts --fix
uv run --extra dev --extra data ruff format backend scripts
