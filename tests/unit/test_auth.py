import unittest

from app import consts
from app.errors import Conflict, Forbidden, Invalid, NotFound, Unauthorized
from tests.fakes import World


class AuthTest(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.a = self.w.auth

    def test_register_ok(self):
        u = self.a.register("new@a.ru", "Ivan", "qwerty1")
        self.assertEqual(u.role_id, consts.EMPLOYEE)
        self.assertNotEqual(u.pass_hash, "qwerty1")

    def test_register_strip(self):
        u = self.a.register("  x@a.ru ", " Ivan ", "qwerty1")
        self.assertEqual((u.email, u.name), ("x@a.ru", "Ivan"))

    def test_register_duplicate(self):
        with self.assertRaises(Conflict):
            self.a.register("emp@a.ru", "Ivan", "qwerty1")

    def test_register_duplicate_case(self):
        with self.assertRaises(Conflict):
            self.a.register("EMP@A.RU", "Ivan", "qwerty1")

    def test_register_bad_email(self):
        for e in ["abc", "@a.ru", ""]:
            with self.assertRaises(Invalid):
                self.a.register(e, "Ivan", "qwerty1")

    def test_register_empty_name(self):
        with self.assertRaises(Invalid):
            self.a.register("n@a.ru", "  ", "qwerty1")

    def test_register_short_password(self):
        with self.assertRaises(Invalid):
            self.a.register("n@a.ru", "Ivan", "12345")

    def test_register_password_6(self):
        self.a.register("n@a.ru", "Ivan", "123456")

    def test_register_long_password(self):
        with self.assertRaises(Invalid):
            self.a.register("n@a.ru", "Ivan", "a" * 73)

    def test_register_long_bytes(self):
        # 40 русских букв = 80 байт
        with self.assertRaises(Invalid):
            self.a.register("n@a.ru", "Ivan", "я" * 40)

    def test_register_commits(self):
        n = self.w.users.commits
        self.a.register("n@a.ru", "Ivan", "qwerty1")
        self.assertEqual(n + 1, self.w.users.commits)

    def test_login_ok(self):
        tok = self.a.login("emp@a.ru", "secret1")
        self.assertTrue(tok.startswith("tok-"))

    def test_login_email_case(self):
        self.a.login("EMP@a.ru", "secret1")

    def test_login_wrong_password(self):
        with self.assertRaises(Unauthorized):
            self.a.login("emp@a.ru", "nope123")

    def test_login_unknown_user(self):
        with self.assertRaises(Unauthorized):
            self.a.login("who@a.ru", "secret1")

    def test_set_role_ok(self):
        u = self.a.set_role(self.w.adm, self.w.emp.id, consts.MANAGER)
        self.assertEqual(u.role_id, consts.MANAGER)

    def test_set_role_manager_forbidden(self):
        with self.assertRaises(Forbidden):
            self.a.set_role(self.w.man, self.w.emp.id, consts.MANAGER)

    def test_set_role_employee_forbidden(self):
        with self.assertRaises(Forbidden):
            self.a.set_role(self.w.emp, self.w.emp.id, consts.ADMIN)

    def test_set_role_unknown_role(self):
        with self.assertRaises(Invalid):
            self.a.set_role(self.w.adm, self.w.emp.id, 77)

    def test_set_role_unknown_user(self):
        with self.assertRaises(NotFound):
            self.a.set_role(self.w.adm, 999, consts.MANAGER)
