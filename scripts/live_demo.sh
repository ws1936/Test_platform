#!/usr/bin/env bash
# Live demo: start uvicorn, hit every endpoint, then stop.
set -e
cd /Users/gws_files/Downloads/ai_project

PORT=8765
LOG=/tmp/uvicorn_demo.log
rm -f $LOG
export DATABASE_URL="sqlite+aiosqlite:///$(mktemp -d)/live_demo.db"
export ENVIRONMENT=test

echo "=== 1) starting uvicorn on :$PORT (background) ==="
uv run uvicorn app.main:app --host 127.0.0.1 --port $PORT > $LOG 2>&1 &
PID=$!
echo "    uvicorn pid=$PID, log=$LOG"

# Wait for startup
for i in 1 2 3 4 5 6 7 8; do
  if curl -s -o /dev/null http://127.0.0.1:$PORT/health; then
    echo "    uvicorn is up (after ${i}s)"
    break
  fi
  sleep 1
done

# === health ===
echo
echo "=== 2) GET /health ==="
curl -s -w "\nHTTP %{http_code}\n" http://127.0.0.1:$PORT/health

# === project paths in OpenAPI ===
echo
echo "=== 3) /openapi.json — /projects paths ==="
curl -s http://127.0.0.1:$PORT/openapi.json | uv run python -c "
import sys, json
spec = json.load(sys.stdin)
for p in sorted(spec['paths']):
    if '/projects' in p:
        for m, info in spec['paths'][p].items():
            print(f'  {m.upper():6s} {p:32s}  {info.get(\"summary\", \"\")!r}')
"

# === unique username ===
USERNAME="live_$(date +%s)"

# === register ===
echo
echo "=== 4) POST /api/v1/auth/register (user=$USERNAME) ==="
REG=$(curl -s -X POST http://127.0.0.1:$PORT/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USERNAME\",\"email\":\"$USERNAME@example.com\",\"password\":\"DemoPass123!\",\"nickname\":\"Live\",\"phone\":\"13800000000\"}")
echo "$REG" | uv run python -m json.tool
TOKEN=$(echo "$REG" | uv run python -c "import sys, json; print(json.load(sys.stdin)['token']['access_token'])")
echo
echo "    access_token (first 60): ${TOKEN:0:60}..."

# === create project ===
echo
echo "=== 5) POST /api/v1/projects (create) ==="
CREATE=$(curl -s -X POST http://127.0.0.1:$PORT/api/v1/projects \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Real Live Demo","description":"Created via real curl"}')
echo "$CREATE" | uv run python -m json.tool
PID2=$(echo "$CREATE" | uv run python -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo
echo "    project_id=$PID2"

# === list ===
echo
echo "=== 6) GET /api/v1/projects (list) ==="
curl -s http://127.0.0.1:$PORT/api/v1/projects \
  -H "Authorization: Bearer $TOKEN" | uv run python -m json.tool

# === detail ===
echo
echo "=== 7) GET /api/v1/projects/{id} (detail) ==="
curl -s -w "\nHTTP %{http_code}\n" http://127.0.0.1:$PORT/api/v1/projects/$PID2 \
  -H "Authorization: Bearer $TOKEN" | uv run python -c "
import sys
raw = sys.stdin.read()
body, _, status = raw.rpartition('HTTP ')
import json
try:
    print(json.dumps(json.loads(body.strip()), indent=2))
except Exception:
    print(body)
print('HTTP' + status.strip() if status else '')
"

# === update ===
echo
echo "=== 8) PUT /api/v1/projects/{id} (update) ==="
curl -s -X PUT http://127.0.0.1:$PORT/api/v1/projects/$PID2 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"description":"Updated via curl"}' | uv run python -m json.tool

# === errors ===
echo
echo "=== 9) POST /api/v1/projects (missing name → expect 422) ==="
curl -s -o /tmp/err422.json -w "HTTP %{http_code}\n" -X POST http://127.0.0.1:$PORT/api/v1/projects \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"description":"no name"}'
cat /tmp/err422.json | uv run python -m json.tool

echo
echo "=== 10) GET /api/v1/projects (no token → expect 401) ==="
curl -s -o /tmp/err401.json -w "HTTP %{http_code}\n" http://127.0.0.1:$PORT/api/v1/projects
cat /tmp/err401.json
echo

# === delete ===
echo
echo "=== 11) DELETE /api/v1/projects/{id} ==="
curl -s -o /tmp/del.json -w "HTTP %{http_code}\n" -X DELETE http://127.0.0.1:$PORT/api/v1/projects/$PID2 \
  -H "Authorization: Bearer $TOKEN"
cat /tmp/del.json
echo

# === verify deletion ===
echo
echo "=== 12) GET deleted project (expect 404) ==="
curl -s -o /tmp/get404.json -w "HTTP %{http_code}\n" http://127.0.0.1:$PORT/api/v1/projects/$PID2 \
  -H "Authorization: Bearer $TOKEN"
cat /tmp/get404.json
echo

# === shutdown ===
echo
echo "=== 13) shutdown uvicorn ==="
kill $PID 2>/dev/null
wait $PID 2>/dev/null
echo "    uvicorn stopped"

echo
echo "=== ALL OK ==="