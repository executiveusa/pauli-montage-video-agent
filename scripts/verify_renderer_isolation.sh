#!/bin/sh
# Run INSIDE the renderer container to prove its boundary:
#   docker compose exec animator-renderer sh /app/scripts/verify_renderer_isolation.sh
# (copy the script in with `docker cp` if it is not baked into the image). Exit 0 = all checks pass.
fail=0
check() { if [ "$2" = "ok" ]; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
# 1. no secret-looking environment
if env | grep -Ei 'secret|token|password|passwd|api_key|database|postgres|redis|signing|aws_|supabase' >/dev/null; then check "environment has no secrets" no; else check "environment has no secrets" ok; fi
# 2. no user-data mounts
if grep -E ' /(data|app/output|var/lib/docker)' /proc/mounts >/dev/null; then check "no data volumes mounted" no; else check "no data volumes mounted" ok; fi
# 3. root filesystem is read-only
if touch /app/.w 2>/dev/null; then rm -f /app/.w; check "root filesystem read-only" no; else check "root filesystem read-only" ok; fi
# 4. work dir is writable (tmpfs)
touch /work/.w 2>/dev/null && rm -f /work/.w && check "work dir writable" ok || check "work dir writable" no
# 5. no egress
python3 - <<'PY' || exit 1
import socket, sys
for host, port in (("1.1.1.1", 443), ("8.8.8.8", 53)):
    s = socket.socket(); s.settimeout(3)
    try:
        s.connect((host, port)); print("FAIL no egress: reached", host); sys.exit(3)
    except OSError:
        pass
print("PASS no egress")
PY
[ $? -eq 0 ] || fail=1
# 6. not root, no capabilities
[ "$(id -u)" != "0" ] && check "runs as non-root" ok || check "runs as non-root" no
grep -q '^CapEff:\s*0000000000000000' /proc/self/status && check "no effective capabilities" ok || check "no effective capabilities" no
exit $fail
