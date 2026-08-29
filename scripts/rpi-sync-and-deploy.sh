#!/usr/bin/env bash
set -euo pipefail

# RPi backup/deploy helper for the split FCB1010 repositories.
#
# Default folder layout:
#   /home/pi/fcbdata
#   /home/pi/fcbapi
#   /home/pi/fcbcontroller
#   /home/pi/fcb-maintenance-ui-distr
#
# Optional overrides:
#   HOME_DIR=/home/pi
#   DATA_DIR=/home/pi/fcbdata
#   API_DIR=/home/pi/fcbapi
#   CONTROLLER_DIR=/home/pi/fcbcontroller
#   UI_DIST_DIR=/home/pi/fcb-maintenance-ui-distr
#   WEB_ROOT=/var/www/html
#   WEB_OWNER=www-data:www-data
#   RESTART_SERVICES=1
#   API_SERVICE=fcbapi
#   CONTROLLER_SERVICE=fcbcontroller

HOME_DIR="${HOME_DIR:-$HOME}"
DATA_DIR="${DATA_DIR:-$HOME_DIR/fcbdata}"
API_DIR="${API_DIR:-$HOME_DIR/fcbapi}"
CONTROLLER_DIR="${CONTROLLER_DIR:-$HOME_DIR/fcbcontroller}"
UI_DIST_DIR="${UI_DIST_DIR:-$HOME_DIR/fcb-maintenance-ui-distr}"
WEB_ROOT="${WEB_ROOT:-/var/www/html}"
WEB_OWNER="${WEB_OWNER:-www-data:www-data}"
RESTART_SERVICES="${RESTART_SERVICES:-0}"
API_SERVICE="${API_SERVICE:-fcbapi}"
CONTROLLER_SERVICE="${CONTROLLER_SERVICE:-fcbcontroller}"

log() {
  printf '\n==> %s\n' "$1"
}

die() {
  printf '\nERROR: %s\n' "$1" >&2
  exit 1
}

require_git_repo() {
  local dir="$1"
  [ -d "$dir/.git" ] || die "$dir is not a git repository"
}

current_branch() {
  git rev-parse --abbrev-ref HEAD
}

ensure_clean_worktree() {
  local dir="$1"
  local name="$2"

  require_git_repo "$dir"
  (
    cd "$dir"
    if [ -n "$(git status --porcelain)" ]; then
      git status --short
      die "$name has local changes. Commit/stash them before pulling."
    fi
  )
}

backup_data_repo() {
  require_git_repo "$DATA_DIR"

  log "Backing up fcbdata"
  (
    cd "$DATA_DIR"
    local branch
    branch="$(current_branch)"
    git add -A

    if [ -n "$(git status --porcelain)" ]; then
      local stamp
      stamp="$(date '+%Y-%m-%d %H:%M:%S')"
      git commit -m "Backup RPi data $stamp"
    else
      echo "No fcbdata changes to commit."
    fi

    git pull --rebase origin "$branch"
    git push origin "$branch"
  )
}

pull_clean_repo() {
  local dir="$1"
  local name="$2"

  ensure_clean_worktree "$dir" "$name"
  log "Updating $name"
  (
    cd "$dir"
    local branch
    branch="$(current_branch)"
    git fetch origin "$branch"
    git pull --ff-only origin "$branch"
  )
}

resolve_ui_dist_dir() {
  if [ -d "$UI_DIST_DIR/.git" ]; then
    printf '%s\n' "$UI_DIST_DIR"
    return
  fi

  local fallback="$HOME_DIR/fcb-maintenance-ui-dist"
  if [ -d "$fallback/.git" ]; then
    printf '%s\n' "$fallback"
    return
  fi

  die "UI dist repo not found at $UI_DIST_DIR or $fallback"
}

publish_ui() {
  local dist_dir="$1"

  [ -f "$dist_dir/index.html" ] || die "$dist_dir does not look like a built UI dist folder; index.html is missing"

  case "$WEB_ROOT" in
    /var/www/html|/var/www/html/) ;;
    *) die "Refusing to publish to unexpected WEB_ROOT: $WEB_ROOT" ;;
  esac

  log "Publishing UI to $WEB_ROOT"
  sudo mkdir -p "$WEB_ROOT"

  if command -v rsync >/dev/null 2>&1; then
    sudo rsync -a --delete --exclude '.git' "$dist_dir"/ "$WEB_ROOT"/
  else
    sudo find "$WEB_ROOT" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
    (
      cd "$dist_dir"
      sudo cp -a . "$WEB_ROOT"/
    )
    sudo rm -rf "$WEB_ROOT/.git"
  fi

  if getent passwd "${WEB_OWNER%%:*}" >/dev/null 2>&1; then
    sudo chown -R "$WEB_OWNER" "$WEB_ROOT"
  else
    echo "Skipping chown; user ${WEB_OWNER%%:*} does not exist."
  fi
}

restart_services_if_requested() {
  if [ "$RESTART_SERVICES" != "1" ]; then
    echo "Service restart skipped. Use RESTART_SERVICES=1 to restart services."
    return
  fi

  log "Restarting services"
  sudo systemctl restart "$API_SERVICE"
  sudo systemctl restart "$CONTROLLER_SERVICE"
  sudo systemctl --no-pager --full status "$API_SERVICE" "$CONTROLLER_SERVICE"
}

main() {
  backup_data_repo
  pull_clean_repo "$API_DIR" "fcbapi"
  pull_clean_repo "$CONTROLLER_DIR" "fcbcontroller"

  local resolved_ui_dist_dir
  resolved_ui_dist_dir="$(resolve_ui_dist_dir)"
  pull_clean_repo "$resolved_ui_dist_dir" "fcb-maintenance-ui-dist"
  publish_ui "$resolved_ui_dist_dir"
  restart_services_if_requested

  log "Done"
}

main "$@"
