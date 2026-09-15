import unittest

from pydantic import ValidationError

from app import app
from components.identity.model import AccountRelationship
from components.social.schemas import FriendActionRequest


class SocialContractTests(unittest.TestCase):
    def test_versioned_social_routes_are_registered(self):
        paths = {route.path for route in app.routes}
        self.assertIn("/social/v1/relationships/{account_uid}", paths)
        self.assertIn("/social/v1/follows/{account_uid}", paths)
        self.assertIn("/social/v1/friends/{account_uid}", paths)
        self.assertIn("/social/v1/friends", paths)
        self.assertIn("/social/v1/friend-requests", paths)
        self.assertIn("/social/v1/blocks/{account_uid}", paths)

    def test_friend_actions_are_explicitly_allowlisted(self):
        for action in ("request", "accept", "reject", "remove"):
            self.assertEqual(FriendActionRequest(action=action).action, action)
        with self.assertRaises(ValidationError):
            FriendActionRequest(action="admin")

    def test_relationship_model_prevents_duplicate_directed_edge(self):
        names = {
            constraint.name
            for constraint in AccountRelationship.__table__.constraints
            if constraint.name
        }
        self.assertIn("uq_account_relationship", names)


if __name__ == "__main__":
    unittest.main()
