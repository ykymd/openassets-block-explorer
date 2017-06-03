# OpenAssets-BlockExplorer
簡易的なopenassetsの流通量を取得するエクスプローラーです。

## 使い方
1. bitcoindをセットアップします。
1. bitcoin.confのblocknotifyにonBlocknotify.shを実行するように設定します
1. bitcoin.confのwalletnotifyにonWalletnotify.shを実行するように設定します
1. onBlocknotify.shとonWalletnotify.shのROOTDIRの値を変更します
1. config.iniを作成して必要情報を入力します
1. 後は新しいブロックが承認されるたびにblock_logにログが書き込まれます

### 手動でクロールする場合
`python crawl.py <最初に検索するブロック>`

<最初に検索するブロック>が空の場合はgenesis blockになります。

config.iniの["crawl"]["nextblockhash"]に必要情報を入力してください
