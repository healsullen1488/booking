import unittest
from datetime import date, datetime, timezone

from app import consts
from app.errors import Invalid
from app.services import rules
from tests.fakes import NOW, TZ, t


class OverlapTest(unittest.TestCase):
    def test_touch_right(self):
        # встык: конец первой == начало второй
        self.assertFalse(rules.is_overlap(t(10), t(11), t(11), t(12)))

    def test_touch_left(self):
        self.assertFalse(rules.is_overlap(t(11), t(12), t(10), t(11)))

    def test_partial_left(self):
        self.assertTrue(rules.is_overlap(t(10), t(12), t(9), t(11)))

    def test_partial_right(self):
        self.assertTrue(rules.is_overlap(t(10), t(12), t(11), t(13)))

    def test_inside(self):
        self.assertTrue(rules.is_overlap(t(10), t(14), t(11), t(12)))

    def test_outside(self):
        self.assertTrue(rules.is_overlap(t(11), t(12), t(10), t(14)))

    def test_same(self):
        self.assertTrue(rules.is_overlap(t(10), t(11), t(10), t(11)))

    def test_far(self):
        self.assertFalse(rules.is_overlap(t(9), t(10), t(15), t(16)))

    def test_one_minute(self):
        self.assertTrue(rules.is_overlap(t(10), t(11), t(10, 59), t(12)))

    def test_other_day(self):
        self.assertFalse(rules.is_overlap(t(10), t(11), t(10, d=11), t(11, d=11)))


class CheckTimeTest(unittest.TestCase):
    def ok(self, a, b):
        rules.check_time(a, b, NOW, TZ)

    def bad(self, a, b, text=None):
        with self.assertRaises(Invalid) as cm:
            rules.check_time(a, b, NOW, TZ)
        if text:
            self.assertIn(text, cm.exception.msg)

    def test_normal(self):
        self.ok(t(10), t(11))

    def test_exact_15(self):
        self.ok(t(10), t(10, 15))

    def test_14_min(self):
        self.bad(t(10), t(10, 14), "shorter")

    def test_exact_4h(self):
        self.ok(t(10), t(14))

    def test_4h_1min(self):
        self.bad(t(10), t(14, 1), "longer")

    def test_end_equals_start(self):
        self.bad(t(10), t(10), "after start")

    def test_end_before_start(self):
        self.bad(t(11), t(10), "after start")

    def test_naive_start(self):
        with self.assertRaises(Invalid):
            rules.check_time(datetime(2026, 11, 10, 10), t(11), NOW, TZ)

    def test_naive_end(self):
        with self.assertRaises(Invalid):
            rules.check_time(t(10), datetime(2026, 11, 10, 11), NOW, TZ)

    def test_past(self):
        self.bad(t(9, d=8), t(10, d=8), "past")

    def test_start_equals_now(self):
        rules.check_time(NOW.replace(hour=9), NOW.replace(hour=10), NOW.replace(hour=9), TZ)

    def test_one_second_before_now(self):
        n = t(10, d=9)
        with self.assertRaises(Invalid):
            rules.check_time(t(9, 59, d=9), t(10, 59, d=9), n, TZ)

    def test_open_09(self):
        self.ok(t(9), t(10))

    def test_before_open(self):
        self.bad(t(8, 30), t(9, 30), "09:00")

    def test_close_21(self):
        self.ok(t(20), t(21))

    def test_after_close(self):
        self.bad(t(20, 30), t(21, 30), "09:00")

    def test_night(self):
        self.bad(t(23), t(23, 30), "09:00")

    def test_over_midnight(self):
        self.bad(t(23), t(23, 59) .replace(day=11, hour=1), "one day")

    def test_utc_input_converted(self):
        # 07:00 UTC = 10:00 Москва, это нормально
        a = datetime(2026, 11, 10, 7, 0, tzinfo=timezone.utc)
        b = datetime(2026, 11, 10, 8, 0, tzinfo=timezone.utc)
        self.ok(a, b)

    def test_utc_input_outside(self):
        # 03:00 UTC = 06:00 Москва, рано
        a = datetime(2026, 11, 10, 3, 0, tzinfo=timezone.utc)
        b = datetime(2026, 11, 10, 4, 0, tzinfo=timezone.utc)
        self.bad(a, b, "09:00")


class PeopleTest(unittest.TestCase):
    def test_equal(self):
        rules.check_people(10, 10)

    def test_one(self):
        rules.check_people(1, 10)

    def test_more(self):
        with self.assertRaises(Invalid):
            rules.check_people(11, 10)

    def test_zero(self):
        with self.assertRaises(Invalid):
            rules.check_people(0, 10)

    def test_negative(self):
        with self.assertRaises(Invalid):
            rules.check_people(-3, 10)


class MovesTest(unittest.TestCase):
    def test_allowed(self):
        for a, b in [(1, 2), (1, 4), (2, 3), (2, 4)]:
            self.assertTrue(rules.can_move(a, b), (a, b))

    def test_not_allowed(self):
        ok = {(1, 2), (1, 4), (2, 3), (2, 4)}
        for a in consts.STATUSES:
            for b in consts.STATUSES:
                if (a, b) not in ok:
                    self.assertFalse(rules.can_move(a, b), (a, b))

    def test_completed_to_confirmed(self):
        self.assertFalse(rules.can_move(consts.COMPLETED, consts.CONFIRMED))

    def test_cancelled_nowhere(self):
        for b in consts.STATUSES:
            self.assertFalse(rules.can_move(consts.CANCELLED, b))

    def test_unknown_status(self):
        self.assertFalse(rules.can_move(99, 1))


class FreeSlotsTest(unittest.TestCase):
    D = date(2026, 11, 10)

    def f(self, busy, now=NOW, minutes=15):
        return rules.free_slots(busy, self.D, TZ, now, minutes)

    def test_empty_day(self):
        self.assertEqual(self.f([]), [(t(9), t(21))])

    def test_one_in_middle(self):
        self.assertEqual(self.f([(t(12), t(13))]), [(t(9), t(12)), (t(13), t(21))])

    def test_start_of_day(self):
        self.assertEqual(self.f([(t(9), t(10))]), [(t(10), t(21))])

    def test_end_of_day(self):
        self.assertEqual(self.f([(t(20), t(21))]), [(t(9), t(20))])

    def test_full_day(self):
        self.assertEqual(self.f([(t(9), t(13)), (t(13), t(17)), (t(17), t(21))]), [])

    def test_unsorted(self):
        r = self.f([(t(15), t(16)), (t(10), t(11))])
        self.assertEqual(r, [(t(9), t(10)), (t(11), t(15)), (t(16), t(21))])

    def test_touching(self):
        r = self.f([(t(10), t(11)), (t(11), t(12))])
        self.assertEqual(r, [(t(9), t(10)), (t(12), t(21))])

    def test_nested(self):
        r = self.f([(t(10), t(14)), (t(11), t(12))])
        self.assertEqual(r, [(t(9), t(10)), (t(14), t(21))])

    def test_short_gap_skipped(self):
        r = self.f([(t(10), t(11)), (t(11, 10), t(12))])
        self.assertEqual(r, [(t(9), t(10)), (t(12), t(21))])

    def test_gap_exact_min(self):
        r = self.f([(t(10), t(11)), (t(11, 15), t(12))])
        self.assertIn((t(11), t(11, 15)), r)

    def test_min_minutes_param(self):
        r = self.f([(t(10), t(11)), (t(11, 30), t(12))], minutes=60)
        self.assertEqual(r, [(t(9), t(10)), (t(12), t(21))])

    def test_today_starts_from_now(self):
        n = t(13, 20, d=10)
        self.assertEqual(self.f([], now=n), [(n, t(21))])

    def test_today_after_close(self):
        self.assertEqual(self.f([], now=t(21, 30, d=10)), [])

    def test_today_busy_before_now(self):
        n = t(13, d=10)
        r = self.f([(t(10), t(11)), (t(14), t(15))], now=n)
        self.assertEqual(r, [(n, t(14)), (t(15), t(21))])

    def test_busy_outside_window(self):
        r = self.f([(t(7), t(8)), (t(22), t(23))])
        self.assertEqual(r, [(t(9), t(21))])

    def test_busy_crossing_open(self):
        r = self.f([(t(8), t(10))])
        self.assertEqual(r, [(t(10), t(21))])

    def test_utc_busy(self):
        a = datetime(2026, 11, 10, 9, 0, tzinfo=timezone.utc)  # 12:00 MSK
        b = datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc)  # 13:00 MSK
        self.assertEqual(self.f([(a, b)]), [(t(9), t(12)), (t(13), t(21))])

    def test_day_window(self):
        self.assertEqual(rules.day_window(self.D, TZ), (t(9), t(21)))
