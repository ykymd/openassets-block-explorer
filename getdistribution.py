# -*- coding: utf-8 -*-
import configparser
import datetime
import sys

import MySQLdb
import oautil
from bitcoinrpc.authproxy import AuthServiceProxy

config = configparser.ConfigParser()
isTestnet = False


def getAddressFrom(conn, txrawdata):
    vin = txrawdata["vin"]
    # マイニング時のトランザクションを考慮した方が良い(in future)
    txin = vin[0]
    txid = txin["txid"]
    vout = txin["vout"]
    prevTx = conn.getrawtransaction(txid, 1)
    fromvout = prevTx["vout"]
    for txout in fromvout:
        if txout["n"] is vout:
            return txout["scriptPubKey"]["addresses"]
    return None


def parseTx(conn, txid):
    block = conn.getrawtransaction(txid, 1)
    vout = block["vout"]
    marker_output_index = 0
    num = 0
    payload = ""

    dbconn = MySQLdb.connect(
        user=config["dbuser"]["name"],
        passwd=config["dbuser"]["pass"],
        host=config["db"]["host"],
        db=config["db"]["dbname"])
    c = dbconn.cursor()

    hasMO, marker_output_index, num, payload = hasMarkerOutput(vout)

    if not hasMO:
        return

    addressFrom = getAddressFrom(conn, block)

    for i in range(num):
        if i is marker_output_index:
            continue
        try:
            amount, payload = oautil.leb128(payload)
            if amount == 0:
                continue
            o = vout[i]
            if "scriptPubKey" not in o:
                continue
            scriptPubKey = o["scriptPubKey"]
            if "addresses" not in scriptPubKey or "hex" not in scriptPubKey:
                continue
            addresses = scriptPubKey["addresses"]
            assetId, issueTxid = searchIssuranceTx(conn, dbconn, i, block,
                                                   amount)
            isIssuranceTx = True if block["txid"] is issueTxid else False
            print("txid: {0}".format(block["txid"]))
            print("出力{0}:".format(i))
            print("送信元: %s" % addressFrom)
            print("送信先: {0}".format(addresses))
            print("アセットID: {0}".format(assetId))
            print("送金量: {0}".format(amount))
            print("時刻: {0}".format(
                datetime.datetime.fromtimestamp(int(block["time"]))))
            print("")
            table = config["db"]["tablename"]
            sql = 'insert into ' + table + ' values (0, %s, %s, %s, %s, %s, %s, %s, %s, %s)'
            c.execute(sql, (block["txid"], addresses[0], addressFrom[0],
                            assetId, i, amount, issueTxid, block["time"], "1"
                            if isIssuranceTx else "0"))
        except Exception as e:
            print('== エラー内容 ==')
            print('type:' + str(type(e)))
            print('args:' + str(e.args))
            print('e自身:' + str(e))

    dbconn.commit()
    c.close()
    dbconn.close()


def parseBlock(blockHash):
    hostURL = "http://{0}:{1}@{2}:{3}".format(
        config["rpcuser"]["rpcid"], config["rpcuser"]["rpcpass"],
        config["rpcsetting"]["host"], config["rpcsetting"]["port"])
    rpcConnection = AuthServiceProxy(hostURL)
    block = rpcConnection.getblock(blockHash)
    tx = block["tx"]
    for txid in tx:
        parseTx(rpcConnection, txid)


def hasMarkerOutput(vout):
    hasMarkerOutput = False
    marker_output_index = -1
    num = 0
    payload = ""
    for i, o in enumerate(vout):
        if "4f41" == o["scriptPubKey"]["hex"][4:8]:
            marker_output_index = i
            # print("OA Version:" + o["scriptPubKey"]["hex"][8:12])
            payload = o["scriptPubKey"]["hex"][12:]
            num, payload = oautil.leb128(payload)
            hasMarkerOutput = True
            break
    return hasMarkerOutput, marker_output_index, num, payload


# 指定したtxのvoutの情報を取得する
def getTransactionAssetAmount(conn, txid, index):
    # print("txid: " + txid)
    # print("vout: " + str(index))
    tx = conn.getrawtransaction(txid, 1)
    vout = tx["vout"]
    # 色付けされてるかを確認
    hasMO, marker_output_index, num, payload = hasMarkerOutput(vout)
    if not hasMO:
        return False, 0, tx
    # print(len(vout))
    # print(marker_output_index)
    # 指定したvoutのasset量を取得する
    for i in range(len(vout)):
        if i is marker_output_index:
            continue
        amount, payload = oautil.leb128(payload)
        if vout[i]["n"] is index:
            return True, amount, tx

    print("指定されたvoutが見つかりませんでした")
    return False, 0, tx


# assetIdを検索する
def searchIssuranceTx(conn, dbconn, voutIndex, txData, txamount):
    vin = txData["vin"]
    isAllColoredTx = True
    c = dbconn.cursor()
    for vinput in vin:
        txid = vinput["txid"]
        vout = vinput["vout"]
        sql = 'select amount, asset_id, issuetxid from ' + config["db"]["tablename"] + ' where txid = %s and vout = %s'
        c.execute(sql, (txid, vout))
        allList = c.fetchall()
        # print(allList)
        # ショートカット
        if len(allList) != 0:
            for record in allList:
                if len(record) < 2:
                    continue
                amount = record[0]
                assetId = record[1]
                issueTxId = record[2]
                isAllColoredTx = False
                if assetId is None or issueTxId is None:
                    continue
                if amount >= txamount:
                    return assetId, issueTxId
        else:
            isColored, amount, inTxData = getTransactionAssetAmount(
                conn, txid, vout)
            # もしvinの中にvoutで使われた以上のassetがある場合
            if isColored and amount >= txamount:
                # そのトランザクションを見る
                assetId, issueTxid = searchIssuranceTx(conn, dbconn, vout,
                                                       inTxData, amount)
                isAllColoredTx = False
                if assetId is not None:
                    return assetId, issueTxid
    # もしvinの中に対応するtxがない or 色付けされたものがない時
    if isAllColoredTx:
        # このトランザクションは発行トランザクション
        print("issue tx: " + txData["txid"])
        o = txData["vout"][voutIndex]
        # print(o)
        if "scriptPubKey" not in o:
            return None, None
        scriptPubKey = o["scriptPubKey"]
        scriptpubkeyHex = scriptPubKey["hex"]
        assetId = oautil.getAssetId(scriptpubkeyHex, isTestnet)
        # 過去にすでに発行されていたならそのアセットIDを使う
        addressFrom = getAddressFrom(conn, txData)
        sql = 'select asset_id, txid from ' + config["db"]["tablename"] + ' where `from` = \'%s\' and `isIssurance` = 1 order by `timestamp`' % addressFrom[0]
        c.execute(sql)
        allList = c.fetchall()
        if len(allList) != 0:
            return allList[0][0], txData["txid"]
        return assetId, txData["txid"]
    else:
        return None, None


if __name__ == "__main__":
    blockHash = sys.argv[1]
    config.read("config.ini")
    isTestnet = scriptpubkeyHex, if "rpcsetting" in config and "testnet" in config["rpcsetting"] and config["rpcsetting"]["testnet"] is "1"
    if len(blockHash) != 0:
        parseBlock(blockHash)
