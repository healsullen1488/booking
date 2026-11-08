import unittest

from app.errors import Conflict, Forbidden, Invalid, NotFound
from tests.fakes import World


class RoomsTest(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.s = self.w.rs
        self.adm = self.w.adm
        self.pr = self.s.add_equipment(self.adm, "Проектор")
        self.tv = self.s.add_equipment(self.adm, "ТВ")

    def test_create_ok(self):
        r = self.s.create(self.adm, "Beta", 3, 6, [self.pr.id, self.tv.id])
        self.assertEqual((r.name, r.floor, r.capacity, r.is_active), ("Beta", 3, 6, True))
        self.assertEqual(len(r.equipment), 2)

    def test_create_strip_name(self):
        self.assertEqual(self.s.create(self.adm, "  Beta ", 3, 6).name, "Beta")

    def test_create_employee(self):
        with self.assertRaises(Forbidden):
            self.s.create(self.w.emp, "Beta", 3, 6)

    def test_create_manager(self):
        with self.assertRaises(Forbidden):
            self.s.create(self.w.man, "Beta", 3, 6)

    def test_create_empty_name(self):
        with self.assertRaises(Invalid):
            self.s.create(self.adm, " ", 3, 6)

    def test_create_zero_capacity(self):
        with self.assertRaises(Invalid):
            self.s.create(self.adm, "Beta", 3, 0)

    def test_create_bad_floor(self):
        for f in (-6, 101):
            with self.assertRaises(Invalid):
                self.s.create(self.adm, "Beta", f, 5)

    def test_create_floor_edges(self):
        self.s.create(self.adm, "Low", -5, 5)
        self.s.create(self.adm, "High", 100, 5)

    def test_create_duplicate(self):
        with self.assertRaises(Conflict):
            self.s.create(self.adm, "Alpha", 1, 5)

    def test_create_unknown_equipment(self):
        with self.assertRaises(Invalid):
            self.s.create(self.adm, "Beta", 3, 6, [999])

    def test_create_equipment_duplicates_ignored(self):
        r = self.s.create(self.adm, "Beta", 3, 6, [self.pr.id, self.pr.id])
        self.assertEqual(len(r.equipment), 1)

    def test_get_ok(self):
        self.assertEqual(self.s.get(self.w.room.id).name, "Alpha")

    def test_get_missing(self):
        with self.assertRaises(NotFound):
            self.s.get(999)

    def test_update_ok(self):
        r = self.s.update(self.adm, self.w.room.id, "Gamma", 5, 12, [self.tv.id])
        self.assertEqual((r.name, r.floor, r.capacity), ("Gamma", 5, 12))
        self.assertEqual([e.name for e in r.equipment], ["ТВ"])

    def test_update_same_name(self):
        self.s.update(self.adm, self.w.room.id, "Alpha", 5, 12)

    def test_update_name_taken(self):
        self.s.create(self.adm, "Beta", 1, 5)
        with self.assertRaises(Conflict):
            self.s.update(self.adm, self.w.room.id, "Beta", 5, 12)

    def test_update_employee(self):
        with self.assertRaises(Forbidden):
            self.s.update(self.w.emp, self.w.room.id, "Gamma", 5, 12)

    def test_update_missing(self):
        with self.assertRaises(NotFound):
            self.s.update(self.adm, 999, "Gamma", 5, 12)

    def test_update_bad_values(self):
        with self.assertRaises(Invalid):
            self.s.update(self.adm, self.w.room.id, "Gamma", 5, 0)

    def test_deactivate_ok(self):
        r = self.s.deactivate(self.adm, self.w.room.id)
        self.assertFalse(r.is_active)

    def test_deactivate_employee(self):
        with self.assertRaises(Forbidden):
            self.s.deactivate(self.w.emp, self.w.room.id)

    def test_deactivate_missing(self):
        with self.assertRaises(NotFound):
            self.s.deactivate(self.adm, 999)

    def test_list_default(self):
        p = self.s.list()
        self.assertEqual((p.total, p.page, p.size), (1, 1, 20))

    def test_list_hides_inactive(self):
        self.s.deactivate(self.adm, self.w.room.id)
        self.assertEqual(self.s.list().total, 0)

    def test_list_show_inactive(self):
        self.s.deactivate(self.adm, self.w.room.id)
        self.assertEqual(self.s.list(only_active=False).total, 1)

    def test_list_filter_capacity(self):
        self.s.create(self.adm, "Big", 1, 30)
        p = self.s.list(min_capacity=20)
        self.assertEqual([r.name for r in p.items], ["Big"])

    def test_list_filter_capacity_equal(self):
        self.assertEqual(self.s.list(min_capacity=10).total, 1)

    def test_list_filter_floor(self):
        self.s.create(self.adm, "Up", 7, 5)
        self.assertEqual([r.name for r in self.s.list(floor=7).items], ["Up"])

    def test_list_filter_equipment(self):
        self.s.create(self.adm, "WithPr", 1, 5, [self.pr.id])
        self.s.create(self.adm, "Both", 1, 5, [self.pr.id, self.tv.id])
        names = [r.name for r in self.s.list(equipment_ids=[self.pr.id]).items]
        self.assertEqual(names, ["WithPr", "Both"])
        names = [r.name for r in self.s.list(equipment_ids=[self.pr.id, self.tv.id]).items]
        self.assertEqual(names, ["Both"])

    def test_list_paging(self):
        for i in range(5):
            self.s.create(self.adm, "R%d" % i, 1, 5)
        p1 = self.s.list(page=1, size=4)
        p2 = self.s.list(page=2, size=4)
        self.assertEqual((len(p1.items), len(p2.items), p1.total), (4, 2, 6))

    def test_list_page_beyond(self):
        self.assertEqual(self.s.list(page=5, size=10).items, [])

    def test_list_bad_page(self):
        for page, size in [(0, 10), (1, 0), (1, 101)]:
            with self.assertRaises(Invalid):
                self.s.list(page=page, size=size)

    def test_equipment_list(self):
        self.assertEqual([e.name for e in self.s.equipment()], ["Проектор", "ТВ"])

    def test_equipment_add_employee(self):
        with self.assertRaises(Forbidden):
            self.s.add_equipment(self.w.emp, "Колонка")

    def test_equipment_add_duplicate(self):
        with self.assertRaises(Conflict):
            self.s.add_equipment(self.adm, "ТВ")

    def test_equipment_add_empty(self):
        with self.assertRaises(Invalid):
            self.s.add_equipment(self.adm, " ")
