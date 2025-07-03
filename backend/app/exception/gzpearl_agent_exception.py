from http import HTTPStatus

class GZPearlBackendException(Exception):
    def __init__(self, error_code: int, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(self.message)


class OpenAIBadRequestException(GZPearlBackendException):
    def __init__(self, message: str):
        error_code = HTTPStatus.BAD_REQUEST
        super().__init__(error_code, message)