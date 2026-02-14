from omniagent.exceptions.error import AppException

class MessageParseException(AppException):
    def __init__(self, message: str, note: str):
        super().__init__(message, note, 'SCHEMA-00', 500)
