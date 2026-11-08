-- Ограничения целостности и индексы.

-- уникальность
ALTER TABLE roles     ADD CONSTRAINT roles_name_uq     UNIQUE (name);
ALTER TABLE statuses  ADD CONSTRAINT statuses_name_uq  UNIQUE (name);
ALTER TABLE actions   ADD CONSTRAINT actions_name_uq   UNIQUE (name);
ALTER TABLE equipment ADD CONSTRAINT equipment_name_uq UNIQUE (name);
ALTER TABLE rooms     ADD CONSTRAINT rooms_name_uq     UNIQUE (name);

-- e-mail уникален без учёта регистра
CREATE UNIQUE INDEX users_email_uq ON users (lower(email));

-- внешние ключи
ALTER TABLE users
    ADD CONSTRAINT users_role_fk FOREIGN KEY (role_id) REFERENCES roles (id);

ALTER TABLE status_moves
    ADD CONSTRAINT status_moves_from_fk FOREIGN KEY (from_id) REFERENCES statuses (id),
    ADD CONSTRAINT status_moves_to_fk   FOREIGN KEY (to_id)   REFERENCES statuses (id),
    ADD CONSTRAINT status_moves_diff    CHECK (from_id <> to_id);

ALTER TABLE room_equipment
    ADD CONSTRAINT room_equipment_room_fk
        FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE CASCADE,
    ADD CONSTRAINT room_equipment_eq_fk
        FOREIGN KEY (equipment_id) REFERENCES equipment (id);

ALTER TABLE bookings
    ADD CONSTRAINT bookings_room_fk   FOREIGN KEY (room_id)   REFERENCES rooms (id),
    ADD CONSTRAINT bookings_user_fk   FOREIGN KEY (user_id)   REFERENCES users (id),
    ADD CONSTRAINT bookings_status_fk FOREIGN KEY (status_id) REFERENCES statuses (id);

ALTER TABLE booking_history
    ADD CONSTRAINT history_booking_fk FOREIGN KEY (booking_id) REFERENCES bookings (id),
    ADD CONSTRAINT history_user_fk    FOREIGN KEY (user_id)    REFERENCES users (id),
    ADD CONSTRAINT history_action_fk  FOREIGN KEY (action_id)  REFERENCES actions (id),
    ADD CONSTRAINT history_status_fk  FOREIGN KEY (status_id)  REFERENCES statuses (id);

-- проверки значений
ALTER TABLE rooms
    ADD CONSTRAINT rooms_capacity_ck CHECK (capacity > 0),
    ADD CONSTRAINT rooms_floor_ck    CHECK (floor BETWEEN -5 AND 100),
    ADD CONSTRAINT rooms_name_ck     CHECK (length(trim(name)) > 0);

ALTER TABLE users
    ADD CONSTRAINT users_email_ck CHECK (position('@' in email) > 1),
    ADD CONSTRAINT users_name_ck  CHECK (length(trim(name)) > 0);

ALTER TABLE bookings
    ADD CONSTRAINT bookings_people_ck CHECK (people > 0),
    ADD CONSTRAINT bookings_title_ck  CHECK (length(trim(title)) > 0),
    ADD CONSTRAINT bookings_time_ck   CHECK (end_at > start_at),
    -- от 15 минут до 4 часов включительно
    ADD CONSTRAINT bookings_len_ck
        CHECK (end_at - start_at >= interval '15 minutes'
           AND end_at - start_at <= interval '4 hours');

ALTER TABLE booking_history
    ADD CONSTRAINT history_time_ck CHECK (end_at > start_at);

-- главное правило: у активных броней (PENDING=1, CONFIRMED=2) в одной комнате
-- интервалы не пересекаются. tstzrange полуоткрытый [start, end), поэтому "встык" можно.
ALTER TABLE bookings
    ADD CONSTRAINT bookings_no_overlap
    EXCLUDE USING gist (
        room_id WITH =,
        tstzrange(start_at, end_at) WITH &&
    ) WHERE (status_id IN (1, 2));

-- индексы
CREATE INDEX bookings_user_ix     ON bookings (user_id);
CREATE INDEX bookings_status_ix   ON bookings (status_id);
CREATE INDEX bookings_start_ix    ON bookings (start_at);
CREATE INDEX room_equipment_eq_ix ON room_equipment (equipment_id);
CREATE INDEX history_booking_ix   ON booking_history (booking_id, at);
CREATE INDEX history_user_ix      ON booking_history (user_id);
CREATE INDEX rooms_capacity_ix    ON rooms (capacity) WHERE is_active;
CREATE INDEX users_role_ix        ON users (role_id);
