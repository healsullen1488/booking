# Хеширование паролей (bcrypt) и JWT.
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app import config, consts


class Hasher:
    def make(self, p):
        return bcrypt.hashpw(p.encode("utf-8"), bcrypt.gensalt()).decode("ascii")

    def check(self, p, h):
        try:
            return bcrypt.checkpw(p.encode("utf-8"), h.encode("ascii"))
        except ValueError:
            return False


class Tokens:
    def make(self, u):
        x = datetime.now(timezone.utc) + timedelta(minutes=config.TOKEN_MINUTES)
        data = {"sub": str(u.id), "role": consts.ROLES[u.role_id], "exp": x}
        return jwt.encode(data, config.SECRET_KEY, algorithm="HS256")

    def decode(self, token):
        return jwt.decode(token, config.SECRET_KEY, algorithms=["HS256"])
