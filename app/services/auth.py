# Регистрация, вход, смена ролей.
from app import consts
from app.errors import Conflict, Forbidden, Invalid, NotFound, Unauthorized


class AuthService:
    def __init__(self, users, hasher, tokens):
        # users - репозиторий; hasher.make(p), hasher.check(p, h); tokens.make(user)
        self.users = users
        self.hasher = hasher
        self.tokens = tokens

    def register(self, email, name, password):
        email = email.strip()
        name = name.strip()
        if "@" not in email or email.startswith("@"):
            raise Invalid("bad email")
        if not name:
            raise Invalid("name is empty")
        if len(password) < 6:
            raise Invalid("password is too short")
        if len(password.encode("utf-8")) > 72:
            raise Invalid("password is too long")
        if self.users.by_email(email):
            raise Conflict("email already used")
        # регистрация всегда создаёт EMPLOYEE
        u = self.users.add(email, name, self.hasher.make(password), consts.EMPLOYEE)
        self.users.commit()
        return u

    def login(self, email, password):
        u = self.users.by_email(email.strip())
        if u is None or not self.hasher.check(password, u.pass_hash):
            raise Unauthorized("wrong email or password")
        return self.tokens.make(u)

    def set_role(self, actor, user_id, role_id):
        if actor.role_id != consts.ADMIN:
            raise Forbidden("only admin can change roles")
        if role_id not in consts.ROLES:
            raise Invalid("unknown role")
        u = self.users.get(user_id)
        if u is None:
            raise NotFound("user not found")
        u.role_id = role_id
        self.users.commit()
        return u
