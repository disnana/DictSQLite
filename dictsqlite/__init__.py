from .main import *
from .modules import utils

def expiring_dict(expiration_time: int):
    expiring_dict = utils.ExpiringDict(expiration_time)
    return expiring_dict
