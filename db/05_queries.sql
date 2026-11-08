-- Примеры запросов к схеме (для защиты и отчёта).

-- 1. Комнаты с оборудованием одной строкой
SELECT r.id, r.name, r.floor, r.capacity,
       coalesce(string_agg(e.name, ', ' ORDER BY e.name), '-') AS equipment
FROM rooms r
LEFT JOIN room_equipment re ON re.room_id = r.id
LEFT JOIN equipment e ON e.id = re.equipment_id
WHERE r.is_active
GROUP BY r.id
ORDER BY r.id;

-- 2. Фильтр: вместимость от 8, есть проектор И ТВ (деление отношений через HAVING)
SELECT r.id, r.name
FROM rooms r
JOIN room_equipment re ON re.room_id = r.id
JOIN equipment e ON e.id = re.equipment_id
WHERE r.is_active AND r.capacity >= 8 AND e.name IN ('Проектор', 'ТВ')
GROUP BY r.id
HAVING count(*) = 2;

-- 3. Есть ли пересечение с новой бронью [10:00, 11:00) в комнате 1
--    (та же логика, что is_overlap в коде: start < new_end AND end > new_start)
SELECT EXISTS (
    SELECT 1 FROM bookings
    WHERE room_id = 1
      AND status_id IN (1, 2)
      AND start_at < timestamptz '2030-01-10 11:00+03'
      AND end_at   > timestamptz '2030-01-10 10:00+03'
) AS is_busy;

-- 4. То же через операторы диапазонов
SELECT EXISTS (
    SELECT 1 FROM bookings
    WHERE room_id = 1 AND status_id IN (1, 2)
      AND tstzrange(start_at, end_at) && tstzrange('2030-01-10 10:00+03', '2030-01-10 11:00+03')
) AS is_busy;

-- 5. Свободные часовые слоты комнаты 1 на дату (09:00-21:00)
SELECT g AS slot_start, g + interval '1 hour' AS slot_end
FROM generate_series(timestamptz '2030-01-10 09:00+03',
                     timestamptz '2030-01-10 20:00+03',
                     interval '1 hour') AS g
WHERE NOT EXISTS (
    SELECT 1 FROM bookings b
    WHERE b.room_id = 1 AND b.status_id IN (1, 2)
      AND tstzrange(b.start_at, b.end_at) && tstzrange(g, g + interval '1 hour')
);

-- 6. Брони пользователя 1 с названиями (представление)
SELECT * FROM booking_info WHERE user_email = 'emp@a.ru' ORDER BY start_at;

-- 7. История брони 1: кто, что и когда сделал
SELECT h.at, u.name AS who, a.name AS action, s.name AS status, h.start_at, h.end_at
FROM booking_history h
JOIN users u    ON u.id = h.user_id
JOIN actions a  ON a.id = h.action_id
JOIN statuses s ON s.id = h.status_id
WHERE h.booking_id = 1
ORDER BY h.at, h.id;

-- 8. Загрузка комнат: сколько часов занято активными бронями
SELECT r.name,
       count(b.id) AS bookings,
       round(coalesce(sum(extract(epoch FROM b.end_at - b.start_at)) / 3600, 0)::numeric, 2) AS hours
FROM rooms r
LEFT JOIN bookings b ON b.room_id = r.id AND b.status_id IN (1, 2, 3)
GROUP BY r.id
ORDER BY hours DESC;

-- 9. Сколько броней в каждом статусе
SELECT s.name, count(b.id) AS total
FROM statuses s
LEFT JOIN bookings b ON b.status_id = s.id
GROUP BY s.id
ORDER BY s.id;

-- 10. Допустимые переходы статусов в читаемом виде
SELECT f.name AS from_status, t.name AS to_status
FROM status_moves m
JOIN statuses f ON f.id = m.from_id
JOIN statuses t ON t.id = m.to_id
ORDER BY m.from_id, m.to_id;

-- 11. Проверка целостности: каждый из запросов должен вернуть 0 строк
-- 11.1 участников больше вместимости у активных броней
SELECT b.id FROM bookings b JOIN rooms r ON r.id = b.room_id
WHERE b.status_id IN (1, 2) AND b.people > r.capacity;
-- 11.2 пересечения активных броней (работает и без EXCLUDE)
SELECT a.id, b.id
FROM bookings a JOIN bookings b
  ON a.room_id = b.room_id AND a.id < b.id
 AND a.status_id IN (1, 2) AND b.status_id IN (1, 2)
 AND a.start_at < b.end_at AND b.start_at < a.end_at;
-- 11.3 у брони нет ни одной записи в журнале
SELECT b.id FROM bookings b
WHERE NOT EXISTS (SELECT 1 FROM booking_history h WHERE h.booking_id = b.id);
-- 11.4 статус брони не совпадает с последней записью журнала (контроль денормализации)
SELECT b.id
FROM bookings b
JOIN LATERAL (SELECT status_id FROM booking_history
              WHERE booking_id = b.id ORDER BY at DESC, id DESC LIMIT 1) h ON true
WHERE h.status_id <> b.status_id;

-- 12. Менеджеры и администраторы
SELECT u.id, u.name, r.name AS role
FROM users u JOIN roles r ON r.id = u.role_id
WHERE r.name IN ('MANAGER', 'ADMIN');
