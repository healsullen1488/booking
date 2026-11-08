-- Демо-данные для ручной проверки (по желанию): psql -f db/06_demo.sql
-- Пользователей лучше создавать через API (пароль хешируется bcrypt).
INSERT INTO rooms (name, floor, capacity) VALUES
    ('Альфа', 1, 6), ('Бета', 2, 10), ('Гамма', 3, 20);

INSERT INTO room_equipment (room_id, equipment_id)
SELECT r.id, e.id FROM rooms r, equipment e
WHERE (r.name = 'Альфа' AND e.name IN ('Маркерная доска'))
   OR (r.name = 'Бета'  AND e.name IN ('Проектор', 'Маркерная доска'))
   OR (r.name = 'Гамма' AND e.name IN ('Проектор', 'ТВ', 'Видеосвязь', 'Маркерная доска'));
