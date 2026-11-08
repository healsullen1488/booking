DROP INDEX IF EXISTS users_role_ix;
DROP INDEX IF EXISTS rooms_capacity_ix;
DROP INDEX IF EXISTS history_user_ix;
DROP INDEX IF EXISTS history_booking_ix;
DROP INDEX IF EXISTS room_equipment_eq_ix;
DROP INDEX IF EXISTS bookings_start_ix;
DROP INDEX IF EXISTS bookings_status_ix;
DROP INDEX IF EXISTS bookings_user_ix;

ALTER TABLE bookings DROP CONSTRAINT IF EXISTS bookings_no_overlap;
ALTER TABLE booking_history DROP CONSTRAINT IF EXISTS history_time_ck;
ALTER TABLE bookings
    DROP CONSTRAINT IF EXISTS bookings_len_ck,
    DROP CONSTRAINT IF EXISTS bookings_time_ck,
    DROP CONSTRAINT IF EXISTS bookings_title_ck,
    DROP CONSTRAINT IF EXISTS bookings_people_ck;
ALTER TABLE users
    DROP CONSTRAINT IF EXISTS users_name_ck,
    DROP CONSTRAINT IF EXISTS users_email_ck;
ALTER TABLE rooms
    DROP CONSTRAINT IF EXISTS rooms_name_ck,
    DROP CONSTRAINT IF EXISTS rooms_floor_ck,
    DROP CONSTRAINT IF EXISTS rooms_capacity_ck;

ALTER TABLE booking_history
    DROP CONSTRAINT IF EXISTS history_status_fk,
    DROP CONSTRAINT IF EXISTS history_action_fk,
    DROP CONSTRAINT IF EXISTS history_user_fk,
    DROP CONSTRAINT IF EXISTS history_booking_fk;
ALTER TABLE bookings
    DROP CONSTRAINT IF EXISTS bookings_status_fk,
    DROP CONSTRAINT IF EXISTS bookings_user_fk,
    DROP CONSTRAINT IF EXISTS bookings_room_fk;
ALTER TABLE room_equipment
    DROP CONSTRAINT IF EXISTS room_equipment_eq_fk,
    DROP CONSTRAINT IF EXISTS room_equipment_room_fk;
ALTER TABLE status_moves
    DROP CONSTRAINT IF EXISTS status_moves_diff,
    DROP CONSTRAINT IF EXISTS status_moves_to_fk,
    DROP CONSTRAINT IF EXISTS status_moves_from_fk;
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_fk;

DROP INDEX IF EXISTS users_email_uq;
ALTER TABLE rooms     DROP CONSTRAINT IF EXISTS rooms_name_uq;
ALTER TABLE equipment DROP CONSTRAINT IF EXISTS equipment_name_uq;
ALTER TABLE actions   DROP CONSTRAINT IF EXISTS actions_name_uq;
ALTER TABLE statuses  DROP CONSTRAINT IF EXISTS statuses_name_uq;
ALTER TABLE roles     DROP CONSTRAINT IF EXISTS roles_name_uq;
