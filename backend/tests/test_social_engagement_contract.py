import unittest

from pydantic import ValidationError

from app import app
from components.achievement.model import AccountAchievement
from components.achievement.service import SYSTEM_ACHIEVEMENT_CODES
from components.engagement.round_model import ConversationRound, ConversationRoundResponse
from components.engagement.round_schemas import (
    ConversationRoundCreateRequest,
    ConversationRoundResponseRequest,
)


class SocialEngagementContractTests(unittest.TestCase):
    def test_achievement_api_is_read_only(self):
        route_methods = {
            (route.path, method)
            for route in app.routes
            for method in (getattr(route, "methods", None) or set())
        }
        self.assertIn(("/achievements/v1/me", "GET"), route_methods)
        self.assertIn(("/achievements/v1/accounts/{account_uid}", "GET"), route_methods)
        achievement_writes = {
            item for item in route_methods
            if item[0].startswith("/achievements/v1") and item[1] in {"POST", "PUT", "PATCH", "DELETE"}
        }
        self.assertEqual(achievement_writes, set())

    def test_conversation_round_routes_are_registered(self):
        route_methods = {
            (route.path, method)
            for route in app.routes
            for method in (getattr(route, "methods", None) or set())
        }
        expected = {
            ("/activities/v1/{activity_uid}/rounds", "GET"),
            ("/activities/v1/{activity_uid}/rounds", "POST"),
            ("/activities/v1/{activity_uid}/rounds/{round_uid}", "PATCH"),
            ("/activities/v1/rounds/{round_uid}/responses", "GET"),
            ("/activities/v1/rounds/{round_uid}/response", "PUT"),
        }
        self.assertTrue(expected.issubset(route_methods))

    def test_initial_achievement_catalog_is_small_and_system_owned(self):
        self.assertEqual(
            SYSTEM_ACHIEVEMENT_CODES,
            {"first_host", "conversation_starter", "first_round_response"},
        )
        names = {constraint.name for constraint in AccountAchievement.__table__.constraints if constraint.name}
        self.assertIn("uq_account_achievement_code", names)

    def test_round_dtos_have_no_competitive_or_paid_fields(self):
        create_fields = ConversationRoundCreateRequest.model_fields
        response_fields = ConversationRoundResponseRequest.model_fields
        forbidden = {
            "score",
            "points",
            "rank",
            "winner",
            "prize",
            "stake",
            "bet",
            "currency",
            "payment",
            "reward_value",
        }
        self.assertTrue(forbidden.isdisjoint(create_fields))
        self.assertTrue(forbidden.isdisjoint(response_fields))

    def test_choice_round_requires_two_distinct_choices(self):
        payload = ConversationRoundCreateRequest(
            round_type="choice",
            prompt="Что лучше подходит для вечера?",
            option_a="Кино",
            option_b="Музыка",
        )
        self.assertEqual(payload.option_a, "Кино")
        with self.assertRaises(ValidationError):
            ConversationRoundCreateRequest(
                round_type="choice",
                prompt="Выберите",
                option_a="Кино",
            )
        with self.assertRaises(ValidationError):
            ConversationRoundCreateRequest(
                round_type="choice",
                prompt="Выберите",
                option_a="Кино",
                option_b="кино",
            )

    def test_non_choice_round_cannot_smuggle_choice_options(self):
        with self.assertRaises(ValidationError):
            ConversationRoundCreateRequest(
                round_type="icebreaker",
                prompt="Как прошла неделя?",
                option_a="Хорошо",
                option_b="Плохо",
            )

    def test_one_response_per_account_and_one_open_round_index(self):
        primary_keys = {column.name for column in ConversationRoundResponse.__table__.primary_key.columns}
        self.assertEqual(primary_keys, {"round_uid", "account_uid"})
        indexes = {index.name: index for index in ConversationRound.__table__.indexes}
        open_index = indexes["uq_conversation_rounds_one_open_per_activity"]
        self.assertTrue(open_index.unique)
        self.assertIsNotNone(open_index.dialect_options["postgresql"].get("where"))

    def test_round_fk_boundaries_are_activity_and_account_scoped(self):
        activity_targets = {
            foreign_key.target_fullname
            for foreign_key in ConversationRound.__table__.c.activity_uid.foreign_keys
        }
        account_targets = {
            foreign_key.target_fullname
            for foreign_key in ConversationRoundResponse.__table__.c.account_uid.foreign_keys
        }
        self.assertEqual(activity_targets, {"space_activities.uid"})
        self.assertEqual(account_targets, {"accounts.uid"})


if __name__ == "__main__":
    unittest.main()
