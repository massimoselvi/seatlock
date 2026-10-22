#!/usr/bin/env bash
# Starts Structurizr on this workspace, renders every view to diagrams/*.svg, and stops it.
#
#   docs/architecture/export.sh
#
# Needs Docker, Node 22 and pnpm. Set CHROME_PATH to a Chrome or Chromium executable, or install
# Playwright's browser once with: (cd docs/architecture/tools && pnpm exec playwright-core install chromium)
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
port="${PORT:-8089}"
name="seatlock-c4-export"
image="structurizr/structurizr:2026.09.19"

cleanup() { docker rm -f "$name" > /dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup

docker run -d --name "$name" -p "$port:8080" -v "$here":/usr/local/structurizr "$image" local > /dev/null

for _ in $(seq 1 60); do
  if [ "$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:$port/workspace/1/diagrams")" = 200 ]; then
    break
  fi
  sleep 1
done

cd "$here/tools"
pnpm install --frozen-lockfile > /dev/null
STRUCTURIZR_URL="http://localhost:$port/workspace/1/diagrams" pnpm run --silent export "$here/diagrams"
