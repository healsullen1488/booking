-- Справочники. id совпадают с app/consts.py и с числами в триггерах.

INSERT INTO roles (id, name) VALUES (1, 'EMPLOYEE'), (2, 'MANAGER'), (3, 'ADMIN');

INSERT INTO statuses (id, name) VALUES
    (1, 'PENDING'), (2, 'CONFIRMED'), (3, 'COMPLETED'), (4, 'CANCELLED');

INSERT INTO actions (id, name) VALUES
    (1, 'CREATE'), (2, 'MOVE'), (3, 'CONFIRM'), (4, 'COMPLETE'), (5, 'CANCEL');

INSERT INTO status_moves (from_id, to_id) VALUES
    (1, 2),  -- PENDING   -> CONFIRMED
    (1, 4),  -- PENDING   -> CANCELLED
    (2, 3),  -- CONFIRMED -> COMPLETED
    (2, 4);  -- CONFIRMED -> CANCELLED

INSERT INTO equipment (name) VALUES
    ('Проектор'), ('ТВ'), ('Видеосвязь'), ('Маркерная доска');
