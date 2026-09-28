import argparse
import asyncio
import json
from uuid import UUID

from components.discovery.profiling import profile_discovery
from components.model_registry import ensure_models_registered
from database import Database


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Profile one privacy-safe organic discovery request.",
    )
    parser.add_argument("--viewer-uid", required=True)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--query")
    parser.add_argument("--purpose")
    parser.add_argument("--tag")
    parser.add_argument("--max-statements", type=int)
    parser.add_argument("--max-wall-ms", type=float)
    return parser


async def run(args: argparse.Namespace) -> int:
    ensure_models_registered()
    viewer_uid = UUID(str(args.viewer_uid))
    try:
        async with Database.sessionmaker()() as db:
            _items, profile = await profile_discovery(
                db,
                viewer_uid,
                query=args.query,
                purpose=args.purpose,
                tag=args.tag,
                limit=max(1, min(100, args.limit)),
                offset=max(0, args.offset),
            )
        payload = profile.as_dict()
        payload["algorithm"] = "organic-v2"
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))

        if (
            args.max_statements is not None
            and profile.statement_count > max(1, args.max_statements)
        ):
            return 2
        if (
            args.max_wall_ms is not None
            and profile.wall_elapsed_ms > max(1.0, args.max_wall_ms)
        ):
            return 3
        return 0
    finally:
        await Database.dispose()


def main() -> int:
    return asyncio.run(run(build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
