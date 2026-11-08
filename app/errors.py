# Ошибки сервисов. Код совпадает с HTTP-кодом ответа.


class AppError(Exception):
    code = 400

    def __init__(self, msg=""):
        super().__init__(msg)
        self.msg = msg


class Invalid(AppError):
    code = 422


class Unauthorized(AppError):
    code = 401


class Forbidden(AppError):
    code = 403


class NotFound(AppError):
    code = 404


class Conflict(AppError):
    code = 409
