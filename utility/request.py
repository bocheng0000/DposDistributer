#!/usr/bin/env python
# encoding: utf-8

"""
@author: Bocheng.Zhang
@license: MIT
@contact: bocheng0000@gmail.com
@file: request.py
@time: 2019-07-03 06:37
"""

import requests
from retrying import retry

import config as cf
from utility import util

api_votes_height = "/api/1/dpos/producer/"
api_rank_height = "/api/1/dpos/rank/height/"


def post_request(ip: str, port: int, method, params={}, user="", password=""):
    try:
        resp = requests.post("http://" + ip + ":" + str(port), json={"method": method, "params": params},
                             headers={"content-type": "application/json"},
                             auth=requests.auth.HTTPBasicAuth(cf.rpc_user, cf.rpc_password))
        if resp.status_code == 200:
            return resp.json()
        else:
            util.feedback(content=resp.status_code, level=util.WARNING, module="RPC")
            return None
    except requests.exceptions.RequestException as e:
        util.feedback(content=e.__str__(), level=util.WARNING, module="RPC")
        return None


@retry(stop_max_attempt_number=5)
def get_block_height(url=cf.node_url, port=cf.node_rpc, user="", password=""):
    resp = post_request(url, port, "getcurrentheight", params={}, user=user, password=password)
    if resp is not None:
        return resp["result"]
    else:
        return resp


@retry(stop_max_attempt_number=5)
def get_block_by_height(url=cf.node_url, port=cf.node_rpc, height=0, user="", password=""):
    resp = post_request(url, port, "getblockbyheight", params={"height": height}, user=user, password=password)
    if resp is not None:
        return resp["result"]
    else:
        return resp


@retry(stop_max_attempt_number=5)
def get_balance(address: str, url=cf.node_url, port=cf.node_rpc, user="", password=""):
    if len(address) != 34:
        return None
    resp = post_request(url, port, "getreceivedbyaddress", params={"address": address}, user=user, password=password)
    if resp is not None:
        return resp["result"]
    else:
        return resp


@retry(stop_max_attempt_number=5)
def get_utxos_by_amount(address: str, amount: str, url=cf.node_url, port=cf.node_rpc, user="", password=""):
    if len(address) != 34:
        return None
    resp = post_request(url, port, "getutxosbyamount", params={"address": address, "amount": amount}, user=user,
                        password=password)
    if resp is not None:
        return resp["result"]
    else:
        return resp


@retry(stop_max_attempt_number=5)
def send_tx(raw_tx: str, url=cf.node_url, port=cf.node_rpc, user="", password=""):
    resp = post_request(url, port, "sendrawtransaction", params={"data": raw_tx}, user=user, password=password)
    if resp is not None:
        return resp["result"]
    else:
        return resp


@retry(stop_max_attempt_number=5)
def get_tx(tx_id: str, url=cf.node_url, port=cf.node_rpc, user="", password=""):
    resp = post_request(url, port, "getrawtransaction", params={"txid": tx_id, "verbose": True}, user=user,
                        password=password)
    if resp is not None:
        return resp["result"]
    else:
        return resp


def get_request(url: str):
    try:
        resp = requests.get(url=url)
        if resp.status_code == 200:
            return resp.json()
        else:
            util.feedback(content=resp.status_code, level=util.WARNING, module="RPC")
            return None
    except requests.exceptions.RequestException as e:
        util.feedback(content=e.__str__(), level=util.WARNING, module="RPC")
        return None


@retry(stop_max_attempt_number=5)
def get_voters_by_height(ownerPublickey: str, height: int):
    _url_request = cf.api_mist_url + api_votes_height + ownerPublickey + "/height/" + str(height)
    resp = get_request(_url_request)
    if resp is not None:
        return resp["result"]
    else:
        return resp


@retry(stop_max_attempt_number=5)
def get_total_votes_by_height(height: int):
    _url_request = cf.api_mist_url + api_rank_height + str(height)
    resp = get_request(_url_request)
    if resp is not None:
        return resp["result"]
    else:
        return resp
