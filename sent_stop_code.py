# config.jsonからmcrconの設定を読み込み、サーバーにstopコマンドを送信する

import json
import mcrcon

# config.jsonから設定を読み込む
with open("config.json", "r") as f:
    config = json.load(f)

# mcrconの設定を読み込む
host = config["minecraft_server_ip"]
port = config["minecraft_server_rcon_port"]
password = config["minecraft_server_rcon_password"]

# mcrconでサーバーに接続する
client = mcrcon.MCRcon(host, password, port)
client.connect()

# サーバーにstopコマンドを送信する
client.command("stop")
