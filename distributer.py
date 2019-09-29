#!/usr/bin/env python
# encoding: utf-8

"""
@author: Bocheng.Zhang
@license: MIT
@contact: bocheng0000@gmail.com
@file: distributer.py
@time: 2019-07-02 21:31
"""

import random
import time

import config as cf
from utility.util import DEBUG, WARNING, ERROR
from wallet import transaction as t
from utility import util, request, encoding


def distributeReward(lastDistributeRound: int, lastDistributeHeight: int):
    """
    Calculate the vote for each address and create a transaction to distribute the dpos reward based on that situation.
    :param lastDistributeRound: The index of the dpos reward distribution round
    :param lastDistributeHeight: The height of the last dpos reward distribution
    :return: None
    """
    # 1. Calculate the distribution of reward per round
    # key: the index of the reward round
    rewardInRound = {}
    # The total amount of the dpos reward
    rewardTotal = 0

    # The first dpos round needed to be distributed in this time
    firstDposRound = lastDistributeRound * cf.distribute_round + 1
    # The last dpos round needed to be distributed in this time
    lastDposRound = firstDposRound + cf.distribute_round - 1

    util.feedback(content=f"The DPOS Round from[{firstDposRound}] to [{lastDposRound}] will be calculated.",
                  module="DPS")

    # fetch the dpos reward records from 'dpos_record.csv'
    dposRecord = util.getDposRecord(firstDposRound, lastDposRound)
    util.feedback(content=dposRecord.__str__(), module="DPS")

    # Calculate the block range for this dpos reward distribution
    firstBlock = lastDistributeHeight
    lastBLock = dposRecord[lastDposRound]["dposHeight"] - 1
    distributionMsg = "Height[{} ~ {}] {}".format(firstBlock, lastBLock, util.get_block_date(lastBLock))
    util.feedback(content=f"Distribution Message:[{distributionMsg}]", module="DPS")

    for i in range(firstDposRound, lastDposRound + 1):
        _record = dposRecord[i]
        _amount = _record["reward"]
        _rewardHeight = _record["dposHeight"]
        _voterHeight = _record["voteHeight"]
        util.feedback(content=f"Round[{i}] Height[{_rewardHeight}]", module="DPS")
        util.feedback(content=f"DposReward is {util.SelaToEla(_amount)}", module="DPS")
        rewardTotal += _amount

        if _amount == 0:
            continue
        else:
            _amountToDistribute = (_amount - cf.operating_costs) * cf.distribution_percent
            _voters = util.getVotersByHeight(ownerPb=cf.ownerPublicKey, hei=_voterHeight)
            _totalVotes = util.getTotalVotesByHeight(ownerPb=cf.ownerPublicKey, hei=_voterHeight)

            if _voters is None:
                util.feedback(content="Get Voters' Information ERROR!", level=ERROR, module="DPS")
                exit(1)

            _receiptor = util.caleRewardByVoter(
                _amountToDistribute, _voters, totalVotes=_totalVotes)
            _distributionThisRound = util.calDistributionAmount(_receiptor)
            util.feedback(content=f"The amound of distribution is {util.SelaToEla(_distributionThisRound)}",
                          module="DPS")
            util.feedback(
                content=f"The percent of distribution is {_distributionThisRound / _amount}", module="DPS")
            util.feedback(content=f"Total votes is {util.SelaToEla(_totalVotes)}", module="DPS")
            rewardInRound[i] = _receiptor
            _receiptor = {}
    if rewardTotal == 0:
        util.feedback(content="There's no dpos reward in this distribution round, bye!", level=WARNING, module="DPS")
        util.write_distribution_record(round=lastDistributeRound + 1, hei=dposRecord[lastDposRound]["dposHeight"],
                                       amount="0", txid="xxxxxxxxxxxxxxxxxxxx", fee=0)
        exit(0)

    # 2. Summary of n rounds of reward distribution
    receivers = {}  # key:address,value:reward for vote
    for i in range(firstDposRound, lastDposRound + 1):
        if i not in rewardInRound.keys():
            continue
        for _add in rewardInRound[i].keys():
            util.feedback(content=f"round[{i}] {_add} reward {rewardInRound[i][_add]}", level=DEBUG, module="DPS")
            if _add not in receivers.keys():
                receivers[_add] = rewardInRound[i][_add]
            else:
                receivers[_add] += rewardInRound[i][_add]
    amountDistribute = 0
    addCount_temp = 0
    addressRemoved = []  # The list of addresses with no voting reward
    for _add in receivers.keys():
        addCount_temp += 1
        _value = int(receivers[_add])
        if _value == 0:
            addressRemoved.append(_add)
        else:
            receivers[_add] = _value
            amountDistribute += _value
            util.feedback(content=f"The total reward of ADD[{_add}] is {util.SelaToEla(_value)}", module="DPS")

    # Remove the addresses which have no voting reward
    for _add in addressRemoved:
        _value = receivers.pop(_add)
        util.feedback(content=f"{_add} has no voting reward [{_value}]", level=WARNING, module="DPS")
        assert _value < 1
        assert _add not in receivers.keys()

    amountDistribution_str = util.SelaToEla(amountDistribute)

    util.feedback(content="The amount of distribution:{}, the number of reward:{}".format(amountDistribution_str,
                                                                                          util.SelaToEla(rewardTotal)),
                  module="DPS")
    util.feedback(content=f"Distribution Percent:{amountDistribute / rewardTotal * 100}%", module="DPS")

    # 3. Create and sign the transaction
    _balance = request.get_balance(cf.address)
    util.feedback(content=f"ADD[{cf.address}]'s balance is {_balance}", module="DPS")
    if util.strElaToIntSela(_balance) < amountDistribute + cf.tx_fee:
        util.feedback(
            content="The balance of [{}:{}] is not enough to pay to voters in {}, require {}".format(cf.address,
                                                                                                     _balance,
                                                                                                     distributionMsg,
                                                                                                     util.SelaToEla(
                                                                                                         amountDistribute)),
            level=ERROR, module="DPS")
        exit(2)
    util.feedback(content="Preparing to build transaction", module="DPS")
    # Get utxo
    _utxos = request.get_utxos_by_amount(address=cf.address, amount=util.SelaToEla(amountDistribute + cf.tx_fee))

    # Create input
    inputs, utxoAmount = util.gen_intput_by_utxo(utxos=_utxos)

    # Create output
    _changeValue = utxoAmount - amountDistribute - cf.tx_fee
    outputs = util.gen_output_by_receiver(receivers)
    _changeOutput = t.TxOutput(address=cf.address, value=_changeValue)
    outputs.append(_changeOutput)

    # Disrupt tx_outputs order
    random.shuffle(outputs)

    # Create the transaction, include memo, attributes
    data_memo = f"{cf.MsgForMemo} {distributionMsg}".encode()
    attr = t.Attribute(usage=t.AttributeUsage_Memo, data=data_memo)
    tx_distribution = t.Transaction(inputs=inputs, outputs=outputs, attributes=[attr])
    txid_infile = encoding.bytes_to_hexstring(data=tx_distribution.hash(), reverse=True)
    util.feedback(content=f"Txid is [{txid_infile}] before signed.", module="DPS")

    # Sign the transactriron
    _code = encoding.get_code_from_pb(cf.public_key)
    _parameter = t.ecdsa_sign(cf.private_key, data=tx_distribution.serialize_unsigned()).hex()
    tx_distribution.programs = [t.Program(code=_code, parameter=_parameter)]

    # Serialize the transaction to get the raw data of the transaction
    raw_tx = tx_distribution.serialize().hex()
    util.write_tx_to_file(rawtx=raw_tx, txid=txid_infile)
    util.feedback(content=f"RawTx:[{raw_tx}]", level=DEBUG, module="DPS")

    # Update the distribution record before sending the transaction
    util.write_distribution_record(round=lastDistributeRound + 1, hei=dposRecord[lastDposRound]["dposHeight"],
                                   amount=amountDistribution_str, txid=txid_infile,
                                   fee=cf.tx_fee)

    # 4. Send transaction to the node
    txid_returned = request.send_tx(raw_tx=raw_tx)

    if txid_returned != txid_infile:
        util.feedback(content=f"Send TX ERROR!txid:[{txid_infile}], return:[{txid_returned}]", level=ERROR,
                      module="DPS")
        exit(2)
    else:
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()))
        _height = request.get_block_height()
        util.feedback(content=f"[{time_str}]Tx[{txid_returned}] is send to node, height[{_height}].", module="DPS")
    # 5. Waiting for a node to package the transaction
    util.feedback(content="Wait for wallet be confirmed.", module="DPS")
    while True:
        time.sleep(30)
        tx_details = request.get_tx(tx_id=txid_returned)
        if tx_details["confirmations"] > 0:
            _height = request.get_block_height()
            util.feedback(
                content=f"Tx[{txid_returned}] is confirmed at height[{_height}], the amount of distribution is {amountDistribution_str}.",
                module="DPS")
            time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()))
            util.feedback(content=f"[{time_str}]Distribution finished, bye", module="DPS")
            break


if __name__ == '__main__':
    currehtHeight = request.get_block_height()
    time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()))
    util.feedback(content=f"[{time_str}]current height:{currehtHeight}", module="DPS")

    # update the record of the node dpos reward
    util.update_dpos_record(currehtHeight)
    lastDposRound, lastDposHeight, lastVoteHeight = util.get_last_dpos_record()

    # get the last distribution record
    lastRecord = util.get_last_distribution_record()
    lastDistributionRound = lastRecord[0]
    lastDistributionHeight = lastRecord[1]
    lastDistributionAmount = lastRecord[2]

    if lastDistributionHeight == 0:
        lastDistributionHeight = cf.H2
        util.feedback(content="Never distribute the dpos reward to voters, we will distribute the fist round.",
                      module="DPS")
    else:
        util.feedback(content=f"last distribute height:{lastDistributionHeight}", module="DPS")
        util.feedback(content=f"last distribute amount:{lastDistributionAmount}", module="DPS")

    remainRound = lastDposRound / cf.distribute_round - lastDistributionRound
    if remainRound < 1:
        util.feedback(content="This distribution cycle has not ended, the distributer program will start later",
                      module="DPS")
        exit()
    else:
        util.feedback(content=f"The number of rounds need to be distributed is {int(remainRound)}", module="DPS")
        util.feedback(content=f"Now to distribute the next round begin after {lastDistributionHeight}", module="DPS")
        distributeReward(lastDistributionRound, lastDistributionHeight)
