from .main import *
from .modules import utils

def expiring_dict(expiration_time: int):
    data = utils.ExpiringDict(expiration_time)
    return data
