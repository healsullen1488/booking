-- Таблицы. Имена простые, как на ER-диаграмме из отчёта.

CREATE EXTENSION IF NOT EXISTS btree_gist;

-- справочники
CREATE TABLE roles (
    id   smallint PRIMARY KEY,
    name varchar(20) NOT NULL
);

CREATE TABLE statuses (
    id   smallint PRIMARY KEY,
    name varchar(20) NOT NULL
);

CREATE TABLE actions (
    id   smallint PRIMARY KEY,
    name varchar(20) NOT NULL
);

CREATE TABLE equipment (
    id   serial PRIMARY KEY,
    name varchar(50) NOT NULL
);

-- допустимые переходы статусов (из какого -> в какой)
CREATE TABLE status_moves (
    from_id smallint NOT NULL,
    to_id   smallint NOT NULL,
    PRIMARY KEY (from_id, to_id)
);

-- основные сущности
CREATE TABLE users (
    id         serial PRIMARY KEY,
    email      varchar(100) NOT NULL,
    name       varchar(100) NOT NULL,
    pass_hash  varchar(100) NOT NULL,
    role_id    smallint NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE rooms (
    id        serial PRIMARY KEY,
    name      varchar(100) NOT NULL,
    floor     smallint NOT NULL,
    capacity  smallint NOT NULL,
    is_active boolean NOT NULL DEFAULT true
);

-- связь "многие ко многим": комната <-> оборудование
CREATE TABLE room_equipment (
    room_id      integer NOT NULL,
    equipment_id integer NOT NULL,
    PRIMARY KEY (room_id, equipment_id)
);

CREATE TABLE bookings (
    id         serial PRIMARY KEY,
    room_id    integer NOT NULL,
    user_id    integer NOT NULL,
    status_id  smallint NOT NULL DEFAULT 1,
    title      varchar(200) NOT NULL,
    people     smallint NOT NULL,
    start_at   timestamptz NOT NULL,
    end_at     timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- журнал: кто, когда, что сделал; start_at/end_at/status_id - снимок на момент действия
CREATE TABLE booking_history (
    id         bigserial PRIMARY KEY,
    booking_id integer NOT NULL,
    user_id    integer NOT NULL,
    action_id  smallint NOT NULL,
    status_id  smallint NOT NULL,
    start_at   timestamptz NOT NULL,
    end_at     timestamptz NOT NULL,
    at         timestamptz NOT NULL DEFAULT now()
);
