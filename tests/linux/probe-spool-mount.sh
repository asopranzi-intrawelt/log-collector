#!/usr/bin/env bash
# Run as root inside a private mount namespace, with the repository path as $1.
set -euo pipefail

source_root=${1:?pass the Linux path to the repository}
if [[ $(id -u) -ne 0 ]]; then
    echo 'root_required' >&2
    exit 1
fi
if [[ $(readlink /proc/self/ns/mnt) == "$(readlink /proc/1/ns/mnt)" ]]; then
    echo 'private_mount_namespace_required' >&2
    exit 1
fi
if [[ ! -f "$source_root/pilot/monitoring-hub/replay-outbox.py" ]]; then
    echo 'source_missing' >&2
    exit 1
fi

work=$(mktemp -d /tmp/log-collector-spool.XXXXXXXX)
case "$work" in
    /tmp/log-collector-spool.*) ;;
    *) echo 'unsafe_temporary_path' >&2; exit 1 ;;
esac
pilot="$work/project/pilot/monitoring-hub"
fixture_root="$pilot/fixtures"
backing="$work/backing"

cleanup() {
    mountpoint -q "$fixture_root/replay-outbox" && umount "$fixture_root/replay-outbox"
    mountpoint -q "$fixture_root/replay-original" && umount "$fixture_root/replay-original"
    mountpoint -q "$backing" && umount "$backing"
    rm -rf -- "$work"
}
trap cleanup EXIT

mkdir -p "$work/project/bin" "$fixture_root/replay-outbox" \
    "$fixture_root/replay-original" "$backing"
cp "$source_root/bin/pilot_consultation_v0.py" "$work/project/bin/"
for name in replay-outbox.py emit-fixture.py check-logs.py; do
    cp "$source_root/pilot/monitoring-hub/$name" "$pilot/"
done

if python3 "$pilot/replay-outbox.py" status >"$work/no-mount.out" 2>"$work/no-mount.err"; then
    echo 'missing_mount_was_accepted' >&2
    exit 1
fi
grep -q 'Mount dedicato' "$work/no-mount.err"
test ! -e "$fixture_root/replay-outbox/.lock"
echo 'missing_mount=rejected_before_write'

mount -t tmpfs -o size=16m,mode=0700 tmpfs "$backing"
mkdir "$backing/outbox" "$backing/originals"
mount --bind "$backing/outbox" "$fixture_root/replay-outbox"
mount --bind "$backing/originals" "$fixture_root/replay-original"

python3 "$pilot/replay-outbox.py" status >"$work/initial.json"
python3 - "$work/initial.json" <<'PY'
import json
import sys

result = json.load(open(sys.argv[1], encoding="utf-8"))
assert result["bounded_mount_verified"] is True
assert result["segments"] == 0
assert 0 < result["filesystem_bytes_available"] <= 16 * 1024 * 1024
PY
echo 'bounded_mount=verified_16mib'

event_id=$(python3 "$pilot/replay-outbox.py" emit)
segment=$(find "$fixture_root/replay-outbox" -maxdepth 1 -name 'technical-*.jsonl' -print -quit)
original="$fixture_root/replay-original/$event_id.log"
test -f "$segment"
test -f "$original"
sha256sum "$segment" "$original" >"$work/first.sha256"
python3 "$pilot/replay-outbox.py" status >"$work/one.json"
python3 - "$work/one.json" <<'PY'
import json
import sys

result = json.load(open(sys.argv[1], encoding="utf-8"))
assert result["segments"] == 1
assert result["logical_bytes"] > 0
assert result["warning_reasons"] == []
PY
echo 'first_record=written_on_bounded_mount'

python3 - "$backing" <<'PY'
import os
from pathlib import Path
import sys

backing = Path(sys.argv[1])
total = os.statvfs(backing).f_blocks * os.statvfs(backing).f_frsize
with (backing / "padding.bin").open("wb", buffering=0) as output:
    while True:
        free = os.statvfs(backing).f_bavail * os.statvfs(backing).f_frsize
        if free <= total // 10:
            break
        output.write(b"x" * min(65536, free - total // 10))
PY
if python3 "$pilot/replay-outbox.py" status >"$work/warning.json"; then
    echo 'low_space_warning_missing' >&2
    exit 1
else
    code=$?
    test "$code" -eq 2
fi
python3 - "$work/warning.json" <<'PY'
import json
import sys

result = json.load(open(sys.argv[1], encoding="utf-8"))
assert "filesystem_bytes_available_20_percent" in result["warning_reasons"]
PY
echo 'low_space=status_exit_2'

python3 - "$backing" <<'PY'
import os
from pathlib import Path
import sys

backing = Path(sys.argv[1])
with (backing / "padding.bin").open("ab", buffering=0) as output:
    while os.statvfs(backing).f_bavail > 1:
        output.write(b"x" * 4096)
assert os.statvfs(backing).f_bavail == 1
PY
if python3 "$pilot/replay-outbox.py" emit >"$work/full.out" 2>"$work/full.err"; then
    echo 'enospc_was_accepted' >&2
    exit 1
fi
grep -q 'No space left on device' "$work/full.err"
test ! -e "$fixture_root/replay-outbox/.lock"
test "$(find "$fixture_root/replay-outbox" -maxdepth 1 -name 'technical-*.jsonl' | wc -l)" -eq 1
sha256sum -c "$work/first.sha256" >/dev/null
echo 'enospc=failed_closed_previous_record_unchanged'

python3 - "$backing" <<'PY'
import os
from pathlib import Path
import sys

backing = Path(sys.argv[1])
with (backing / "padding.bin").open("ab", buffering=0) as output:
    while os.statvfs(backing).f_bavail:
        output.write(b"x" * 4096)
PY
if python3 "$pilot/replay-outbox.py" status >"$work/no-blocks.out" 2>"$work/no-blocks.err"; then
    echo 'zero_free_blocks_was_accepted' >&2
    exit 1
fi
if ! grep -q 'No space left on device' "$work/no-blocks.err"; then
    tail -n 4 "$work/no-blocks.err" >&2
    exit 1
fi
if [[ -e "$fixture_root/replay-outbox/.lock" ]]; then
    echo 'residual_lock_after_enospc' >&2
    exit 1
fi
echo 'zero_free_blocks=no_residual_lock'
