import asyncio
import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from pydantic import ValidationError

from app import app
from components.room.model import Room
from components.space.content_schemas import SpaceEventCreateRequest, SpaceEventUpdateRequest
from components.space.invitation_schemas import SpaceInvitationActionRequest
from components.space.membership_schemas import SpaceMembershipActionRequest
from components.space.membership_service import _load_room
from components.space.model import (
    SpaceEvent,
    SpaceHistoryEntry,
    SpaceInvitation,
    SpaceMembership,
    SpaceRule,
)
from components.space.schemas import SpaceCreateRequest, SpaceUpdateRequest
from components.space.service import _load_active_room_by_uid, _slugify_tag


class SpaceContractTests(unittest.TestCase):
    def test_versioned_space_routes_are_registered(self):
        paths = {route.path for route in app.routes}
        expected = {
            "/spaces/v1",
            "/spaces/v1/invitations",
            "/spaces/v1/invitations/{invitation_uid}",
            "/spaces/v1/{space_uid}",
            "/spaces/v1/{space_uid}/join",
            "/spaces/v1/{space_uid}/membership",
            "/spaces/v1/{space_uid}/members",
            "/spaces/v1/{space_uid}/members/{account_uid}",
            "/spaces/v1/{space_uid}/members/{account_uid}/membership",
            "/spaces/v1/{space_uid}/invitations/{account_uid}",
            "/spaces/v1/{space_uid}/rules",
            "/spaces/v1/{space_uid}/rules/{rule_uid}",
            "/spaces/v1/{space_uid}/events",
            "/spaces/v1/{space_uid}/events/{event_uid}",
            "/spaces/v1/{space_uid}/history",
        }
        self.assertTrue(expected.issubset(paths))

    def test_private_space_is_invite_only(self):
        for invalid_policy in ("open", "request"):
            with self.assertRaises(ValidationError):
                SpaceCreateRequest(
                    name="Закрытый клуб",
                    visibility="private",
                    join_policy=invalid_policy,
                )

        payload = SpaceCreateRequest(
            name="Закрытый клуб",
            visibility="private",
            join_policy="invite",
        )
        self.assertEqual(payload.join_policy, "invite")

    def test_visible_name_cannot_be_only_whitespace(self):
        with self.assertRaises(ValidationError):
            SpaceCreateRequest(name="      ")

    def test_tags_are_trimmed_and_deduplicated(self):
        payload = SpaceCreateRequest(
            name="Кино по пятницам",
            tags=[" кино ", "КИНО", " авторское   кино "],
        )
        self.assertEqual(payload.tags, ["кино", "авторское кино"])

    def test_update_contract_does_not_accept_privileged_legacy_fields(self):
        fields = SpaceUpdateRequest.model_fields
        for forbidden in ("owner_uid", "rating", "is_active", "created_at"):
            self.assertNotIn(forbidden, fields)

    def test_membership_is_unique_per_space_and_account(self):
        names = {constraint.name for constraint in SpaceMembership.__table__.constraints if constraint.name}
        self.assertIn("uq_space_membership", names)

    def test_space_service_room_loader_queries_public_uuid(self):
        space_uid = uuid4()
        room = Room(uid=space_uid, name="UUID service room", is_active=True)
        result = MagicMock()
        result.scalar_one_or_none.return_value = room
        db = MagicMock()
        db.execute = AsyncMock(return_value=result)

        loaded = asyncio.run(_load_active_room_by_uid(db, space_uid))

        self.assertIs(loaded, room)
        statement = db.execute.await_args.args[0]
        sql = str(statement)
        self.assertIn("rooms.uid", sql)
        self.assertNotIn("rooms.id =", sql)

    def test_membership_room_loader_queries_public_uuid(self):
        space_uid = uuid4()
        room = Room(uid=space_uid, name="UUID room")
        result = MagicMock()
        result.scalar_one_or_none.return_value = room
        db = MagicMock()
        db.execute = AsyncMock(return_value=result)

        loaded = asyncio.run(_load_room(db, space_uid))

        self.assertIs(loaded, room)
        statement = db.execute.await_args.args[0]
        sql = str(statement)
        self.assertIn("rooms.uid", sql)
        self.assertNotIn("rooms.id =", sql)

    def test_invitation_is_unique_per_space_and_invitee(self):
        names = {constraint.name for constraint in SpaceInvitation.__table__.constraints if constraint.name}
        self.assertIn("uq_space_invitation_invitee", names)

    def test_space_content_tables_share_space_foreign_key(self):
        for model in (SpaceRule, SpaceEvent, SpaceHistoryEntry):
            targets = {foreign_key.target_fullname for foreign_key in model.__table__.c.room_uid.foreign_keys}
            self.assertEqual(targets, {"rooms.uid"})

    def test_membership_actions_are_allowlisted(self):
        for action in ("approve", "reject", "remove"):
            self.assertEqual(SpaceMembershipActionRequest(action=action).action, action)
        with self.assertRaises(ValidationError):
            SpaceMembershipActionRequest(action="ban")

    def test_invitation_actions_are_allowlisted(self):
        for action in ("accept", "decline"):
            self.assertEqual(SpaceInvitationActionRequest(action=action).action, action)
        with self.assertRaises(ValidationError):
            SpaceInvitationActionRequest(action="forward")

    def test_event_end_must_be_after_start(self):
        start = datetime.utcnow()
        with self.assertRaises(ValidationError):
            SpaceEventCreateRequest(
                title="Ночной квиз",
                starts_at=start,
                ends_at=start - timedelta(minutes=1),
            )

    def test_event_status_is_allowlisted(self):
        self.assertEqual(SpaceEventUpdateRequest(status="cancelled").status, "cancelled")
        with self.assertRaises(ValidationError):
            SpaceEventUpdateRequest(status="hidden")

    def test_tag_slug_is_stable_for_unicode_and_spaces(self):
        self.assertEqual(_slugify_tag("  Авторское   кино  "), "авторское-кино")


if __name__ == "__main__":
    unittest.main()
