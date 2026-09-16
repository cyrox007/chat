#!/usr/bin/env bash
set -Eeuo pipefail

IMAGE="${PUBCHAT_REDIS_TEST_IMAGE:-redis:7.2-alpine}"
PREFIX="pubchat-sentinel-${GITHUB_RUN_ID:-local}-$$"
MASTER_CONTAINER="${PREFIX}-master"
REPLICA_CONTAINER="${PREFIX}-replica"
S1_CONTAINER="${PREFIX}-s1"
S2_CONTAINER="${PREFIX}-s2"
S3_CONTAINER="${PREFIX}-s3"
TMP_DIR="$(mktemp -d)"

cleanup() {
  docker rm -f \
    "$S1_CONTAINER" "$S2_CONTAINER" "$S3_CONTAINER" \
    "$REPLICA_CONTAINER" "$MASTER_CONTAINER" >/dev/null 2>&1 || true
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

wait_exec() {
  local container="$1"
  shift
  local attempt
  for attempt in $(seq 1 80); do
    if docker exec "$container" "$@" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.25
  done
  echo "Timed out waiting for $container: $*" >&2
  docker logs "$container" >&2 || true
  return 1
}

write_sentinel_config() {
  local port="$1"
  local directory="$2"
  mkdir -p "$directory"
  chmod 777 "$directory"
  cat > "$directory/sentinel.conf" <<EOF
port $port
bind 127.0.0.1
protected-mode no
daemonize no
logfile ""
sentinel monitor pubchat-master 127.0.0.1 6380 2
sentinel down-after-milliseconds pubchat-master 1000
sentinel failover-timeout pubchat-master 5000
sentinel parallel-syncs pubchat-master 1
EOF
  chmod 666 "$directory/sentinel.conf"
}

write_sentinel_config 26379 "$TMP_DIR/s1"
write_sentinel_config 26380 "$TMP_DIR/s2"
write_sentinel_config 26381 "$TMP_DIR/s3"

# All topology containers use the runner's network namespace so Sentinel can
# announce/reach stable 127.0.0.1 ports without Docker bridge address rewriting.
docker run -d --name "$MASTER_CONTAINER" --network host "$IMAGE" \
  redis-server --bind 127.0.0.1 --protected-mode no --port 6380 --save '' --appendonly no >/dev/null

docker run -d --name "$REPLICA_CONTAINER" --network host "$IMAGE" \
  redis-server --bind 127.0.0.1 --protected-mode no --port 6381 \
  --replicaof 127.0.0.1 6380 --save '' --appendonly no >/dev/null

for spec in \
  "$S1_CONTAINER:$TMP_DIR/s1:26379" \
  "$S2_CONTAINER:$TMP_DIR/s2:26380" \
  "$S3_CONTAINER:$TMP_DIR/s3:26381"
do
  IFS=: read -r container directory port <<< "$spec"
  # Mount the directory, not only the file: Sentinel persists failover state by
  # atomically rewriting/renaming its config and therefore needs directory writes.
  docker run -d --name "$container" --network host \
    -v "$directory:/data" \
    "$IMAGE" redis-server /data/sentinel.conf --sentinel >/dev/null
  wait_exec "$container" redis-cli -p "$port" ping
done

wait_exec "$MASTER_CONTAINER" redis-cli -p 6380 ping
wait_exec "$REPLICA_CONTAINER" redis-cli -p 6381 ping

# Wait until replication is actually established before killing the master.
for attempt in $(seq 1 80); do
  if docker exec "$REPLICA_CONTAINER" redis-cli -p 6381 INFO replication \
      | tr -d '\r' | grep -q '^master_link_status:up$'; then
    break
  fi
  if [[ "$attempt" == "80" ]]; then
    echo "Replica never reached master_link_status:up" >&2
    docker logs "$REPLICA_CONTAINER" >&2 || true
    exit 1
  fi
  sleep 0.25
done

PUBCHAT_REDIS_SENTINEL_INTEGRATION=1 \
PUBCHAT_SENTINEL_MASTER_CONTAINER="$MASTER_CONTAINER" \
PUBCHAT_SENTINEL_MASTER_NAME="pubchat-master" \
PUBCHAT_SENTINEL_NODES="127.0.0.1:26379,127.0.0.1:26380,127.0.0.1:26381" \
python -m unittest tests.test_redis_sentinel_failover_integration
