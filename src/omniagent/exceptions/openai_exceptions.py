from omniagent.exceptions.error import AppException

class UnrecognizedMessageTypeException(AppException):
    def __init__(self, message: str, note: str):
        super().__init__(message, note, 'OPENAI-00', 500)
