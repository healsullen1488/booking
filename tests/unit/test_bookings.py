import unittest

from app import consts
from app.errors import Conflict, Forbidden, Invalid, NotFound
from tests.fakes import World, t


class Base(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.s = self.w.bs
        self.r = self.w.room        # вместимость 10
        self.e = self.w.emp

    def mk(self, a=10, b=11, user=None, people=3, room=None):
        return self.s.create(user or self.e, (room or self.r).id, t(a), t(b), "Meet", people)


class CreateTest(Base):
    def test_ok(self):
        b = self.mk()
        self.assertEqual((b.status_id, b.user_id, b.room_id), (consts.PENDING, self.e.id, self.r.id))

    def test_strip_title(self):
        b = self.s.create(self.e, self.r.id, t(10), t(11), "  X ", 2)
        self.assertEqual(b.title, "X")

    def test_empty_title(self):
        with self.assertRaises(Invalid):
            self.s.create(self.e, self.r.id, t(10), t(11), " ", 2)

    def test_room_missing(self):
        with self.assertRaises(NotFound):
            self.s.create(self.e, 999, t(10), t(11), "x", 2)

    def test_room_inactive(self):
        self.w.rs.deactivate(self.w.adm, self.r.id)
        with self.assertRaises(Conflict):
            self.mk()

    def test_exact_15_min(self):
        self.s.create(self.e, self.r.id, t(10), t(10, 15), "x", 2)

    def test_14_min(self):
        with self.assertRaises(Invalid):
            self.s.create(self.e, self.r.id, t(10), t(10, 14), "x", 2)

    def test_exact_4_hours(self):
        self.s.create(self.e, self.r.id, t(10), t(14), "x", 2)

    def test_4_hours_1_min(self):
        with self.assertRaises(Invalid):
            self.s.create(self.e, self.r.id, t(10), t(14, 1), "x", 2)

    def test_past(self):
        with self.assertRaises(Invalid):
            self.s.create(self.e, self.r.id, t(10, d=8), t(11, d=8), "x", 2)

    def test_before_open(self):
        with self.assertRaises(Invalid):
            self.s.create(self.e, self.r.id, t(8, 30), t(9, 30), "x", 2)

    def test_after_close(self):
        with self.assertRaises(Invalid):
            self.s.create(self.e, self.r.id, t(20, 30), t(21, 30), "x", 2)

    def test_work_edges(self):
        self.s.create(self.e, self.r.id, t(9), t(10), "x", 2)
        self.s.create(self.e, self.r.id, t(20), t(21), "x", 2)

    def test_people_equal_capacity(self):
        self.mk(people=10)

    def test_people_more_than_capacity(self):
        with self.assertRaises(Invalid):
            self.mk(people=11)

    def test_people_zero(self):
        with self.assertRaises(Invalid):
            self.mk(people=0)

    def test_writes_history(self):
        b = self.mk()
        h = self.w.books.history(b.id)
        self.assertEqual(len(h), 1)
        self.assertEqual((h[0].action_id, h[0].user_id, h[0].status_id),
                         (consts.A_CREATE, self.e.id, consts.PENDING))
        self.assertEqual((h[0].start_at, h[0].end_at), (t(10), t(11)))

    def test_commits_once(self):
        n = self.w.books.commits
        self.mk()
        self.assertEqual(self.w.books.commits, n + 1)

    def test_failed_create_has_no_history(self):
        with self.assertRaises(Invalid):
            self.mk(people=99)
        self.assertEqual(self.w.books.h, [])


class OverlapTest(Base):
    def setUp(self):
        super().setUp()
        self.mk(10, 12)

    def fail(self, a, b):
        with self.assertRaises(Conflict):
            self.mk(a, b, user=self.w.emp2)

    def test_touch_before(self):
        self.mk(9, 10, user=self.w.emp2)

    def test_touch_after(self):
        self.mk(12, 13, user=self.w.emp2)

    def test_same(self):
        self.fail(10, 12)

    def test_partial_before(self):
        self.fail(9, 11)

    def test_partial_after(self):
        self.fail(11, 13)

    def test_inside(self):
        self.fail(10, 11)

    def test_outside(self):
        self.fail(9, 13)

    def test_one_minute(self):
        with self.assertRaises(Conflict):
            self.s.create(self.w.emp2, self.r.id, t(11, 59), t(12, 30), "x", 2)

    def test_other_room_is_free(self):
        r2 = self.w.rs.create(self.w.adm, "Beta", 1, 10)
        self.mk(10, 12, user=self.w.emp2, room=r2)

    def test_other_day_is_free(self):
        self.s.create(self.w.emp2, self.r.id, t(10, d=11), t(12, d=11), "x", 2)

    def test_cancelled_frees_room(self):
        b = self.w.books.get(1)
        self.s.cancel(self.e, b.id)
        self.mk(10, 12, user=self.w.emp2)

    def test_confirmed_still_busy(self):
        self.s.confirm(self.w.man, 1)
        self.fail(11, 13)

    def test_completed_frees_room(self):
        self.s.confirm(self.w.man, 1)
        self.s.complete(self.w.man, 1)
        self.mk(10, 12, user=self.w.emp2)


class MoveTest(Base):
    def setUp(self):
        super().setUp()
        self.b = self.mk(10, 11)

    def test_ok(self):
        b = self.s.move(self.e, self.b.id, t(14), t(15))
        self.assertEqual((b.start_at, b.end_at), (t(14), t(15)))

    def test_history(self):
        self.s.move(self.e, self.b.id, t(14), t(15))
        h = self.w.books.history(self.b.id)
        self.assertEqual([x.action_id for x in h], [consts.A_CREATE, consts.A_MOVE])
        self.assertEqual(h[-1].start_at, t(14))

    def test_overlap_with_self_is_ok(self):
        self.s.move(self.e, self.b.id, t(10, 30), t(11, 30))

    def test_overlap_with_other(self):
        self.mk(14, 15, user=self.w.emp2)
        with self.assertRaises(Conflict):
            self.s.move(self.e, self.b.id, t(14, 30), t(15, 30))

    def test_touch_other_ok(self):
        self.mk(14, 15, user=self.w.emp2)
        self.s.move(self.e, self.b.id, t(15), t(16))

    def test_bad_time(self):
        with self.assertRaises(Invalid):
            self.s.move(self.e, self.b.id, t(14), t(14, 10))

    def test_past(self):
        with self.assertRaises(Invalid):
            self.s.move(self.e, self.b.id, t(10, d=8), t(11, d=8))

    def test_outside_work_time(self):
        with self.assertRaises(Invalid):
            self.s.move(self.e, self.b.id, t(7), t(8))

    def test_other_room(self):
        r2 = self.w.rs.create(self.w.adm, "Beta", 1, 10)
        b = self.s.move(self.e, self.b.id, t(10), t(11), r2.id)
        self.assertEqual(b.room_id, r2.id)

    def test_other_room_too_small(self):
        r2 = self.w.rs.create(self.w.adm, "Tiny", 1, 2)
        with self.assertRaises(Invalid):
            self.s.move(self.e, self.b.id, t(10), t(11), r2.id)

    def test_other_room_inactive(self):
        r2 = self.w.rs.create(self.w.adm, "Beta", 1, 10)
        self.w.rs.deactivate(self.w.adm, r2.id)
        with self.assertRaises(Conflict):
            self.s.move(self.e, self.b.id, t(10), t(11), r2.id)

    def test_other_room_missing(self):
        with self.assertRaises(NotFound):
            self.s.move(self.e, self.b.id, t(10), t(11), 999)

    def test_not_owner(self):
        with self.assertRaises(Forbidden):
            self.s.move(self.w.emp2, self.b.id, t(14), t(15))

    def test_manager_can(self):
        self.s.move(self.w.man, self.b.id, t(14), t(15))

    def test_admin_can(self):
        self.s.move(self.w.adm, self.b.id, t(14), t(15))

    def test_missing(self):
        with self.assertRaises(NotFound):
            self.s.move(self.e, 999, t(14), t(15))

    def test_confirmed_can_move(self):
        self.s.confirm(self.w.man, self.b.id)
        b = self.s.move(self.e, self.b.id, t(14), t(15))
        self.assertEqual(b.status_id, consts.CONFIRMED)

    def test_cancelled_can_not(self):
        self.s.cancel(self.e, self.b.id)
        with self.assertRaises(Conflict):
            self.s.move(self.e, self.b.id, t(14), t(15))

    def test_completed_can_not(self):
        self.s.confirm(self.w.man, self.b.id)
        self.s.complete(self.w.man, self.b.id)
        with self.assertRaises(Conflict):
            self.s.move(self.e, self.b.id, t(14), t(15))


class StatusTest(Base):
    def setUp(self):
        super().setUp()
        self.b = self.mk()
        self.man = self.w.man

    def status(self):
        return self.w.books.get(self.b.id).status_id

    def test_confirm(self):
        self.s.confirm(self.man, self.b.id)
        self.assertEqual(self.status(), consts.CONFIRMED)

    def test_confirm_admin(self):
        self.s.confirm(self.w.adm, self.b.id)
        self.assertEqual(self.status(), consts.CONFIRMED)

    def test_confirm_employee(self):
        with self.assertRaises(Forbidden):
            self.s.confirm(self.e, self.b.id)

    def test_confirm_twice(self):
        self.s.confirm(self.man, self.b.id)
        with self.assertRaises(Conflict):
            self.s.confirm(self.man, self.b.id)

    def test_complete_pending(self):
        with self.assertRaises(Conflict):
            self.s.complete(self.man, self.b.id)

    def test_complete_confirmed(self):
        self.s.confirm(self.man, self.b.id)
        self.s.complete(self.man, self.b.id)
        self.assertEqual(self.status(), consts.COMPLETED)

    def test_complete_employee(self):
        self.s.confirm(self.man, self.b.id)
        with self.assertRaises(Forbidden):
            self.s.complete(self.e, self.b.id)

    def test_cancel_pending(self):
        self.s.cancel(self.e, self.b.id)
        self.assertEqual(self.status(), consts.CANCELLED)

    def test_cancel_confirmed(self):
        self.s.confirm(self.man, self.b.id)
        self.s.cancel(self.e, self.b.id)
        self.assertEqual(self.status(), consts.CANCELLED)

    def test_cancel_by_manager(self):
        self.s.cancel(self.man, self.b.id)
        self.assertEqual(self.status(), consts.CANCELLED)

    def test_cancel_not_owner(self):
        with self.assertRaises(Forbidden):
            self.s.cancel(self.w.emp2, self.b.id)

    def test_cancel_twice(self):
        self.s.cancel(self.e, self.b.id)
        with self.assertRaises(Conflict):
            self.s.cancel(self.e, self.b.id)

    def test_cancel_completed(self):
        self.s.confirm(self.man, self.b.id)
        self.s.complete(self.man, self.b.id)
        with self.assertRaises(Conflict):
            self.s.cancel(self.e, self.b.id)

    def test_from_cancelled_nowhere(self):
        self.s.cancel(self.e, self.b.id)
        for f in (self.s.confirm, self.s.complete):
            with self.assertRaises(Conflict):
                f(self.man, self.b.id)

    def test_completed_to_confirmed(self):
        self.s.confirm(self.man, self.b.id)
        self.s.complete(self.man, self.b.id)
        with self.assertRaises(Conflict):
            self.s.confirm(self.man, self.b.id)

    def test_missing(self):
        with self.assertRaises(NotFound):
            self.s.confirm(self.man, 999)

    def test_conflict_text(self):
        self.s.cancel(self.e, self.b.id)
        with self.assertRaises(Conflict) as cm:
            self.s.confirm(self.man, self.b.id)
        self.assertIn("CANCELLED", cm.exception.msg)
        self.assertIn("CONFIRMED", cm.exception.msg)

    def test_full_history(self):
        self.s.move(self.e, self.b.id, t(12), t(13))
        self.s.confirm(self.man, self.b.id)
        self.s.complete(self.man, self.b.id)
        h = self.s.history(self.e, self.b.id)
        self.assertEqual([x.action_id for x in h], [
            consts.A_CREATE, consts.A_MOVE, consts.A_CONFIRM, consts.A_COMPLETE])
        self.assertEqual([x.user_id for x in h],
                         [self.e.id, self.e.id, self.man.id, self.man.id])
        self.assertEqual(h[-1].status_id, consts.COMPLETED)

    def test_cancel_in_history(self):
        self.s.cancel(self.e, self.b.id)
        h = self.s.history(self.e, self.b.id)
        self.assertEqual(h[-1].action_id, consts.A_CANCEL)
        self.assertEqual(h[-1].status_id, consts.CANCELLED)

    def test_failed_change_has_no_history(self):
        with self.assertRaises(Conflict):
            self.s.complete(self.man, self.b.id)
        self.assertEqual(len(self.w.books.history(self.b.id)), 1)


class ReadTest(Base):
    def test_get_owner(self):
        b = self.mk()
        self.assertEqual(self.s.get(self.e, b.id).id, b.id)

    def test_get_other_employee(self):
        b = self.mk()
        with self.assertRaises(Forbidden):
            self.s.get(self.w.emp2, b.id)

    def test_get_manager(self):
        b = self.mk()
        self.s.get(self.w.man, b.id)

    def test_get_missing(self):
        with self.assertRaises(NotFound):
            self.s.get(self.e, 999)

    def test_mine_only_own(self):
        self.mk(10, 11)
        self.mk(12, 13, user=self.w.emp2)
        p = self.s.mine(self.e)
        self.assertEqual((p.total, [b.user_id for b in p.items]), (1, [self.e.id]))

    def test_mine_empty(self):
        self.assertEqual(self.s.mine(self.e).total, 0)

    def test_mine_paging(self):
        for h in range(9, 14):
            self.mk(h, h + 1)
        p = self.s.mine(self.e, page=2, size=2)
        self.assertEqual((len(p.items), p.total), (2, 5))

    def test_mine_bad_page(self):
        with self.assertRaises(Invalid):
            self.s.mine(self.e, page=0)

    def test_all_manager(self):
        self.mk(10, 11)
        self.mk(12, 13, user=self.w.emp2)
        self.assertEqual(self.s.all(self.w.man).total, 2)

    def test_all_admin(self):
        self.mk()
        self.assertEqual(self.s.all(self.w.adm).total, 1)

    def test_all_employee(self):
        with self.assertRaises(Forbidden):
            self.s.all(self.e)

    def test_all_by_status(self):
        self.mk(10, 11)
        b = self.mk(12, 13)
        self.s.cancel(self.e, b.id)
        self.assertEqual(self.s.all(self.w.man, status_id=consts.CANCELLED).total, 1)

    def test_all_unknown_status(self):
        with self.assertRaises(Invalid):
            self.s.all(self.w.man, status_id=42)

    def test_history_owner(self):
        b = self.mk()
        self.assertEqual(len(self.s.history(self.e, b.id)), 1)

    def test_history_other_employee(self):
        b = self.mk()
        with self.assertRaises(Forbidden):
            self.s.history(self.w.emp2, b.id)

    def test_history_missing(self):
        with self.assertRaises(NotFound):
            self.s.history(self.e, 999)


class FreeTest(Base):
    D = __import__("datetime").date(2026, 11, 10)

    def test_empty(self):
        self.assertEqual(self.s.free(self.r.id, self.D), [(t(9), t(21))])

    def test_with_booking(self):
        self.mk(10, 12)
        self.assertEqual(self.s.free(self.r.id, self.D), [(t(9), t(10)), (t(12), t(21))])

    def test_cancelled_not_busy(self):
        b = self.mk(10, 12)
        self.s.cancel(self.e, b.id)
        self.assertEqual(self.s.free(self.r.id, self.D), [(t(9), t(21))])

    def test_other_room_ignored(self):
        r2 = self.w.rs.create(self.w.adm, "Beta", 1, 10)
        self.mk(10, 12, room=r2)
        self.assertEqual(self.s.free(self.r.id, self.D), [(t(9), t(21))])

    def test_other_day_ignored(self):
        self.s.create(self.e, self.r.id, t(10, d=11), t(12, d=11), "x", 2)
        self.assertEqual(self.s.free(self.r.id, self.D), [(t(9), t(21))])

    def test_min_minutes(self):
        self.mk(10, 11)
        self.mk(11, 12, user=self.w.emp2)
        self.assertEqual(self.s.free(self.r.id, self.D, 600), [])

    def test_inactive_room(self):
        self.w.rs.deactivate(self.w.adm, self.r.id)
        self.assertEqual(self.s.free(self.r.id, self.D), [])

    def test_missing_room(self):
        with self.assertRaises(NotFound):
            self.s.free(999, self.D)

    def test_bad_minutes(self):
        with self.assertRaises(Invalid):
            self.s.free(self.r.id, self.D, 0)

    def test_default_clock(self):
        # без подставленных часов сервис берёт настоящее время
        from app.services.bookings import BookingService
        x = BookingService(self.w.books, self.w.rooms, "Europe/Moscow")
        self.assertEqual(x.now().tzinfo is not None, True)
        self.assertEqual(str(x.tz), "Europe/Moscow")
