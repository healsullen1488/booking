# Создать первого администратора:
#   python scripts/make_admin.py admin@example.com "Admin" secret123
# Если пользователь с таким e-mail есть, ему просто ставится роль ADMIN.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import consts
from app.database import Session
from app.repos import UserRepo
from app.security import Hasher
from app.services.auth import AuthService

if len(sys.argv) != 4:
    print("usage: make_admin.py EMAIL NAME PASSWORD")
    sys.exit(1)

email, name, pw = sys.argv[1:]
s = Session()
users = UserRepo(s)
u = users.by_email(email)
if u is None:
    u = AuthService(users, Hasher(), None).register(email, name, pw)
u.role_id = consts.ADMIN
users.commit()
print("admin ready:", u.id, u.email)
