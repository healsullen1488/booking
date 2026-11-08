from datetime import datetime

from tests.api.conftest import TZ, at, book, engine


def hm(s):
    # "ЧЧ:ММ" по Москве, независимо от пояса, в котором пришла строка
    return datetime.fromisoformat(s).astimezone(TZ).strftime("%H:%M")


# ---------- пользователи и вход ----------

def test_register_and_login(client):
    r = client.post("/auth/register", json={"email": "a@a.ru", "name": "Ann", "password": "secret1"})
    assert r.status_code == 201
    assert r.json()["role"] == "EMPLOYEE"
    assert "pass_hash" not in r.json()
    r = client.post("/auth/login", data={"username": "a@a.ru", "password": "secret1"})
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"
    assert r.json()["access_token"]


def test_register_duplicate_email(client):
    x = {"email": "a@a.ru", "name": "Ann", "password": "secret1"}
    assert client.post("/auth/register", json=x).status_code == 201
    x["email"] = "A@A.RU"
    assert client.post("/auth/register", json=x).status_code == 409


def test_password_is_hashed_in_db(client):
    client.post("/auth/register", json={"email": "a@a.ru", "name": "Ann", "password": "secret1"})
    with engine.begin() as c:
        h = c.exec_driver_sql("SELECT pass_hash FROM users").scalar()
    assert h.startswith("$2") and "secret1" not in h


def test_login_wrong_password(client):
    client.post("/auth/register", json={"email": "a@a.ru", "name": "Ann", "password": "secret1"})
    r = client.post("/auth/login", data={"username": "a@a.ru", "password": "wrong"})
    assert r.status_code == 401


def test_me_needs_token(client, emp):
    assert client.get("/users/me").status_code == 401
    assert client.get("/users/me", headers={"Authorization": "Bearer abc"}).status_code == 401
    r = client.get("/users/me", headers=emp)
    assert r.status_code == 200 and r.json()["email"] == "emp@a.ru"


def test_admin_changes_role(client, adm, emp):
    uid = client.get("/users/me", headers=emp).json()["id"]
    r = client.patch("/users/%d/role" % uid, headers=adm, json={"role": "MANAGER"})
    assert r.status_code == 200 and r.json()["role"] == "MANAGER"
    # новая роль действует сразу, даже со старым токеном
    r = client.get("/bookings?all=true", headers=emp)
    assert r.status_code == 200


def test_role_change_forbidden_for_employee(client, emp):
    r = client.patch("/users/1/role", headers=emp, json={"role": "ADMIN"})
    assert r.status_code == 403


# ---------- комнаты ----------

def test_employee_cannot_create_room(client, emp):
    r = client.post("/rooms", headers=emp, json={"name": "X", "floor": 1, "capacity": 5})
    assert r.status_code == 403


def test_admin_creates_and_gets_room(client, adm, emp, room):
    assert room["is_active"] is True
    assert [e["name"] for e in room["equipment"]] == ["Проектор", "ТВ"]
    r = client.get("/rooms/%d" % room["id"], headers=emp)
    assert r.status_code == 200 and r.json()["name"] == "Alpha"
    assert client.get("/rooms/999", headers=emp).status_code == 404


def test_room_duplicate_name(client, adm, room):
    r = client.post("/rooms", headers=adm, json={"name": "Alpha", "floor": 1, "capacity": 5})
    assert r.status_code == 409


def test_rooms_filters_and_paging(client, adm, emp):
    for i, (fl, cap, eq) in enumerate([(1, 4, []), (2, 8, [1]), (2, 20, [1, 3]), (3, 12, [4])]):
        r = client.post("/rooms", headers=adm, json={
            "name": "R%d" % i, "floor": fl, "capacity": cap, "equipment_ids": eq})
        assert r.status_code == 201
    names = lambda q: [x["name"] for x in client.get("/rooms" + q, headers=emp).json()["items"]]
    assert names("") == ["R0", "R1", "R2", "R3"]
    assert names("?min_capacity=10") == ["R2", "R3"]
    assert names("?floor=2") == ["R1", "R2"]
    assert names("?equipment_id=1") == ["R1", "R2"]
    assert names("?equipment_id=1&equipment_id=3") == ["R2"]
    r = client.get("/rooms?page=2&size=3", headers=emp).json()
    assert (r["total"], r["page"], r["size"], len(r["items"])) == (4, 2, 3, 1)
    assert client.get("/rooms?size=1000", headers=emp).status_code == 422


def test_update_room(client, adm, emp, room):
    body = {"name": "Alpha2", "floor": 5, "capacity": 6, "equipment_ids": [3]}
    assert client.put("/rooms/%d" % room["id"], headers=emp, json=body).status_code == 403
    r = client.put("/rooms/%d" % room["id"], headers=adm, json=body)
    assert r.status_code == 200
    assert (r.json()["name"], r.json()["capacity"]) == ("Alpha2", 6)
    assert [e["name"] for e in r.json()["equipment"]] == ["Видеосвязь"]


def test_soft_delete_room(client, adm, emp, room):
    assert client.delete("/rooms/%d" % room["id"], headers=emp).status_code == 403
    r = client.delete("/rooms/%d" % room["id"], headers=adm)
    assert r.status_code == 200 and r.json()["is_active"] is False
    # из списка пропала, но по id доступна
    assert client.get("/rooms", headers=emp).json()["total"] == 0
    assert client.get("/rooms?only_active=false", headers=emp).json()["total"] == 1
    assert client.get("/rooms/%d" % room["id"], headers=emp).status_code == 200
    # новую бронь создать нельзя
    r = book(client, emp, room["id"], at(10), at(11))
    assert r.status_code == 409


def test_equipment_admin_only(client, adm, emp):
    assert client.post("/equipment", headers=emp, json={"name": "Колонка"}).status_code == 403
    r = client.post("/equipment", headers=adm, json={"name": "Колонка"})
    assert r.status_code == 201
    assert client.post("/equipment", headers=adm, json={"name": "Колонка"}).status_code == 409
    names = [e["name"] for e in client.get("/equipment", headers=emp).json()]
    assert names == ["Проектор", "ТВ", "Видеосвязь", "Маркерная доска", "Колонка"]


# ---------- брони ----------

def test_create_booking(client, emp, room):
    r = book(client, emp, room["id"], at(10), at(11))
    assert r.status_code == 201
    x = r.json()
    assert (x["status"], x["room_id"], x["people"]) == ("PENDING", room["id"], 3)


def test_overlap_returns_409(client, emp, emp2, room):
    assert book(client, emp, room["id"], at(10), at(12)).status_code == 201
    for a, b in [((10, 0), (12, 0)), ((9, 0), (11, 0)), ((11, 0), (13, 0)),
                 ((10, 30), (11, 30)), ((9, 0), (13, 0))]:
        r = book(client, emp2, room["id"], at(*a), at(*b))
        assert r.status_code == 409, (a, b, r.text)


def test_touching_bookings_are_ok(client, emp, emp2, room):
    assert book(client, emp, room["id"], at(10), at(12)).status_code == 201
    assert book(client, emp2, room["id"], at(12), at(13)).status_code == 201
    assert book(client, emp2, room["id"], at(9), at(10)).status_code == 201


def test_other_room_is_free(client, adm, emp, room):
    r2 = client.post("/rooms", headers=adm, json={"name": "Beta", "floor": 1, "capacity": 5}).json()
    assert book(client, emp, room["id"], at(10), at(11)).status_code == 201
    assert book(client, emp, r2["id"], at(10), at(11)).status_code == 201


def test_booking_rules_return_422(client, emp, room):
    i = room["id"]
    assert book(client, emp, i, at(10), at(10, 14)).status_code == 422     # 14 минут
    assert book(client, emp, i, at(10), at(14, 1)).status_code == 422      # 4 часа 1 минута
    assert book(client, emp, i, at(10), at(10, 15)).status_code == 201     # ровно 15 минут
    assert book(client, emp, i, at(14), at(18)).status_code == 201         # ровно 4 часа
    assert book(client, emp, i, at(7), at(8)).status_code == 422           # до открытия
    assert book(client, emp, i, at(20, 30), at(21, 30)).status_code == 422  # после закрытия
    assert book(client, emp, i, at(10, days=-1), at(11, days=-1)).status_code == 422  # прошлое
    assert book(client, emp, i, at(12), at(13), people=11).status_code == 422  # больше вместимости
    assert book(client, emp, i, at(12), at(13), people=0).status_code == 422
    assert book(client, emp, i, "2030-01-01T10:00:00", "2030-01-01T11:00:00").status_code == 422  # без пояса


def test_booking_unknown_room(client, emp):
    assert book(client, emp, 999, at(10), at(11)).status_code == 404


def test_manager_confirms(client, emp, man, room):
    b = book(client, emp, room["id"], at(10), at(11)).json()
    r = client.post("/bookings/%d/confirm" % b["id"], headers=man)
    assert r.status_code == 200 and r.json()["status"] == "CONFIRMED"
    r = client.post("/bookings/%d/complete" % b["id"], headers=man)
    assert r.status_code == 200 and r.json()["status"] == "COMPLETED"


def test_employee_cannot_confirm(client, emp, room):
    b = book(client, emp, room["id"], at(10), at(11)).json()
    assert client.post("/bookings/%d/confirm" % b["id"], headers=emp).status_code == 403


def test_bad_transitions_return_409(client, emp, man, room):
    b = book(client, emp, room["id"], at(10), at(11)).json()
    u = "/bookings/%d/" % b["id"]
    assert client.post(u + "complete", headers=man).status_code == 409   # PENDING -> COMPLETED
    assert client.post(u + "cancel", headers=emp).status_code == 200
    assert client.post(u + "confirm", headers=man).status_code == 409    # из CANCELLED никуда
    assert client.post(u + "cancel", headers=emp).status_code == 409
    b2 = book(client, emp, room["id"], at(10), at(11)).json()
    u = "/bookings/%d/" % b2["id"]
    client.post(u + "confirm", headers=man)
    client.post(u + "complete", headers=man)
    assert client.post(u + "confirm", headers=man).status_code == 409    # COMPLETED -> CONFIRMED


def test_cancel_frees_the_room(client, emp, emp2, room):
    b = book(client, emp, room["id"], at(10), at(11)).json()
    assert book(client, emp2, room["id"], at(10), at(11)).status_code == 409
    assert client.post("/bookings/%d/cancel" % b["id"], headers=emp).status_code == 200
    assert book(client, emp2, room["id"], at(10), at(11)).status_code == 201


def test_free_slots(client, emp, room):
    book(client, emp, room["id"], at(10), at(12))
    book(client, emp, room["id"], at(15), at(16))
    d = at(0).split("T")[0]
    r = client.get("/rooms/%d/free?day=%s" % (room["id"], d), headers=emp)
    assert r.status_code == 200
    got = [(hm(s["start_at"]), hm(s["end_at"])) for s in r.json()["slots"]]
    assert got == [("09:00", "10:00"), ("12:00", "15:00"), ("16:00", "21:00")]
    r = client.get("/rooms/%d/free?day=%s&minutes=180" % (room["id"], d), headers=emp)
    got = [(hm(s["start_at"]), hm(s["end_at"])) for s in r.json()["slots"]]
    assert got == [("12:00", "15:00"), ("16:00", "21:00")]
    assert client.get("/rooms/999/free?day=" + d, headers=emp).status_code == 404


def test_move_booking(client, emp, emp2, room):
    b = book(client, emp, room["id"], at(10), at(11)).json()
    book(client, emp2, room["id"], at(14), at(15))
    u = "/bookings/%d/move" % b["id"]
    r = client.put(u, headers=emp, json={"start_at": at(12), "end_at": at(13)})
    assert r.status_code == 200 and hm(r.json()["start_at"]) == "12:00"
    r = client.put(u, headers=emp, json={"start_at": at(14, 30), "end_at": at(15, 30)})
    assert r.status_code == 409                                       # занято другой бронью
    r = client.put(u, headers=emp, json={"start_at": at(12, 30), "end_at": at(13, 30)})
    assert r.status_code == 200                                       # с самой собой не конфликтует
    r = client.put(u, headers=emp, json={"start_at": at(7), "end_at": at(8)})
    assert r.status_code == 422
    r = client.put(u, headers=emp2, json={"start_at": at(16), "end_at": at(17)})
    assert r.status_code == 403                                       # чужую нельзя


def test_booking_visibility(client, emp, emp2, man, room):
    b = book(client, emp, room["id"], at(10), at(11)).json()
    book(client, emp2, room["id"], at(12), at(13))
    mine = client.get("/bookings", headers=emp).json()
    assert mine["total"] == 1 and mine["items"][0]["id"] == b["id"]
    assert client.get("/bookings?all=true", headers=emp).status_code == 403
    assert client.get("/bookings?all=true", headers=man).json()["total"] == 2
    assert client.get("/bookings/%d" % b["id"], headers=emp2).status_code == 403
    assert client.get("/bookings/%d" % b["id"], headers=man).status_code == 200
    assert client.get("/bookings/999", headers=emp).status_code == 404


def test_history(client, emp, emp2, man, room):
    b = book(client, emp, room["id"], at(10), at(11)).json()
    client.put("/bookings/%d/move" % b["id"], headers=emp, json={"start_at": at(12), "end_at": at(13)})
    client.post("/bookings/%d/confirm" % b["id"], headers=man)
    client.post("/bookings/%d/cancel" % b["id"], headers=emp)
    r = client.get("/bookings/%d/history" % b["id"], headers=emp)
    assert r.status_code == 200
    assert [x["action"] for x in r.json()] == ["CREATE", "MOVE", "CONFIRM", "CANCEL"]
    assert [x["status"] for x in r.json()] == ["PENDING", "PENDING", "CONFIRMED", "CANCELLED"]
    assert r.json()[2]["user_id"] != r.json()[0]["user_id"]
    assert client.get("/bookings/%d/history" % b["id"], headers=emp2).status_code == 403


def test_errors_have_detail(client, emp, room):
    r = book(client, emp, room["id"], at(10), at(10, 14))
    assert r.status_code == 422 and "detail" in r.json()


def test_openapi_is_available(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    assert "/bookings/{bid}/history" in paths and "/rooms/{room_id}/free" in paths
    assert client.get("/docs").status_code == 200
