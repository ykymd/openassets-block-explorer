# -*- coding: utf-8 -*-
import subprocess
import sys
from bitcoinrpc.authproxy import AuthServiceProxy
import configparser

from signal import signal, SIGPIPE, SIG_DFL
signal(SIGPIPE, SIG_DFL)

GENESIS_BLOCK = "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"
GENESIS_BLOCK_TESTNET = "00000000b873e79784647a6c82962c70d228557d24a747ea4d1b8bbe878e1206"

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read("config.ini")

    blockHash = GENESIS_BLOCK
    if "rpcsetting" in config and "testnet" in config["rpcsetting"] and config["rpcsetting"]["testnet"] is "1":
        blockHash = GENESIS_BLOCK_TESTNET
    if len(sys.argv) > 1:
        blockHash = sys.argv[1]
    elif "crawl" in config and "nextblock" in config["crawl"]:
        blockHash = config["crawl"]["nextblock"]
    num = 100
    if len(sys.argv) > 2:
        num = int(sys.argv[2])
    if len(blockHash) != 0:
        hostURL = "http://{0}:{1}@{2}:{3}".format(
            config["rpcuser"]["rpcid"],
            config["rpcuser"]["rpcpass"],
            config["rpcsetting"]["host"],
            config["rpcsetting"]["port"]
        )
        print(hostURL)
        rpcConnection = AuthServiceProxy(hostURL)
        # for i in range(num):
        while(True):
            print(blockHash)
            block = rpcConnection.getblock(blockHash)
            blockHash = block["nextblockhash"]
            res = subprocess.run(
                ["python", "getdistribution.py", blockHash], stdout=subprocess.PIPE)
            sys.stdout.buffer.write(res.stdout)
            try:
                config.set("crawl", 'nextblock', blockHash)
                config.write(open("config.ini", 'w'))
            except Exception as e:
                print >> sys.stderr, 'Error: Could not write to config file: %s' % e
                sys.exit(1)
