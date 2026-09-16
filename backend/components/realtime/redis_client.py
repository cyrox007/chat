from __future__ import annotations

from dataclasses import dataclass

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.asyncio.sentinel import Sentinel

from settings import config


@dataclass
class RedisClientHandle:
    client: Redis
    mode: str
    sentinel: Sentinel | None = None

    async def aclose(self) -> None:
        try:
            await self.client.aclose(close_connection_pool=True)
        finally:
            if self.sentinel is not None:
                # redis-py Sentinel owns separate clients for Sentinel nodes.
                # Close them explicitly so tests/workers do not leak transports.
                for sentinel_client in self.sentinel.sentinels:
                    try:
                        await sentinel_client.aclose()
                    except Exception:
                        pass


def parse_sentinel_nodes(value: str) -> list[tuple[str, int]]:
    nodes: list[tuple[str, int]] = []
    for raw_node in (part.strip() for part in value.split(',')):
        if not raw_node:
            continue

        if raw_node.startswith('['):
            closing = raw_node.find(']')
            if closing <= 1 or closing + 2 >= len(raw_node) or raw_node[closing + 1] != ':':
                raise ValueError(f'Invalid Redis Sentinel node: {raw_node}')
            host = raw_node[1:closing]
            port_text = raw_node[closing + 2:]
        else:
            host, separator, port_text = raw_node.rpartition(':')
            if not separator or not host:
                raise ValueError(f'Invalid Redis Sentinel node: {raw_node}')

        try:
            port = int(port_text)
        except ValueError as exc:
            raise ValueError(f'Invalid Redis Sentinel port: {raw_node}') from exc
        if not 1 <= port <= 65535:
            raise ValueError(f'Invalid Redis Sentinel port: {raw_node}')
        nodes.append((host, port))

    if not nodes:
        raise ValueError('REDIS_SENTINEL_NODES must contain at least one host:port pair')
    return nodes


def redis_topology_mode() -> str:
    sentinel_nodes = config.REDIS_SENTINEL_NODES.strip()
    sentinel_master = config.REDIS_SENTINEL_MASTER.strip()
    if sentinel_nodes or sentinel_master:
        if not sentinel_nodes or not sentinel_master:
            raise ValueError(
                'REDIS_SENTINEL_NODES and REDIS_SENTINEL_MASTER must be configured together'
            )
        return 'sentinel'
    if config.REDIS_URL:
        return 'direct'
    return 'unconfigured'


def create_redis_client() -> RedisClientHandle:
    mode = redis_topology_mode()
    common = {
        'decode_responses': True,
        'max_connections': config.REDIS_MAX_CONNECTIONS,
        'socket_connect_timeout': config.REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS,
        'socket_timeout': config.REDIS_SOCKET_TIMEOUT_SECONDS,
        'retry_on_timeout': True,
    }

    if mode == 'direct':
        return RedisClientHandle(
            client=redis.from_url(config.REDIS_URL, **common),
            mode='direct',
        )

    if mode != 'sentinel':
        raise ValueError('Redis is not configured')

    sentinel_kwargs = {
        'socket_connect_timeout': config.REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS,
        'socket_timeout': config.REDIS_SOCKET_TIMEOUT_SECONDS,
        'decode_responses': True,
    }
    if config.REDIS_SENTINEL_USERNAME:
        sentinel_kwargs['username'] = config.REDIS_SENTINEL_USERNAME
    if config.REDIS_SENTINEL_PASSWORD:
        sentinel_kwargs['password'] = config.REDIS_SENTINEL_PASSWORD

    sentinel = Sentinel(
        parse_sentinel_nodes(config.REDIS_SENTINEL_NODES),
        min_other_sentinels=config.REDIS_SENTINEL_MIN_OTHER_SENTINELS,
        sentinel_kwargs=sentinel_kwargs,
        socket_connect_timeout=config.REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS,
        socket_timeout=config.REDIS_SOCKET_TIMEOUT_SECONDS,
    )

    master_kwargs = dict(common)
    master_kwargs['db'] = config.REDIS_DB
    if config.REDIS_USERNAME:
        master_kwargs['username'] = config.REDIS_USERNAME
    if config.REDIS_PASSWORD:
        master_kwargs['password'] = config.REDIS_PASSWORD

    client = sentinel.master_for(config.REDIS_SENTINEL_MASTER, **master_kwargs)
    return RedisClientHandle(client=client, mode='sentinel', sentinel=sentinel)
