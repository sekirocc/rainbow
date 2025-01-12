class BaseAccessException(Exception):
    def __str__(self):
        return self.message


class ClientHttpError(BaseAccessException):
    def __init__(self, res_status_code=None, res_content=None):
        self.res_status_code = res_status_code
        self.res_content = res_content
        self.message = 'Response status_code: %s, Response content:%s' \
                       % (res_status_code, res_content)
