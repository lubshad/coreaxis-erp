#!/bin/bash

set -euo pipefail

APP_NAME="${APP_NAME:-coreaxis}"
SERVER_HOST="${SERVER_HOST:-erp.coreaxissolutions.in}"
SERVER_USER="${SERVER_USER:-frappe}"
SERVER_PORT="${SERVER_PORT:-22}"
BENCH_DIR="${BENCH_DIR:-/home/frappe/frappe-bench}"
SITE="${SITE:-erp.coreaxissolutions.in}"
SKIP_MIGRATE=0
SKIP_RESTART=0
DRY_RUN=0

LOCAL_APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BENCH_ROOT="$(cd "$LOCAL_APP_DIR/../.." && pwd)"
SSH_KEY="${SSH_KEY:-$BENCH_ROOT/personal}"
REMOTE_APP_DIR="${REMOTE_APP_DIR:-$BENCH_DIR/apps/$APP_NAME}"

usage() {
	cat <<EOF
Usage: apps/coreaxis/sync.sh [options]

Deploy the CoreAxis Frappe app to the production bench.

Options:
  --server-host HOST   Remote server host. Default: $SERVER_HOST
  --server-user USER   Remote SSH user. Default: $SERVER_USER
  --server-port PORT   Remote SSH port. Default: $SERVER_PORT
  --ssh-key PATH       SSH private key. Default: $SSH_KEY
  --bench-dir PATH     Remote bench directory. Default: $BENCH_DIR
  --site SITE          Frappe site name. Default: $SITE
  --dry-run            Validate and show rsync changes without changing server files
  --skip-migrate       Skip bench migrate after syncing
  --skip-restart       Skip bench restart after syncing
  -h, --help           Show this help message

Environment overrides:
  APP_NAME, SERVER_HOST, SERVER_USER, SERVER_PORT, SSH_KEY, BENCH_DIR, SITE, REMOTE_APP_DIR
EOF
}

require_command() {
	local command_name="$1"
	if ! command -v "$command_name" >/dev/null 2>&1; then
		echo "Required command not found: $command_name" >&2
		exit 1
	fi
}

require_path() {
	local path_value="$1"
	local label="$2"
	if [ ! -e "$path_value" ]; then
		echo "$label not found: $path_value" >&2
		exit 1
	fi
}

resolve_path() {
	local path_value="$1"

	if [[ "$path_value" = /* ]]; then
		echo "$path_value"
		return
	fi

	if [ -e "$PWD/$path_value" ]; then
		printf '%s/%s\n' "$(cd "$(dirname "$PWD/$path_value")" && pwd)" "$(basename "$path_value")"
		return
	fi

	if [ -e "$BENCH_ROOT/$path_value" ]; then
		printf '%s/%s\n' "$(cd "$(dirname "$BENCH_ROOT/$path_value")" && pwd)" "$(basename "$path_value")"
		return
	fi

	if [ -e "$LOCAL_APP_DIR/$path_value" ]; then
		printf '%s/%s\n' "$(cd "$(dirname "$LOCAL_APP_DIR/$path_value")" && pwd)" "$(basename "$path_value")"
		return
	fi

	echo "$path_value"
}

while [ "$#" -gt 0 ]; do
	case "$1" in
		--server-host)
			SERVER_HOST="$2"
			shift 2
			;;
		--server-user)
			SERVER_USER="$2"
			shift 2
			;;
		--server-port)
			SERVER_PORT="$2"
			shift 2
			;;
		--ssh-key)
			SSH_KEY="$2"
			shift 2
			;;
		--bench-dir)
			BENCH_DIR="$2"
			REMOTE_APP_DIR="${REMOTE_APP_DIR:-$BENCH_DIR/apps/$APP_NAME}"
			shift 2
			;;
		--site)
			SITE="$2"
			shift 2
			;;
		--dry-run)
			DRY_RUN=1
			shift
			;;
		--skip-migrate)
			SKIP_MIGRATE=1
			shift
			;;
		--skip-restart)
			SKIP_RESTART=1
			shift
			;;
		-h|--help)
			usage
			exit 0
			;;
		*)
			echo "Unknown option: $1" >&2
			usage >&2
			exit 1
			;;
	esac
done

SSH_KEY="$(resolve_path "$SSH_KEY")"
SERVER="$SERVER_USER@$SERVER_HOST"
REMOTE_APP_DIR="${REMOTE_APP_DIR:-$BENCH_DIR/apps/$APP_NAME}"
SSH_OPTIONS=(-i "$SSH_KEY" -p "$SERVER_PORT" -o BatchMode=yes -o ConnectTimeout=15)
RSYNC_RSH="ssh -i $SSH_KEY -p $SERVER_PORT -o BatchMode=yes -o ConnectTimeout=15"

echo "Validating local setup..."
require_command rsync
require_command ssh
require_path "$SSH_KEY" "SSH identity file"
require_path "$LOCAL_APP_DIR" "Local app directory"
require_path "$LOCAL_APP_DIR/pyproject.toml" "App pyproject.toml"

echo "App:        $APP_NAME"
echo "Server:     $SERVER"
echo "Site:       $SITE"
echo "Bench:      $BENCH_DIR"
echo "Remote app: $REMOTE_APP_DIR"
echo "SSH key:    $SSH_KEY"

if [ "$DRY_RUN" -eq 1 ]; then
	echo "Dry run enabled. No remote files or bench state will be changed."
	echo "Checking remote bench directory..."
	ssh "${SSH_OPTIONS[@]}" "$SERVER" "test -d '$BENCH_DIR'"

	echo "Previewing rsync changes..."
	rsync -avzn --delete \
		--exclude '.git' \
		--exclude '__pycache__' \
		--exclude '*.pyc' \
		--exclude '.DS_Store' \
		--exclude '.pytest_cache' \
		--exclude '.ruff_cache' \
		--exclude '*.egg-info' \
		--exclude 'node_modules' \
		-e "$RSYNC_RSH" \
		"$LOCAL_APP_DIR/" "$SERVER:$REMOTE_APP_DIR/"

	cat <<EOF
Dry run completed. A real deploy would run these remote steps:
  cd "$BENCH_DIR"
  "$BENCH_DIR/env/bin/pip" install -e "apps/$APP_NAME"
  bench --site "$SITE" install-app "$APP_NAME"  # only if not already installed
  bench --site "$SITE" migrate
  bench restart
EOF
	exit 0
fi

echo "Ensuring remote app directory exists..."
ssh "${SSH_OPTIONS[@]}" "$SERVER" <<EOF
set -euo pipefail

if [ ! -d "$BENCH_DIR" ]; then
	echo "Bench directory not found: $BENCH_DIR" >&2
	exit 1
fi

mkdir -p "$REMOTE_APP_DIR"
EOF

echo "Syncing $APP_NAME to $SERVER:$REMOTE_APP_DIR ..."
rsync -avz --delete \
	--exclude '.git' \
	--exclude '__pycache__' \
	--exclude '*.pyc' \
	--exclude '.DS_Store' \
	--exclude '.pytest_cache' \
	--exclude '.ruff_cache' \
	--exclude '*.egg-info' \
	--exclude 'node_modules' \
	-e "$RSYNC_RSH" \
	"$LOCAL_APP_DIR/" "$SERVER:$REMOTE_APP_DIR/"

echo "Running remote deployment steps..."
ssh "${SSH_OPTIONS[@]}" "$SERVER" <<EOF
set -euo pipefail

if [ ! -d "$BENCH_DIR" ]; then
	echo "Bench directory not found: $BENCH_DIR" >&2
	exit 1
fi

if [ ! -d "$REMOTE_APP_DIR" ]; then
	echo "Remote app directory not found: $REMOTE_APP_DIR" >&2
	exit 1
fi

cd "$BENCH_DIR"
"$BENCH_DIR/env/bin/pip" install -e "apps/$APP_NAME"

if ! bench --site "$SITE" list-apps | awk '{print \$1}' | grep -Fxq "$APP_NAME"; then
	bench --site "$SITE" install-app "$APP_NAME"
fi

if [ "$SKIP_MIGRATE" -eq 0 ]; then
	bench --site "$SITE" migrate
else
	echo "Skipping migrate."
fi

if [ "$SKIP_RESTART" -eq 0 ]; then
	bench restart
else
	echo "Skipping restart."
fi
EOF

echo "Deployment completed successfully."
