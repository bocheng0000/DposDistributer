# -*- coding: utf-8 -*-
#
#    BitcoinLib - Python Cryptocurrency Library
#    ENCODING - Methods for encoding and conversion
#    © 2016 - 2018 October - 1200 Web Development <http://1200wd.com/>
#    2019 Bocheng.Zhang <bocheng0000@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import base58
import binascii
from copy import deepcopy
import hashlib
import struct

from utility import util

INFINITYLEN = 1
FLAGLEN = 1
XORYVALUELEN = 32
COMPRESSEDLEN = 33
NOCOMPRESSEDLEN = 65
COMPEVENFLAG = 0x02
COMPODDFLAG = 0x03
NOCOMPRESSEDFLAG = 0x04
EMPTYBYTE = 0x00
# P256PARAMA = -3

# Address Type
STANDARD = 0xAC
REGISTERID = 0xAD
MULTISIG = 0xAE
CROSSCHAIN = 0xAF

# Prefix for differeyt Address
PrefixStandard = b'21'
PrefixRegisterId = b'67'
PrefixMultisig = b'12'
PrefixCrossChain = b'4B'


class EncodingError(Exception):
    """ Log and raise encoding errors """

    def __init__(self, msg=''):
        self.msg = msg
        util.feedback(content=msg, level=util.ERROR, module="ENCODE")

    def __str__(self):
        return self.msg


def double_sha256(string, as_hex=False):
    """
    Get double SHA256 hash of string

    :param string: String to be hashed
    :type string: bytes
    :param as_hex: Return value as hexadecimal string. Default is False
    :type as_hex

    :return bytes, str:
    """
    if not as_hex:
        return hashlib.sha256(hashlib.sha256(string).digest()).digest()
    else:
        return hashlib.sha256(hashlib.sha256(string).digest()).hexdigest()


def bytes_to_hexstring(data, reverse=True):
    if reverse:
        return ''.join(reversed(['{:02x}'.format(v) for v in data]))
    else:
        return ''.join(['{:02x}'.format(v) for v in data])


def hexstring_to_bytes(s: str, reverse=True):
    if reverse:
        return bytes(reversed([int(s[x:x + 2], 16) for x in range(0, len(s), 2)]))
    else:
        return bytes([int(s[x:x + 2], 16) for x in range(0, len(s), 2)])


def normalize_var(var, base=256):
    """
    For Python 2 convert variabele to string
    For Python 3 convert to bytes
    Convert decimals to integer type

    :param var: input variable in any format
    :type var: str, byte, bytearray, unicode
    :param base: specify variable format, i.e. 10 for decimal, 16 for hex
    :type base: int

    :return: Normalized var in string for Python 2, bytes for Python 3, decimal for base10
    """
    try:
        if isinstance(var, str):
            var = var.encode('ISO-8859-1')
    except ValueError:
        try:
            var = var.encode('utf-8')
        except ValueError:
            util.feedback(content="Unknown character '%s' in input format" % var, level=util.ERROR, module="ENCODE")
            raise EncodingError("Unknown character '%s' in input format" % var)

    if base == 10:
        return int(var)
    elif isinstance(var, list):
        return deepcopy(var)
    else:
        return var


def to_bytes(string, unhexlify=True):
    """
    Convert String, Unicode or ByteArray to Bytes

    :param string: String to convert
    :type string: str, unicode, bytes, bytearray
    :param unhexlify: Try to unhexlify hexstring
    :type unhexlify: bool

    :return: Bytes var
    """
    s = normalize_var(string)
    if unhexlify:
        try:
            s = binascii.unhexlify(s)
            return s
        except (TypeError, binascii.Error):
            pass
    return s


# address convert
def programhash_to_address(programhash):
    """
    Convert public key hash to Base58 encoded address

    :param programhash: Public Key Hash
    :type programhash: str, bytes

    :return str: Crypto currency address in base-58 format
    """

    if isinstance(programhash, str):
        data = hexstring_to_bytes(programhash, reverse=False)
    else:
        data = programhash
    return base58.b58encode(data + double_sha256(data)[0:4]).decode()


def address_to_programhash(address: str, as_hex=True):
    """
    Convert Base58 encoded address to public key hash

    :param address: Crypto currency address in base-58 format
    :type address: str, bytes
    :param as_hex: Output as hexstring
    :type as_hex: bool

    :return bytes, str: Public Key Hash
    """
    try:
        data = base58.b58decode(address.encode())
    except EncodingError as err:
        raise EncodingError("Invalid address %s: %s" % (address, err))
    programhash = data[:21]
    if as_hex:
        return programhash.hex()
    else:
        return programhash


def get_code_from_pb(public_key: str):
    pub_bytes = bytes.fromhex(public_key)
    data_list = []
    data_list.append(struct.pack("B", len(pub_bytes)))
    data_list.append(pub_bytes)
    data_list.append(struct.pack("B", STANDARD))
    return b''.join(data_list).hex()


def encode_point(is_compressed, public_key_ECC):
    public_key_x = public_key_ECC._point._x
    public_key_y = public_key_ECC._point._y

    if public_key_x is None or public_key_y is None:
        infinity = []
        for i in range(INFINITYLEN):
            infinity.append(EMPTYBYTE)
        return infinity
    encodedData = []
    if is_compressed:
        for i in range(COMPRESSEDLEN):
            encodedData.append(EMPTYBYTE)
    else:
        for i in range(NOCOMPRESSEDLEN):
            encodedData.append(EMPTYBYTE)
        y_bytes = public_key_y.to_bytes()
        for i in range(NOCOMPRESSEDLEN - len(y_bytes), NOCOMPRESSEDLEN):
            encodedData[i] = y_bytes[i - NOCOMPRESSEDLEN + len(y_bytes)]
    x_bytes = public_key_x.to_bytes()
    l = len(x_bytes)
    for i in range(COMPRESSEDLEN - l, COMPRESSEDLEN):
        encodedData[i] = x_bytes[i - COMPRESSEDLEN + l]

    if is_compressed:
        if public_key_y % 2 == 0:
            encodedData[0] = COMPEVENFLAG
        else:
            encodedData[0] = COMPODDFLAG
    else:
        encodedData[0] = NOCOMPRESSEDFLAG
    return bytes(encodedData)


# common convert

if __name__ == '__main__':
    pass
