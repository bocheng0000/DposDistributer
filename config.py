#!/usr/bin/env python
# encoding: utf-8

"""
@author: Bocheng.Zhang
@license: MIT
@contact: bocheng0000@gmail.com
@file: config.py
@time: 2019-07-02 21:44
"""

########## The parameters about the distribution rule. Please adjust this part of the parameters according to your distribution strategy. ##########
distribute_round = 20  # DPOS reward distribution cycle
distribution_percent = 1  # Distribution ratio of DPOS rewards, 1 = 100%
investorEquity = 0  # Node investor's equity
investorCount = 0  # The number of the investors
investorsVotes = investorEquity * investorCount  # The total quity of the node investors which is used in the reward calculation

tx_fee = 10 ** 4  # The transaction fee
operating_costs = 0  # cost for server, it will be deducted in each round, in sela

########## Need to modify the parameters of the node before the first run ##########
dposRewardAddress = "ElaAddress"  # The dpos node's reward address
ownerPublicKey = "OwnerPublicKey"  # The owner public key of the dpos node
MsgForMemo = "Thank you for your support"
node_url = "localhost"
node_rpc = 20336
rpc_user = ""  # Enter the RPC User in config.json
rpc_password = ""  # Enter the RPC Password in config.json

# account for distribution.
address = "ElaAddresses0000000000000000000000"  # The address used to distribute the dpos reward
public_key = "Public Key"  # The public key of the address above
private_key = "Private Key"  # The private key of the address above

investor_a = ""  # The inverstors' addresses used to receive the reward.

# If there are more than one investor, just add investor's address and his investorEquity to the dict below
investors = {investor_a: {"Votes": investorEquity, "Txid": []}}
ignoreAddress = ["ELANULLXXXXXXXXXXXXXXXXXXXXXYvs3rr"]  # The votes from this address list will be ignored.

########## The parameters which shouldn't be modified ##########
H2 = 402680  # This is the height of the DPOS consensus, please do not modify
api_mist_url = "https://api-wallet-ela.elastos.org"  # api server's domain name
distribution_record_file = "distribute_record.csv"  # The file for the distribution record
dpos_record_file = "dpos_record.csv"  # The file for the dpos reward record
log_path = "logs"  # The configuration for log
tx_path = "txs"  # The path to store the transaction
Memo_Prefix = "type:text,msg:"
