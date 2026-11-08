DROP VIEW IF EXISTS booking_info;
DROP TRIGGER IF EXISTS t_history_ro ON booking_history;
DROP TRIGGER IF EXISTS t_booking_lock ON bookings;
DROP TRIGGER IF EXISTS t_booking_status ON bookings;
DROP TRIGGER IF EXISTS t_booking_check ON bookings;
DROP FUNCTION IF EXISTS f_history_ro();
DROP FUNCTION IF EXISTS f_booking_lock();
DROP FUNCTION IF EXISTS f_booking_status();
DROP FUNCTION IF EXISTS f_booking_check();
