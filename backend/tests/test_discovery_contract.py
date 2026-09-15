import inspect
import unittest
from datetime import datetime, timedelta

from app import app
from components.discovery import service


class DiscoveryContractTests(unittest.TestCase):
    def test_discovery_route_is_registered(self):
        route_methods = {
            (route.path, method)
            for route in app.routes
            for method in (getattr(route, "methods", None) or set())
        }
        self.assertIn(("/discovery/v1/spaces", "GET"), route_methods)

    def test_algorithm_does_not_import_paid_or_legacy_rank_models(self):
        imported_names = set(service.__dict__)
        forbidden_models = {
            "GiftDefinition",
            "SupportLedgerEntry",
            "CosmeticEntitlement",
            "CreatorSupportProfile",
            "Room",
        }
        self.assertTrue(forbidden_models.isdisjoint(imported_names))

        score_source = inspect.getsource(service._score_space).casefold()
        for token in ("gift_code", "wallet", "currency", "payment", "price"):
            self.assertNotIn(token, score_source)

    def test_score_is_internal_and_projection_is_explainable(self):
        now = datetime(2026, 9, 15, 12, 0, 0)
        space = {
            "uid": "00000000-0000-0000-0000-000000000001",
            "name": "Разговоры вечером",
            "purpose": "conversation",
            "tags": ["Кино", "Музыка"],
            "member_count": 12,
            "viewer_membership": None,
            "created_at": now.isoformat(),
        }
        score, reasons = service._score_space(
            space,
            recent_contributors=4,
            upcoming={"starts_at": now + timedelta(hours=4)},
            viewer_purposes={"conversation"},
            viewer_tags={"кино"},
            social_intent="open",
            now=now,
        )
        self.assertGreater(score, 0)
        codes = {item["code"] for item in reasons}
        self.assertIn("active_conversation", codes)
        self.assertIn("upcoming_activity", codes)
        self.assertLessEqual(len(reasons), 3)

    def test_quiet_intent_does_not_create_behavioral_match(self):
        now = datetime(2026, 9, 15, 12, 0, 0)
        space = {
            "uid": "00000000-0000-0000-0000-000000000002",
            "name": "Спокойный чат",
            "purpose": "conversation",
            "tags": [],
            "member_count": 0,
            "viewer_membership": None,
            "created_at": (now - timedelta(days=30)).isoformat(),
        }
        _, reasons = service._score_space(
            space,
            recent_contributors=0,
            upcoming=None,
            viewer_purposes=set(),
            viewer_tags=set(),
            social_intent="quiet",
            now=now,
        )
        self.assertNotIn("intent_match", {item["code"] for item in reasons})

    def test_recent_activity_uses_distinct_authors_not_message_volume(self):
        source = inspect.getsource(service._recent_contributor_counts)
        self.assertIn("func.distinct(Message.author_uid)", source)
        self.assertNotIn("func.count(Message.uid)", source)

    def test_private_pending_context_is_not_used_for_live_signals(self):
        source = inspect.getsource(service.discover_spaces)
        self.assertIn('space.get("visibility") == "public"', source)
        self.assertIn('membership.get("status") == "active"', source)
        self.assertIn("recent_contributors = recent_by_room.get(room_uid, 0) if can_see_live_context else 0", source)
        self.assertIn("upcoming = upcoming_by_room.get(room_uid) if can_see_live_context else None", source)

    def test_diversity_breaks_three_similar_results_when_close(self):
        ranked = [
            {"space": {"uid": "1", "purpose": "games"}, "_score": 30},
            {"space": {"uid": "2", "purpose": "games"}, "_score": 29},
            {"space": {"uid": "3", "purpose": "games"}, "_score": 28},
            {"space": {"uid": "4", "purpose": "conversation"}, "_score": 27},
        ]
        result = service._diversify(ranked)
        self.assertEqual(result[2]["space"]["purpose"], "conversation")

    def test_candidate_pool_is_bounded(self):
        self.assertGreaterEqual(service.DISCOVERY_POOL_LIMIT, 50)
        self.assertLessEqual(service.DISCOVERY_POOL_LIMIT, 500)


if __name__ == "__main__":
    unittest.main()
