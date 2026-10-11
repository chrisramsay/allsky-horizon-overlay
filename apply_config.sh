#!/usr/bin/env bash
# Apply allsky-patch.jq to the live indi-allsky config, with backup,
# preview, restart and an image-circle check.
#
#   ./apply_config.sh            preview + apply + restart + check
#   ./apply_config.sh --dry-run  preview only
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
PATCH="$REPO/config/allsky-patch.jq"
CHECK="$REPO/find_circle.py"
OUTDIR=~/allsky-config
WAIT=60                                   # seconds to wait for fresh frames
IMAGE=/var/www/html/allsky/images/latest.jpg

cd ~/indi-allsky
[ -f virtualenv/indi-allsky/bin/activate ] && source virtualenv/indi-allsky/bin/activate

umask 077                                 # dumps contain secrets: owner-only files
mkdir -p "$OUTDIR"
TS=$(date +%Y%m%d-%H%M%S)
BACKUP="$OUTDIR/config-$TS-before.json"
NEW="$OUTDIR/config-$TS-after.json"

echo "1. Downloading current config -> $BACKUP"
./config.py dump > "$BACKUP" 2>/dev/null

echo "2. Applying $PATCH"
jq -f "$PATCH" "$BACKUP" > "$NEW"

echo "   Changes:"
if diff <(jq -S . "$BACKUP") <(jq -S . "$NEW"); then
    echo "   (none - config already matches the patch)"
    exit 0
fi

[ "${1:-}" = "--dry-run" ] && { echo "Dry run - nothing applied."; exit 0; }
read -rp "Apply these changes? [y/N] " ok
[ "$ok" = "y" ] || { echo "Cancelled."; exit 0; }

echo "3. Uploading new config"
./config.py load -c "$NEW" --force

echo "4. Restarting indi-allsky"
systemctl --user restart indi-allsky

echo "5. Waiting ${WAIT}s for new frames, then checking the image circle"
sleep "$WAIT"
python3 "$CHECK" "$IMAGE"

echo
echo "To undo:  cd ~/indi-allsky && ./config.py load -c $BACKUP --force && systemctl --user restart indi-allsky"
echo "     or:  ./config.py list   then   ./config.py revert -i <previous id>"
