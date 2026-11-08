# Константы. Числа совпадают со справочниками в db/04_seed.sql.

# роли
EMPLOYEE = 1
MANAGER = 2
ADMIN = 3
ROLES = {EMPLOYEE: "EMPLOYEE", MANAGER: "MANAGER", ADMIN: "ADMIN"}

# статусы
PENDING = 1
CONFIRMED = 2
COMPLETED = 3
CANCELLED = 4
STATUSES = {
    PENDING: "PENDING",
    CONFIRMED: "CONFIRMED",
    COMPLETED: "COMPLETED",
    CANCELLED: "CANCELLED",
}

# активные брони занимают комнату
ACTIVE = (PENDING, CONFIRMED)

# действия журнала
A_CREATE = 1
A_MOVE = 2
A_CONFIRM = 3
A_COMPLETE = 4
A_CANCEL = 5
ACTIONS = {
    A_CREATE: "CREATE",
    A_MOVE: "MOVE",
    A_CONFIRM: "CONFIRM",
    A_COMPLETE: "COMPLETE",
    A_CANCEL: "CANCEL",
}

# допустимые переходы статусов (такие же строки лежат в таблице status_moves)
MOVES = {
    PENDING: (CONFIRMED, CANCELLED),
    CONFIRMED: (COMPLETED, CANCELLED),
    COMPLETED: (),
    CANCELLED: (),
}

# правила времени
MIN_MIN = 15          # минимум минут
MAX_MIN = 240         # максимум минут (4 часа)
OPEN_H = 9            # открытие
CLOSE_H = 21          # закрытие
