from requests.exceptions import RequestException


class DatasetNotFoundException(RequestException):
    pass
