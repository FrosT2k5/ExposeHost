import os
from binascii import hexlify

def random_string(length: int):
    r_string = hexlify(os.urandom(length)).decode()

    # r_string will be of twice the size of length 
    # since each byte contains 2 hex chars eg: 0xaa (1byte, but 2 chars)
    # return sliced string with length
    return r_string[0:length]


