E_STATUS_CODE_VALUES = {
    0: 'file not found',
    1: 'invalid bitmap file format',
    2: 'invalid nine-slice metrics',
    3: 'invalid nine-slice index',
    4: 'invalid bitmap index',
    5: 'invalid bargraph index',
    6: 'invalid animation index',
    7: 'invalid animation file format',
    8: 'invalid font index',
    9: 'invalid command parameters',
    10: 'display is out of RAM',
    11: 'invalid region file format',
    12: 'invalid touch calibration',
    13: 'successful touch calibration',
    14: 'invalid file format',
    15: 'invalid trace index',
    16: 'invalid touch region',
    17: 'invalid label index',
    128: 'object not found',
    129: 'property not found',
    130: 'invalid property type',
    131: 'invalid object type',
    132: 'invalid index',
    253: 'timeout',
    254: 'success',
    255: 'unknown exception'
}


class StatusError(Exception):
    def __init__(self, *status_codes: int):
        message = f'The last command resulted in errors: '
        for status_code in status_codes:
            error_desc = E_STATUS_CODE_VALUES.get(status_code, default='unknown code')
            message += f'code {status_code:d}: "{error_desc}", '

        super().__init__(message)


class UnexpectedResponse(Exception):
    """Raised when a response to a command is not what was expected"""
