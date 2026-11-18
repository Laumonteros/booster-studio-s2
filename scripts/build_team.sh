#!/usr/bin/env bash
set -euo pipefail

if [[ $# != 2 ]]; then
  echo "Usage: $0 RUNNING_AGENT_DEV_CONTAINER OUTPUT_AGENT_PATH" >&2
  exit 2
fi
container=$1
output=$2
repo=$(cd "$(dirname "$0")/.." && pwd)
output_dir=$(dirname "$output")
if [[ ! -d "$output_dir" ]]; then
  echo "Output parent must already exist: $output_dir" >&2
  exit 2
fi
if [[ -e "$output" ]]; then
  echo "Refusing to overwrite package: $output" >&2
  exit 2
fi
docker inspect "$container" >/dev/null
sign_dir=$(mktemp -d "$output_dir/team-signing.XXXXXX")
build_dir="/workspace/laumonteros-build-$(date +%s)"
keystore="/tmp/$(basename "$sign_dir").p12"
cleanup() {
  docker exec -u root "$container" rm -f "$keystore" >/dev/null 2>&1 || true
  rm -f "$sign_dir/local.key" "$sign_dir/local.crt" "$sign_dir/local.p12"
  rmdir "$sign_dir"
}
trap cleanup EXIT
export LOCAL_SIGNING_PASSWORD
LOCAL_SIGNING_PASSWORD=$(openssl rand -hex 24)
openssl req -x509 -newkey rsa:2048 -nodes -keyout "$sign_dir/local.key" \
  -out "$sign_dir/local.crt" -subj '/CN=Local Team Testing Only' -days 30 2>/dev/null
openssl pkcs12 -export -inkey "$sign_dir/local.key" -in "$sign_dir/local.crt" \
  -out "$sign_dir/local.p12" -passout env:LOCAL_SIGNING_PASSWORD
chmod 600 "$sign_dir/local.p12"
docker exec -u root "$container" mkdir -p "$build_dir"
docker cp "$repo/team/." "$container:$build_dir"
docker cp "$sign_dir/local.p12" "$container:$keystore"
docker exec -u root "$container" chown -R dev:dev "$build_dir" "$keystore"
docker exec -e "AGENT_SIGN_KEYSTORE=$keystore" \
  -e "AGENT_SIGN_KEYSTORE_PASSWD=$LOCAL_SIGNING_PASSWORD" "$container" \
  /sdk/agent_bundler/build_pyagent "$build_dir"
docker cp "$container:$build_dir/build/laumonteros_team_v1-1.0.0.agent" "$output"
echo "Built local-only signed package: $output"
