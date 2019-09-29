#!/usr/bin/env python
# encoding: utf-8

"""
@author: Bocheng.Zhang
@license: MIT
@contact: bocheng0000@gmail.com
@file: payload.py
@time: 2019-07-04 20:23
"""

import struct

from wallet import transaction as t
from utility.serialize import Serialize


class Payload:
    @staticmethod
    def serialize(pl):
        return pl.serialize()

    @staticmethod
    def serialize_size(pl):
        return pl.serialize_size()

    @staticmethod
    def unserialize(data, tx_type, payload_version=0):
        if tx_type == t.COINBASE:
            return PayloadCoinBase.unserialize(data=data)
        elif tx_type == t.REGISTERASSET:
            return PayloadRegisterAsset.unserialize(data=data)
        elif tx_type == t.TRANSFERASSET:
            return PayloadTransferMainchain.unserialize(data=data)
        # elif tx_type == t.RECORD:
        #     return PayloadRecord.unserialize(data=data)
        # elif tx_type == t.SIDECHAINPOW:
        #     return PayloadSidechainPOW.unserialize(data=data)
        # elif tx_type == t.WITHDRAWFROMSIDECHAIN:
        #     return PayloadWithDrawFromSidechain.unserialize(data=data)
        # elif tx_type == t.TRANSFERCROSSCHAINASSET:
        #     return PayloadTransferCrosschainAsset.unserialize(data=data)

    @staticmethod
    def __str__(pl):
        return pl.__str__()


class PayloadCoinBase:
    def __init__(self, payload: bytes):
        self.payload = payload

    def serialize(self):
        return Serialize.serialize_bytes(self.payload)

    def serialize_size(self):
        len_payload = len(self.payload)
        return Serialize.serialize_variable_int_size(len_payload) + len_payload

    @staticmethod
    def unserialize(data):
        payload, data = Serialize.unserialize_bytes(data)
        coinbase_payload = PayloadCoinBase(payload=payload)
        return coinbase_payload, data

    def __str__(self):
        return self.payload.decode()


class PayloadRegisterAsset:
    def __init__(self, name: bytes, description: bytes, precision, asset_type, record_type, value, controller):
        self.name = name
        self.description = description
        self.precision = precision
        self.asset_type = asset_type
        self.record_type = record_type
        self.value = value
        self.controller = controller

    def serialize(self):
        data_list = []
        data_list.append(Serialize.serialize_bytes(self.name))
        data_list.append(Serialize.serialize_bytes(self.description))
        data_list.append(struct.pack("B", self.precision))
        data_list.append(struct.pack("B", self.asset_type))
        data_list.append(struct.pack("B", self.record_type))
        data_list.append(struct.pack("<Q", self.value))
        data_list.append(self.controller)
        return b''.join(data_list)

    def serialize_size(self):
        len_name = len(self.name)
        len_description = len(self.description)
        return Serialize.serialize_variable_int_size(len_name) + len_name + \
               Serialize.serialize_variable_int_size(len_description) + len_description + 3 + 8 + 21

    @staticmethod
    def unserialize(data: bytes):
        name, data = Serialize.unserialize_bytes(data)
        description, data = Serialize.unserialize_bytes(data)

        precision = data[0]
        # if precision <= b'0x00':
        if precision <= 0:
            raise ValueError('Precision is less than 0.')
        asset_type = data[1]
        # if asset_type <= b'0x00':
        if asset_type not in [0, 1]:
            raise ValueError('Asset type is less than 0.')
        record_type = data[2]
        value = struct.unpack("<Q", data[3:11])[0]
        controller = data[11:32]
        registerAssetPayload = PayloadRegisterAsset(name=name, description=description, precision=precision,
                                                    asset_type=asset_type, record_type=record_type, value=value,
                                                    controller=controller)
        return registerAssetPayload, data[32:]

    def __str__(self):
        return '<\n\tname:{},\n\tdescription:{},\n\tprecission:{},\n\tasset type:{},\n\trecord type:{},\n\tvalue:{},\n\tcontroller:{},\n\t>'.format(
            self.name.decode(), self.description.decode(), self.precision, self.asset_type, self.record_type,
            self.value, self.controller.hex())


class PayloadTransferMainchain:
    def __init__(self):
        self.payload = None

    def serialize(self):
        return b''

    def serialize_size(self):
        return 0

    @staticmethod
    def unserialize(data):
        return PayloadTransferMainchain(), data

    def __str__(self):
        return ""
