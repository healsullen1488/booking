-- Триггеры и представление.

-- 1) при создании/переносе: комната активна, участников не больше вместимости
CREATE OR REPLACE FUNCTION f_booking_check() RETURNS trigger AS $$
DECLARE
    r    rooms%ROWTYPE;
    need boolean;
BEGIN
    SELECT * INTO r FROM rooms WHERE id = NEW.room_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'room % not found', NEW.room_id USING ERRCODE = '23503';
    END IF;
    -- проверяем только активные брони и только если поменялось важное
    IF NEW.status_id IN (1, 2) THEN
        IF TG_OP = 'INSERT' THEN
            need := true;
        ELSE
            need := NEW.room_id IS DISTINCT FROM OLD.room_id
                 OR NEW.people  IS DISTINCT FROM OLD.people;
        END IF;
        IF need THEN
            IF NOT r.is_active THEN
                RAISE EXCEPTION 'room % is not active', r.id USING ERRCODE = '23514';
            END IF;
            IF NEW.people > r.capacity THEN
                RAISE EXCEPTION 'people % > capacity %', NEW.people, r.capacity
                    USING ERRCODE = '23514';
            END IF;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER t_booking_check
    BEFORE INSERT OR UPDATE ON bookings
    FOR EACH ROW EXECUTE FUNCTION f_booking_check();

-- 2) новая бронь всегда PENDING; статус меняется только по таблице status_moves
CREATE OR REPLACE FUNCTION f_booking_status() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.status_id <> 1 THEN
            RAISE EXCEPTION 'new booking must be PENDING' USING ERRCODE = '23514';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.status_id IS DISTINCT FROM OLD.status_id THEN
        IF NOT EXISTS (SELECT 1 FROM status_moves
                       WHERE from_id = OLD.status_id AND to_id = NEW.status_id) THEN
            RAISE EXCEPTION 'move % -> % is not allowed', OLD.status_id, NEW.status_id
                USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER t_booking_status
    BEFORE INSERT OR UPDATE ON bookings
    FOR EACH ROW EXECUTE FUNCTION f_booking_status();

-- 3) закрытую (COMPLETED=3, CANCELLED=4) бронь менять нельзя
CREATE OR REPLACE FUNCTION f_booking_lock() RETURNS trigger AS $$
BEGIN
    IF OLD.status_id IN (3, 4) THEN
        RAISE EXCEPTION 'booking % is closed', OLD.id USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER t_booking_lock
    BEFORE UPDATE ON bookings
    FOR EACH ROW EXECUTE FUNCTION f_booking_lock();

-- 4) журнал только дописывается: менять и удалять строки нельзя
CREATE OR REPLACE FUNCTION f_history_ro() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'booking_history is append only' USING ERRCODE = '23514';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER t_history_ro
    BEFORE UPDATE OR DELETE ON booking_history
    FOR EACH ROW EXECUTE FUNCTION f_history_ro();

-- представление: бронь вместе с названиями (для отчётов)
CREATE VIEW booking_info AS
SELECT b.id,
       b.title,
       b.people,
       b.start_at,
       b.end_at,
       r.name  AS room,
       r.floor AS floor,
       u.name  AS user_name,
       u.email AS user_email,
       s.name  AS status
FROM bookings b
JOIN rooms    r ON r.id = b.room_id
JOIN users    u ON u.id = b.user_id
JOIN statuses s ON s.id = b.status_id;
