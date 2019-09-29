#!/usr/bin/env python
# encoding: utf-8

"""
@author: Bocheng.Zhang
@license: MIT
@contact: bocheng0000@gmail.com
@file: transaction.py
@time: 2019-07-04 14:44
"""
# import binascii
import ecdsa
import hashlib
import random
import struct

from wallet import payload as p
from utility import encoding, util
from utility.serialize import Serialize
from utility.secp256r1 import secp256r1_generator as generator, secp256r1_curve as curve, secp256r1_p as secp_p, \
    secp256r1_n as secp_n

ELA_ASSETID = "a3d0eaa466df74983b5d7c543de6904f4c9418ead5ffd6d25814234a96db37b0"


class TxInput:
    def __init__(self, txid: str, index: int, sequence=0xffffffff):
        self.txid = txid
        self.index = index
        self.sequence = sequence

    def is_final(self):
        return self.sequence == 0xffffffff

    def serialize(self):
        data_list = []
        data_list.append(encoding.hexstring_to_bytes(self.txid))
        data_list.append(struct.pack("<H", self.index))
        data_list.append(struct.pack("<L", self.sequence))
        return b''.join(data_list)

    @staticmethod
    def serialize_size():
        return 38

    @staticmethod
    def unserialize(data):
        txid = data[:32]
        index = struct.unpack("<H", data[32:34])[0]
        sequence = struct.unpack("<L", data[34:38])[0]
        tx_input = TxInput(txid=txid, index=index, sequence=sequence)
        return tx_input, data[38:]

    def __str__(self):
        return '<\n\ttxid:{},\n\tindex={:04x},\n\tsequence={},\n\t>'.format(self.txid, self.index,
                                                                            self.sequence)


class TxOutput:
    def __init__(self, value: int, outputLock=0, address="", programHash="", assetID=ELA_ASSETID):
        assert value >= 0
        assert len(address) == 34 or len(programHash) == 42
        self.assetID = assetID
        self.value = value
        self.outputLock = outputLock
        if len(programHash) == 0:
            programHash = encoding.address_to_programhash(address)
        self.programHash = programHash

    def serialize(self):
        data_list = []
        data_list.append(encoding.hexstring_to_bytes(self.assetID))
        data_list.append(struct.pack("<Q", self.value))
        data_list.append(struct.pack("<L", self.outputLock))
        data_list.append(encoding.hexstring_to_bytes(self.programHash, reverse=False))
        return b''.join(data_list)

    @staticmethod
    def serialize_size():
        return 65

    @staticmethod
    def unserialize(data):
        asset_id = encoding.bytes_to_hexstring(data[:32])
        value = struct.unpack("<Q", data[32:40])[0]
        output_lock = struct.unpack("<L", data[40:44])[0]
        program_hash = data[44:65].decode()
        tx_output = TxOutput(assetID=asset_id, value=value, outputLock=output_lock, programHash=program_hash)
        return tx_output, data[65:]

    def __str__(self):
        return '<\n\tassetID:{},\n\tvalue:{},\n\toutputLock:{},\n\tprogramHash:{},\n\t>'.format(
            self.assetID,
            self.value,
            self.outputLock,
            self.programHash)


# AttributeUsage
AttributeUsage_Nonce = 0x00
AttributeUsage_Script = 0x20
AttributeUsage_Memo = 0x81
AttributeUsage_Description = 0x90
AttributeUsage_DescriptionUrl = 0x91
AttributeUsage_Confirmations = 0x92


def isValidAttribute(attr):
    if attr in [AttributeUsage_Nonce, AttributeUsage_Script, AttributeUsage_Memo, AttributeUsage_Description,
                AttributeUsage_DescriptionUrl, AttributeUsage_Confirmations]:
        return True
    else:
        return False


class Attribute:
    def __init__(self, usage, data):
        self.usage = usage
        self.data = data

    def serialize(self):
        data_list = []
        data_list.append(struct.pack('B', self.usage))
        data_list.append(Serialize.serialize_bytes(self.data))
        return b''.join(data_list)

    def serialize_size(self):
        len_data = len(self.data)
        return 1 + Serialize.serialize_variable_int_size(len_data) + len_data

    @staticmethod
    def unserialize(data):
        usage = data[0]
        if not isValidAttribute(usage):
            raise ValueError('Attribute is invalid.')
        attribute_data, data = Serialize.unserialize_bytes(data[1:])
        attribute = Attribute(usage=usage, data=attribute_data)
        return attribute, data

    def __str__(self):
        return '<\n\t\tusage:{},\n\t\tdata:{},\n\t>'.format(self.usage, self.data.hex())


class Program:
    def __init__(self, parameter: str, code: str):
        self.parameter = parameter
        self.code = code

    def serialize(self):
        data_list = []
        data_list.append(Serialize.serialize_bytes(encoding.hexstring_to_bytes(self.parameter, reverse=False)))
        data_list.append(Serialize.serialize_bytes(encoding.hexstring_to_bytes(self.code, reverse=False)))
        return b''.join(data_list)

    def serialize_size(self):
        len_parameter = len(self.parameter)
        len_code = len(self.code)
        return Serialize.serialize_variable_int_size(len_parameter) + len_parameter + \
               Serialize.serialize_variable_int_size(len_code) + len_code

    @staticmethod
    def unserialize(data):
        len_parameter, data = Serialize.unserialize_variable_int(data)
        parameter = data[:len_parameter]
        len_code, data = Serialize.unserialize_variable_int(data[len_parameter:])
        code = data[:len_code]
        program = Program(parameter=parameter.hex(), code=code.hex())
        return program, data[len_code:]

    def __str__(self):
        return 'parameter:{},\n\tcode:{}\n'.format(self.parameter.hex(), self.code.hex())


# Transaction Type
COINBASE = 0x00
REGISTERASSET = 0x01
TRANSFERASSET = 0x02
RECORD = 0x03
DEPLOY = 0x04
SIDECHAINPOW = 0x05
RECHARGETOSIDECHAIN = 0x06
WITHDRAWFROMSIDECHAIN = 0x07
TRANSFERCROSSCHAINASSET = 0x08

REGISITERPRODUCER = 0x09
CANCELPRODUCER = 0x0a
UPDATEPRODUCER = 0x0b
RETURNDEPOSITCOIN = 0x0c
ACTIVATEPRODUCER = 0x0d

ILLEGALPROPOSALEVIDENCE = 0x0e
ILLEGALVOTEEVIDENCE = 0x0f
ILLEGALBLOCKEVIDENCE = 0x10
ILLEGALSIDECHAINEVIDENCE = 0x11
INACTIVEARBITRATORS = 0x12
UpdateVersion = 0x13


class Transaction:
    def __init__(self, tx_type=TRANSFERASSET, payload_version=0x00, payload=None, attributes=[], inputs=[], outputs=[],
                 lock_time=0, programs=[]):
        self.tx_type = tx_type
        self.payload_version = payload_version
        self.payload = p.PayloadTransferMainchain() if payload is None else payload
        self.attributes = attributes
        self.inputs = [] if inputs is None else inputs
        self.outputs = [] if outputs is None else outputs
        self.lock_time = lock_time
        self.programs = [] if programs is None else programs

    def hash(self):
        data = self.serialize_unsigned()
        return encoding.double_sha256(data)

    def is_coinbase(self):
        return len(self.inputs) == 1 and self.inputs[0].txid == (b'\x00' * 32) and self.inputs[
            0].index == 0xffff and self.inputs[0].sequence == 0xffffffff

    # Todo: test check function
    def check(self):
        if self.is_coinbase():
            return True
        else:
            result = []
            for program in self.programs:
                result.append(program.check())
            return all(result)

    def serialize_unsigned(self):
        data_list = []
        data_list.append(struct.pack('B', self.tx_type))
        data_list.append(struct.pack('B', self.payload_version))
        data_list.append(self.payload.serialize())
        data_list.append(Serialize.serialize_variable_int(len(self.attributes)))
        for attribute in self.attributes:
            data_list.append(attribute.serialize())

        data_list.append(Serialize.serialize_variable_int(len(self.inputs)))
        for _input in self.inputs:
            data_list.append(_input.serialize())

        data_list.append(Serialize.serialize_variable_int(len(self.outputs)))
        for output in self.outputs:
            data_list.append(output.serialize())
        data_list.append(struct.pack("<L", self.lock_time))
        return b''.join(data_list)

    def serialize(self):
        data_list = []
        data_list.append(self.serialize_unsigned())
        data_list.append(Serialize.serialize_variable_int(len(self.programs)))
        for program in self.programs:
            data_list.append(program.serialize())
        return b''.join(data_list)

    def serialize_size(self):
        data_size = 0
        data_size += 2
        data_size += p.Payload.serialize_size(self.payload)
        count_attributes = len(self.attributes)
        data_size += Serialize.serialize_variable_int_size(count_attributes)
        for i in range(count_attributes):
            data_size += self.attributes[i].serialize_size()

        count_inputs = len(self.inputs)
        data_size += Serialize.serialize_variable_int_size(count_inputs) + count_inputs * TxInput.serialize_size()

        count_outputs = len(self.outputs)
        data_size += Serialize.serialize_variable_int_size(count_outputs) + count_outputs * TxOutput.serialize_size()

        data_size += 4
        count_programs = len(self.programs)
        data_size += Serialize.serialize_variable_int_size(count_programs)
        for i in range(count_programs):
            data_size += self.programs[i].serialize_size()
        return data_size

    @staticmethod
    def unserialize(data):
        tx_type = data[0]
        payload_version = data[1]
        payload, data = p.Payload.unserialize(data[2:], tx_type, payload_version)
        count_attribute, data = Serialize.unserialize_variable_int(data)
        attributes = []
        for i in range(count_attribute):
            attribute, data = Attribute.unserialize(data)
            attributes.append(attribute)

        num_inputs, data = Serialize.unserialize_variable_int(data)
        inputs = []
        for i in range(num_inputs):
            tx_input, data = TxInput.unserialize(data)
            inputs.append(tx_input)

        outputs = []
        num_outputs, data = Serialize.unserialize_variable_int(data)
        for i in range(num_outputs):
            tx_output, data = TxOutput.unserialize(data)
            outputs.append(tx_output)
        lock_time = struct.unpack("<L", data[:4])[0]

        count_program, data = Serialize.unserialize_variable_int(data[4:])
        programs = []
        for i in range(count_program):
            program, data = p.Program.unserialize(data)
            programs.append(program)
        tx = Transaction(tx_type=tx_type, payload_version=payload_version, payload=payload, attributes=attributes,
                         inputs=inputs, outputs=outputs, lock_time=lock_time, programs=programs)
        return tx, data

    def __str__(self):
        s = '<\n\t{},\n\t{},\n\t{},\n\t{},\n\t{},\n\t{},\n\t{},\n\t{}>'.format('type:{}'.format(self.tx_type),
                                                                               'payload version:{}'.format(
                                                                                   self.payload_version),
                                                                               'payload:{}'.format(self.payload),
                                                                               'attribute:[' + '\n\t'.join(
                                                                                   '\n\t{}'.format(i) for i in
                                                                                   self.attributes) + ']',
                                                                               'input:[' + ''.join(
                                                                                   '\n\t{}'.format(i) for i in
                                                                                   self.inputs) + ']',
                                                                               'output:[' + ''.join(
                                                                                   '\n\t{}'.format(i) for i in
                                                                                   self.outputs) + ']',
                                                                               'lock time:{}'.format(self.lock_time),
                                                                               'program:[' + '\n\t'.join(
                                                                                   '\n\t{}'.format(i) for i in
                                                                                   self.programs) + ']'
                                                                               )
        return util.replace_angle_brackets(s)


def ecdsa_verify(private_key: str, data: str, signature: str):
    if len(signature) != 128:
        return False
    private_key = bytes.fromhex(private_key)
    data = bytes.fromhex(data)
    signature = bytes.fromhex(signature)

    r = int.from_bytes(signature[:32], byteorder="big", signed=False)
    s = int.from_bytes(signature[32:], byteorder="big", signed=False)
    data_hash = hashlib.sha256(data).digest()

    secret = int.from_bytes(private_key, byteorder="big", signed=False)
    digest = int.from_bytes(data_hash, byteorder="big", signed=False)
    pub_key = ecdsa.ecdsa.Public_key(generator, generator * secret)
    print(type(pub_key), pub_key)
    sig = ecdsa.ecdsa.Signature(r, s)

    return pub_key.verifies(digest, sig)


def ecdsa_sign(private_key: str, data):
    if isinstance(data, str):
        data = bytes.fromhex(data)
    private_key = bytes.fromhex(private_key)
    data_hash = hashlib.sha256(data).digest()

    n = generator.order()

    randrange = random.SystemRandom().randrange
    secret = int.from_bytes(private_key, byteorder="big", signed=False)
    digest = int.from_bytes(data_hash, byteorder="big", signed=False)
    pub_key = ecdsa.ecdsa.Public_key(generator, generator * secret)
    pri_key = ecdsa.ecdsa.Private_key(pub_key, secret)

    signature = pri_key.sign(digest, randrange(1, n))
    r = signature.r.to_bytes(32, byteorder="big", signed=False)
    s = signature.s.to_bytes(32, byteorder="big", signed=False)

    return struct.pack("B", len(r + s)) + r + s
