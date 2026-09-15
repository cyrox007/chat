import unittest
from datetime import datetime

from pydantic import ValidationError

from app import app
from components.engagement.occurrence_model import ActivityOccurrence
from components.engagement.occurrence_service import OCCURRENCE_HORIZON_DAYS
from components.engagement.recurrence import occurrences_between
from components.notification.model import ActivityReminderPreference, UserNotification
from components.notification.schemas import ActivityReminderUpdateRequest
from components.notification.service import (
    MAX_REMINDER_PREFERENCES_PER_SYNC,
    MAX_REMINDERS_PER_ACCOUNT,
)


class NotificationContractTests(unittest.TestCase):
    def test_occurrence_and_notification_routes_are_registered(self):
        route_methods = {
            (route.path, method)
            for route in app.routes
            for method in (getattr(route, "methods", None) or set())
        }
        expected = {
            ("/activity-occurrences/v1/activities/{activity_uid}", "GET"),
            ("/notifications/v1/sync", "POST"),
            ("/notifications/v1/unread-count", "GET"),
            ("/notifications/v1", "GET"),
            ("/notifications/v1/spaces/{space_uid}/reminders", "GET"),
            ("/notifications/v1/activities/{activity_uid}/reminder", "PUT"),
            ("/notifications/v1/activities/{activity_uid}/reminder", "DELETE"),
            ("/notifications/v1/read-all", "POST"),
            ("/notifications/v1/{notification_uid}/read", "PATCH"),
        }
        self.assertTrue(expected.issubset(route_methods))

    def test_notification_api_has_no_cross_account_path(self):
        paths = {route.path for route in app.routes if route.path.startswith("/notifications/v1")}
        self.assertFalse(any("account_uid" in path or "accounts" in path for path in paths))

    def test_reminder_lead_minutes_are_allowlisted(self):
        for value in (15, 60, 1440):
            self.assertEqual(ActivityReminderUpdateRequest(lead_minutes=value).lead_minutes, value)
        with self.assertRaises(ValidationError):
            ActivityReminderUpdateRequest(lead_minutes=30)

    def test_reminder_account_limit_covers_every_syncable_preference(self):
        self.assertEqual(MAX_REMINDERS_PER_ACCOUNT, MAX_REMINDER_PREFERENCES_PER_SYNC)
        self.assertGreater(MAX_REMINDERS_PER_ACCOUNT, 0)
        self.assertLessEqual(MAX_REMINDERS_PER_ACCOUNT, 200)

    def test_occurrence_rows_are_unique_per_activity_start(self):
        constraints = {constraint.name for constraint in ActivityOccurrence.__table__.constraints if constraint.name}
        self.assertIn("uq_activity_occurrence_start", constraints)

    def test_notification_dedupe_is_account_scoped(self):
        constraints = {constraint.name for constraint in UserNotification.__table__.constraints if constraint.name}
        self.assertIn("uq_user_notification_dedupe", constraints)
        self.assertEqual(
            {column.name for column in ActivityReminderPreference.__table__.primary_key.columns},
            {"activity_uid", "account_uid"},
        )

    def test_occurrence_materialization_horizon_is_bounded(self):
        self.assertGreater(OCCURRENCE_HORIZON_DAYS, 0)
        self.assertLessEqual(OCCURRENCE_HORIZON_DAYS, 45)

    def test_monthly_recurrence_does_not_drift_after_short_month(self):
        values = occurrences_between(
            datetime(2027, 1, 31, 18, 0),
            "monthly",
            datetime(2027, 1, 1),
            datetime(2027, 4, 30, 23, 59),
        )
        self.assertEqual(
            values,
            [
                datetime(2027, 1, 31, 18, 0),
                datetime(2027, 2, 28, 18, 0),
                datetime(2027, 3, 31, 18, 0),
                datetime(2027, 4, 30, 18, 0),
            ],
        )

    def test_notification_context_preserves_history_when_activity_is_deleted(self):
        activity_fk = next(iter(UserNotification.__table__.c.activity_uid.foreign_keys))
        occurrence_fk = next(iter(UserNotification.__table__.c.occurrence_uid.foreign_keys))
        self.assertEqual(activity_fk.ondelete, "SET NULL")
        self.assertEqual(occurrence_fk.ondelete, "SET NULL")


if __name__ == "__main__":
    unittest.main()
