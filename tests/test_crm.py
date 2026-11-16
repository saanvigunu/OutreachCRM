import datetime
import unittest

from outreachcrm import core
from outreachcrm.db import connect


TODAY = datetime.date.today()
DAYS = datetime.timedelta(days=1)


def iso(d):
    return d.isoformat()


class CrmTestBase(unittest.TestCase):
    def setUp(self):
        self.db = connect(":memory:")
        self.alice = core.add_contact(
            self.db, "Alice Chen", "alice@lab.berkeley.edu",
            org="BAIR", role="PhD student")
        self.bob = core.add_contact(
            self.db, "Bob Rivera", "bob@startup.com", org="Stealth")


class ContactTests(CrmTestBase):
    def test_add_and_get(self):
        c = core.get_contact(self.db, self.alice)
        self.assertEqual(c["name"], "Alice Chen")
        self.assertEqual(c["org"], "BAIR")

    def test_find_by_email(self):
        self.assertEqual(core.find_contact(self.db, "alice@lab.berkeley.edu")["id"],
                         self.alice)
        self.assertIsNone(core.find_contact(self.db, "nobody@x.com"))

    def test_bad_email_rejected(self):
        with self.assertRaises(ValueError):
            core.add_contact(self.db, "No Email", "not-an-email")

    def test_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            core.add_contact(self.db, "  ", "x@y.com")

    def test_missing_contact_raises(self):
        with self.assertRaises(KeyError):
            core.get_contact(self.db, 999)


class FollowUpTests(CrmTestBase):
    def test_nothing_due_without_outreach(self):
        self.assertEqual(core.followups_due(self.db), [])

    def test_not_due_before_window(self):
        core.log_outreach(self.db, self.alice,
                          sent_date=iso(TODAY - 3 * DAYS), followup_days=5)
        self.assertEqual(core.followups_due(self.db), [])

    def test_due_after_window(self):
        core.log_outreach(self.db, self.alice,
                          sent_date=iso(TODAY - 6 * DAYS), followup_days=5)
        due = core.followups_due(self.db)
        self.assertEqual(len(due), 1)
        self.assertEqual(due[0]["contact"]["id"], self.alice)
        self.assertEqual(due[0]["days_waiting"], 6)
        self.assertEqual(due[0]["overdue_by"], 1)

    def test_exact_boundary_is_due(self):
        core.log_outreach(self.db, self.alice,
                          sent_date=iso(TODAY - 5 * DAYS), followup_days=5)
        self.assertEqual(len(core.followups_due(self.db)), 1)

    def test_logging_followup_resets_clock(self):
        core.log_outreach(self.db, self.alice,
                          sent_date=iso(TODAY - 9 * DAYS), followup_days=5)
        core.log_outreach(self.db, self.alice, kind="follow-up",
                          sent_date=iso(TODAY - 2 * DAYS), followup_days=5)
        self.assertEqual(core.followups_due(self.db), [])

    def test_replied_contact_not_due(self):
        core.log_outreach(self.db, self.alice,
                          sent_date=iso(TODAY - 9 * DAYS))
        core.mark_status(self.db, self.alice, "replied")
        self.assertEqual(core.followups_due(self.db), [])

    def test_dead_contact_not_due(self):
        core.log_outreach(self.db, self.alice,
                          sent_date=iso(TODAY - 9 * DAYS))
        core.mark_status(self.db, self.alice, "dead")
        self.assertEqual(core.followups_due(self.db), [])

    def test_most_overdue_first(self):
        core.log_outreach(self.db, self.alice,
                          sent_date=iso(TODAY - 10 * DAYS), followup_days=5)
        core.log_outreach(self.db, self.bob,
                          sent_date=iso(TODAY - 7 * DAYS), followup_days=5)
        due = core.followups_due(self.db)
        self.assertEqual([d["contact"]["id"] for d in due],
                         [self.alice, self.bob])

    def test_mark_without_outreach_raises(self):
        with self.assertRaises(ValueError):
            core.mark_status(self.db, self.alice, "replied")

    def test_bad_kind_rejected(self):
        with self.assertRaises(ValueError):
            core.log_outreach(self.db, self.alice, kind="telepathy")


class StatsTests(CrmTestBase):
    def test_empty_stats(self):
        s = core.stats(self.db)
        self.assertEqual(s["emails_sent"], 0)
        self.assertEqual(s["reply_rate"], 0.0)

    def test_funnel_numbers(self):
        core.log_outreach(self.db, self.alice, sent_date=iso(TODAY - 9 * DAYS))
        core.log_outreach(self.db, self.bob, sent_date=iso(TODAY - 8 * DAYS))
        core.log_outreach(self.db, self.bob, kind="follow-up",
                          sent_date=iso(TODAY - 2 * DAYS))
        core.mark_status(self.db, self.bob, "replied")
        s = core.stats(self.db)
        self.assertEqual(s["emails_sent"], 3)
        self.assertEqual(s["initial_emails"], 2)
        self.assertEqual(s["contacts_replied"], 1)
        self.assertEqual(s["reply_rate"], 0.5)

    def test_by_org(self):
        core.log_outreach(self.db, self.alice)
        core.log_outreach(self.db, self.bob)
        core.mark_status(self.db, self.alice, "replied")
        s = core.stats(self.db)
        self.assertEqual(s["by_org"]["BAIR"], {"sent": 1, "replies": 1})
        self.assertEqual(s["by_org"]["Stealth"], {"sent": 1, "replies": 0})


class PipelineTests(CrmTestBase):
    def test_pipeline_latest_state(self):
        core.log_outreach(self.db, self.alice, sent_date=iso(TODAY - 9 * DAYS))
        core.log_outreach(self.db, self.alice, kind="follow-up",
                          sent_date=iso(TODAY - 1 * DAYS))
        rows = {r["contact"]["id"]: r for r in core.pipeline(self.db)}
        self.assertEqual(rows[self.alice]["outreach_count"], 2)
        self.assertEqual(rows[self.alice]["latest"]["kind"], "follow-up")
        self.assertIsNone(rows[self.bob]["latest"])


if __name__ == "__main__":
    unittest.main()
