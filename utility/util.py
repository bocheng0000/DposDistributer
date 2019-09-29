#!/usr/bin/env python
# encoding: utf-8

"""
@author: Bocheng.Zhang
@license: MIT
@contact: bocheng0000@gmail.com
@file: util.py
@time: 2019-07-02 21:39
"""

from copy import deepcopy
import linecache
import logging
import os
import time

import config as cf
from utility import request
from wallet import transaction as t


# OS
def check_dir(dir: str):
    """
    Check if the dir exists. If the dir does not exist, create a file.
    :param filename: the path of the dir
    :return:None
    """
    if not os.path.exists(dir):
        os.makedirs(dir)


def check_file(filename: str):
    """
    Check if the file exists. If the file does not exist, create a file.
    :param filename: the name of the file
    :return:None
    """
    if not os.path.exists(filename):
        os.system(f"touch {filename}")


# log
DEBUG = 0
INFO = 1
WARNING = 2
ERROR = 3
CRITICAL = 4

check_dir(cf.log_path)
log_file = f"{cf.log_path}/dposreward_{time.strftime('%m%d%H%M', time.gmtime(time.time()))}.log"
logging.basicConfig(filename=log_file, filemode="a", format="%(asctime)s %(name)s:%(levelname)s:%(message)s",
                    datefmt="%a, %d %b %Y %H:%M:%S", level=logging.INFO)


def feedback(content: str, level=INFO, module="UTL"):
    """
    record the content in the log files and print on the screen
    :param content: The information needs feedback.
    :param level: The log level
    :param module: The name of the module that called the logger
    :return: None
    """
    logger = logging.getLogger(module)
    print(content)
    if level == DEBUG:
        logger.debug(content)
    elif level == INFO:
        logger.info(content)
    elif level == WARNING:
        logger.warning(content)
    elif level == ERROR:
        logger.error(content)
    elif level == CRITICAL:
        logger.critical(content)


def getVotersByHeight(ownerPb: str, hei: int) -> dict:
    # get the information of voters at the specified height for the owner
    _votersInfo = request.get_voters_by_height(ownerPublickey=ownerPb, height=hei)

    if "" in cf.investors.keys():
        voters = {}
    else:
        voters = deepcopy(cf.investors)
    if _votersInfo is not None:
        for _voter in _votersInfo:
            _add = _voter["Address"]
            if _add in cf.ignoreAddress:
                feedback(content=f"{_add} is in the blacklist.", level=WARNING)
                continue
            elif len(_add) != 34:
                feedback(content=f"{_add} is not standard address.", level=WARNING)
                continue

            _value = strElaToIntSela(_voter["Value"])
            _txid = _voter["Txid"]
            _producerPb = _voter["Producer_public_key"]
            _txType = _voter["Vote_type"]
            if _producerPb == ownerPb and _txType == "Delegate":
                if _add not in voters.keys():
                    # 该地址第一次被统计，或在投票统计中仅出现一次
                    voters[_add] = {"Votes": _value, "Txid": [_txid]}
                else:
                    # 该地址使用不同的utxo同时进行了多次投票，或者接口结果有bug
                    if _txid not in voters[_add]["Txid"]:
                        voters[_add]["Votes"] += _value
                        voters[_add]["Txid"].append(_txid)
                    else:
                        feedback(content="Error: API_MISC return Duplicate txid", level=ERROR)
                        feedback(content=f"txid:{_txid}", level=ERROR)
                        feedback(content=f"voter: add[{_add}] {voters[_add]}", level=ERROR)
        return voters
    else:
        feedback(content=f"getVotersByHeight failed!{ownerPb},{hei}", level=ERROR)
        return None


def getTotalVotesByHeight(ownerPb: str, hei: int) -> int:
    producers = request.get_total_votes_by_height(height=hei)
    if producers is not None:
        for _p in producers:
            _pb = _p["Ownerpublickey"]
            if _pb == ownerPb:
                return strElaToIntSela(_p["Value"])
        return None
    else:
        feedback(content="getTotalVotesByHeight failed!", level=ERROR)
        return None


def getCoinbaseByHeight(hei: int) -> dict:
    """
    get the coinbase transaction at the specified height
    :param hei: the specified height
    :return: A dict representing the block data.
    """

    # get the block at the specified height
    _block = request.get_block_by_height(height=hei)
    # get all transactions in the block
    _txs = _block["tx"]

    # The coinbase transaction must be the first transaction and type 0
    _coinbase = _txs[0]
    assert _coinbase["type"] == 0
    return _coinbase


def getCoinbaseOutput(hei: int) -> list:
    """
    return the coinbase's outputs at the specified height
    :param hei: the specified height
    :return: coinbase's outputs
    """
    _coinbase = getCoinbaseByHeight(hei)
    return _coinbase["vout"]


def getDposRewardByHeight(hei: int, add=cf.dposRewardAddress) -> int:
    """
    get the specified node's dpos reward at the specified height
    :param hei: the specified height of the dpos reward
    :param add: the address of the specified dpos node
    :return: the reward in sela

        If the node's address is not in the coinbase's outputs, 0 is returned.
    """

    # get the coinbase's output at the specified height
    _vouts = getCoinbaseOutput(hei)
    for _vout in _vouts:
        # if the dpos node's address is in coinbase's outputs, convert the output's value to sela and return
        if _vout["address"] == add:
            return strElaToIntSela(_vout["value"])
    feedback(content=f"There is no dpos reward for {add} in block[{hei}]", level=WARNING)
    return 0


def caleRewardByVoter(amount: int, voters: dict, totalVotes: int) -> dict:
    validVotes = totalVotes + cf.investorsVotes
    _rewardPerVote = amount / validVotes

    rewards = {}
    for _add in voters.keys():
        if _add in cf.ignoreAddress:
            feedback(content=f"Address[{_add}] is ignored.")
            continue
        else:
            _vote = voters[_add]["Votes"]
            rewards[_add] = _vote * _rewardPerVote
    return rewards


def calDistributionAmount(receiptor: dict) -> int:
    amount = 0
    for _, value in receiptor.items():
        amount += value
    return amount


def SelaToEla(value: int) -> str:
    """
    convert sela to ela
    :param value: sela, 1 ela = 10^8 sela
    :return: a string representing the amount in ela
    """
    value = int(value)
    front = int(value / 100000000)
    after = value % 100000000
    return str(front) + "." + "0" * (8 - len(str(after))) + str(after)


def strElaToIntSela(value: str) -> int:
    dotLocation = value.find(".")
    if dotLocation == -1:
        value_sela = int(value) * 100000000
        return value_sela
    else:
        front = value[:dotLocation]
        end = value[dotLocation + 1:]
        assert len(end) <= 8
        end = end + "0" * (8 - len(end))
        value_sela = int(front) * 100000000 + int(end)
        return value_sela


# utility for time
def get_block_date(height: int) -> str:
    blockInfo = request.get_block_by_height(height=height)
    return timestamp_to_data(blockInfo["time"])


def timestamp_to_data(timestamp: int) -> str:
    time_gm = time.gmtime(timestamp)
    return time.strftime("%Y-%m-%d", time_gm)


# utility for transaction
def gen_intput_by_utxo(utxos: dict):
    amount = 0
    inputs = []
    for _utxo in utxos:
        amount += strElaToIntSela(_utxo["amount"])
        _input = t.TxInput(txid=_utxo["txid"], index=_utxo["vout"])
        inputs.append(_input)
    return inputs, amount


def gen_output_by_receiver(receivers: dict):
    if len(receivers.keys()) == 0:
        return None
    else:
        outputs = []
        for _add in receivers.keys():
            _value = int(receivers[_add])
            _output = t.TxOutput(address=_add, value=_value)
            outputs.append(_output)
        return outputs


def get_last_distribution_record():
    """
    Get the last record of the dpos reward distribution.
    :return:
        _round: the index of the dpos round
        _height: the height of the last dpos reward distribution
        _amount: the amount of the dpos reward distribution
        _txid: the hash of the reward distribution transaction
        _fee: the fee of the reward distribution transaction

        If there is no record, 0 is returned.
    """
    check_file(cf.distribution_record_file)
    _record = get_last_line(cf.distribution_record_file).split(",")
    if len(_record) == 1:
        _round = 0
        _height = 0
        _amount = ""
        _txid = ""
        _fee = 0
    else:
        _round = int(_record[0])
        _height = int(_record[1])
        _amount = _record[2]
        _txid = _record[3]
        _fee = int(_record[4])
    return _round, _height, _amount, _txid, _fee


def getDposRecord(firstRound: int, lastRound: int) -> dict:
    """
    get the dpos records from 'dpos_record.csv'
    :param firstRound: The starting  round
    :param lastRound: The ending round
    :return: A dict
        key: the round
        value: dposHeight, voteHeight and the amount of the dpos reward
    """
    _lines = linecache.getlines(cf.dpos_record_file)[firstRound - 1:lastRound]
    _result = {}
    for _line in _lines:
        _record = _line.strip('\n').split(",")
        _result[int(_record[0])] = {"dposHeight": int(_record[1]), "voteHeight": int(_record[2]),
                                    "reward": int(_record[3])}
    return _result


def get_last_dpos_record():
    """
    read the last dpos record from 'dpos_record.csv' and return
    :return:
        the count of round
        the height of the last dpos reward
        the height of the last round voting

        If the program doesn't be run before, the return will be '0,0,0'
    """
    check_file(cf.dpos_record_file)
    _record = get_last_line(cf.dpos_record_file).split(",")
    if len(_record) == 1:
        return 0, 0, 0
    else:
        return int(_record[0]), int(_record[1]), int(_record[2])


def update_dpos_record(currentHeight: int):
    """
    write the new dpos reward records to the 'dpos_record.csv'
    :param currentHeight: The height of the best block
    :return: None
    """

    # get the last dpos reward record from 'dpos_record.csv'
    _round, _lastDposHeight, _lastVoteHeight = get_last_dpos_record()

    if _round == 0 and _lastDposHeight == 0 and _lastVoteHeight == 0:
        feedback(content="No dpos record is found, the first two records will be added manully")
        # write_dpos_record("round", "dposHeight", "voteHeight", "reward")
        write_dpos_record(1, cf.H2 + 36, cf.H2 - 361, getDposRewardByHeight(hei=cf.H2 + 36))
        write_dpos_record(2, cf.H2 + 72, cf.H2 - 1, getDposRewardByHeight(hei=cf.H2 + 72))
        _round, _lastDposHeight, _lastVoteHeight = get_last_dpos_record()

    if currentHeight - _lastDposHeight < 36:
        feedback(content="Less than 36 blocks from last dpos height, no dpos record needs to be updates.")
        return
    else:
        feedback(content="Start to update dpos record")
        _lastHeight = _lastDposHeight
        _lastVote = _lastVoteHeight
        _forceChangeState = False
        for _hei in range(_lastDposHeight + 1, currentHeight):
            # check each block after the last dpos height to find the dpos reward output
            _vouts = getCoinbaseOutput(_hei)
            if len(_vouts) < 3:
                # If the outputs contains dpos reward, the number of outputs must not be less than 3.
                continue
            else:
                feedback(content=f"Check Block[{_hei}]'s output")
                if _hei - _lastHeight < 36:
                    # If the interval between _hei(the height being checked) and  _lastHeight(last dpos reward height
                    # in the record) is less than 36, then ForceChange is triggered.
                    _round += 1
                    _reward = getDposRewardByHeight(hei=_hei)
                    _lastVote = _lastHeight - 36 - 1
                    _lastHeight = _hei
                    # If ForceChange is triggered, the height of the votie is the previous one of the dpos reward height.
                    _forceChangeState = True
                    write_dpos_record(_round, _lastHeight, _lastVote, _reward)
                    feedback(content=f"There is a ForceChange at {_hei}", level=WARNING)

                elif _hei - _lastHeight == 36 and _forceChangeState:
                    # There is a normal dpos round after the ForceChange and the height of the vote is the same as
                    # previous round.
                    _round += 1
                    _reward = getDposRewardByHeight(hei=_hei)
                    _lastVote = _lastHeight - 1
                    _lastHeight = _hei
                    write_dpos_record(_round, _lastHeight, _lastVote, _reward)
                    # Restore the ForceChange flag to false
                    _forceChangeState = False
                    feedback(content=f"Restore the ForceChange flag to False at {_hei}", level=WARNING)

                elif _hei - _lastHeight == 36:
                    # This is the normal dpos round.
                    _round += 1
                    _reward = getDposRewardByHeight(hei=_hei)
                    _lastVote = _hei - 73
                    _lastHeight = _hei
                    write_dpos_record(_round, _lastHeight, _lastVote, _reward)
                else:
                    # There are some dirty data on the chain that there are more than 36 blocks without dpos reward.
                    feedback(content="There is more than 36 blocks with no dpos reward!", level=ERROR)
                    _round += 1
                    _reward = getDposRewardByHeight(hei=_hei)
                    _lastVote = _hei - 73
                    _lastHeight = _hei
                    write_dpos_record(_round, _lastHeight, _lastVote, _reward)


def write_distribution_record(round: int, hei: int, amount: str, txid: str, fee: int):
    # 将收益分配记录写入文件，amount单位为ela，fee单位为sela
    _record = f"{round},{hei},{amount},{txid},{fee}\n"
    write_record(cf.distribution_record_file, _record)
    feedback(
        content=f"Update DistributionRecord: Round[{round}] DposHeight[{hei} Txid[{txid}] Amount:{amount}] fee:{fee}")


def write_dpos_record(round, dposHeight, voteHeight, reward):
    """
    Write the record of the node dpos reward to the file.
    :param round: The index of the dpos round.
    :param dposHeight: The height of the dpos reward.
    :param voteHeight: The height of the vote
    :param reward: The amount of the specificed dpos node's reward.
    :return: None
    """
    _record = f"{round},{dposHeight},{voteHeight},{reward}\n"
    write_record(cf.dpos_record_file, _record)
    feedback(
        content=f"Update DposRecord: Round[{round}] DposHeight[{dposHeight}] VoteHeight[{voteHeight}] Reward[{reward}]")


# utility for file
def write_record(file, content):
    """
    Write the content to the file
    :param file: The file used to record the content.
    :param content: The content needed to be recorded.
    :return: None
    """
    with open(file, "a") as f_out:
        f_out.write(content)


def get_last_line(inputfile):
    """
    Get the content of the last line of the 'inputfile'
    :param inputfile: The whole path of the file.
    :return: The content of the last line.
    """
    filesize = os.path.getsize(inputfile)
    blocksize = 1024
    with open(inputfile, 'r') as dat_file:
        last_line = ""
        if filesize > blocksize:
            maxseekpoint = (filesize // blocksize)
            dat_file.seek((maxseekpoint - 1) * blocksize)
        elif filesize:
            dat_file.seek(0, 0)
        lines = dat_file.readlines()
        if lines:
            last_line = lines[-1].strip()
    return last_line


def write_tx_to_file(rawtx: str, txid: str):
    """
    record the data of the transaction in a file named by txid
    :param rawtx: The data of the transaction
    :param txid: The hash of the transaction which will be the file's name.
    :return: None
    """
    check_dir(cf.tx_path)
    file_name = f"{cf.tx_path}/{timestamp_to_data(time.time())}_{txid}.tx"
    with open(file_name, "w") as tx_f:
        tx_f.write(rawtx)
        feedback(content=f"txid[{txid}] is recorded.")


def replace_angle_brackets(s):
    return s.replace('<', '{').replace('>', '}').replace('}\n\t{', '},\n\t{').replace('}{', '},\n\t{').replace('\n',
                                                                                                               '').replace(
        '\t', "")


if __name__ == '__main__':
    pass
