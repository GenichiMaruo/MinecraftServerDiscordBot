TOKEN = None
SERVER_DIRECTORY = "./MINECRAFT/server"
SERVER_NAME = "Minecraft Server"
SERVER_SHELL = "run.bat"
SERVER_LOG = "logs/latest.log"
SERVER_PORT = 25565
JSON_FILE_NAME = "user_data.json"

import os
import re
import signal
import time
import subprocess
import random
import json
import file_io
import asyncio
import mcrcon
import discord
from discord import app_commands

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client=client)
last_execution_time = 0
process = None

# config.jsonからdiscordのtokenとchannel_idを読み込む
with open("config.json", "r") as f:
    data = json.load(f)
    TOKEN = data["discord_token"]
    channel_id = data["discord_channel_id"]
    server_address = data["minecraft_server_ip"]
    rcon_port = data["minecraft_server_rcon_port"]
    server_password = data["minecraft_server_rcon_password"]
os.chdir(SERVER_DIRECTORY)

dice_emoji = [
    "<:dice_1:1186303558426038385>",
    "<:dice_2:1186303562163175565>",
    "<:dice_3:1186303565522813000>",
    "<:dice_4:1186303567036960788>",
    "<:dice_5:1186303569624838315>",
    "<:dice_6:1186303556953833572>",
]


@tree.command(name="hello", description="Says hello to you")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"Hello, {interaction.user.mention}!")


# ネタコマンド
@tree.command(name="stap", description="Innovative unknown cell")
async def stap(interaction: discord.Interaction):
    # 100分の1の確率でStap細胞が出現する
    if random.randint(0, 100) == 0:
        await interaction.response.send_message("Stap細胞はあります！")
    else:
        await interaction.response.send_message("Stap細胞はありません…")


# 引数なしだと1つのサイコロ、引数があるとその数のサイコロを振る
@tree.command(name="dice", description="Rolls a dice")
async def dice(interaction: discord.Interaction, num: int = 1):
    if num > 60:
        await interaction.response.send_message("Too many dice!")
        return
    if num < 1:
        await interaction.response.send_message("Too few dice!")
        return
    # サイコロを振る
    dice_list = []
    for i in range(num):
        dice_list.append(random.randint(1, 6))
    # サイコロの目を表示する
    dice_str = ", ".join([str(i) for i in dice_list])
    await interaction.response.send_message(f"{interaction.user.mention} rolled!")
    # discordのサイコロの絵文字を表示する
    dice_resp = ""
    for i in dice_list:
        dice_resp += f"{dice_emoji[i-1]}"
    await interaction.channel.send(dice_resp)


# ヘルプコマンド
@tree.command(name="help", description="Shows the help message")
async def help(interaction: discord.Interaction):
    await interaction.response.send_message(
        "```fix\n"
        + "Minecraft Discord Bot\n"
        + "Commands:\n"
        + "/hello - Says hello to you\n"
        + "/dice - Rolls a dice\n"
        + "/start - Starts the Minecraft server\n"
        + "/backup - Backs up the Minecraft server\n"
        + "/stop - Stops the Minecraft server\n"
        + "/status - Checks the status of the Minecraft server\n"
        + "/list - Lists the players on the Minecraft server\n"
        + "/exit - Stops the Discord bot\n"
        + "/say - Says a message on the Minecraft server\n"
        + "/command - Sends a command to the Minecraft server\n"
        + "/register - Registers you to the point system\n"
        + "/link - Links your Minecraft account to your Discord account\n"
        + "/check - Checks if your Minecraft account is linked to your Discord account\n"
        + "/unlink - Unlinks your Minecraft account from your Discord account\n"
        + "/point - Checks your server points\n"
        + "/mcshop - Shows the shop\n"
        + "/buy - Buy an item with your server points\n"
        + "```"
    )


@tree.command(name="start", description="Starts the Minecraft server")
async def start_server(interaction: discord.Interaction):
    global last_execution_time
    global process
    channel = interaction.channel
    # 2分以内に実行された場合は、実行しない
    if time.time() - last_execution_time < 120:
        await interaction.response.send_message(
            "Please wait 2 minutes before starting the server again!"
        )
        return
    # if minecraft server is already running
    if is_server_running():
        await interaction.response.send_message("Minecraft server is already running!")
        return
    # Code to start the Minecraft server
    else:
        await interaction.response.send_message("Start Command Received!")
        sent_message = await channel.send("```fix\nStarting Minecraft server...\n```")
        await client.change_presence(activity=discord.Game(name="Starting..."))
        last_execution_time = time.time()
        # Start the Minecraft server
        success = await start_process()
        if not success:
            await client.change_presence(activity=discord.Game(name=""))
            await sent_message.edit(
                content="```arm\nMinecraft server failed to start!\n```"
            )
            return
        await sent_message.edit(content="```fix\nMinecraft server started!\n```")
        # Change presence to show server is running
        await client.change_presence(activity=discord.Game(name=SERVER_NAME))


async def start_process():
    global process
    # shell scriptを実行して、サーバーを起動する
    process = subprocess.Popen(
        SERVER_SHELL,
        shell=True,
    )
    # Wait for server to start
    start_time = time.time()
    while not is_server_running():
        if time.time() - start_time > 300:
            # kill the server process
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            return False
        await asyncio.sleep(1)
    return True


@tree.command(name="backup", description="Backs up the Minecraft server")
async def backup_server(interaction: discord.Interaction):
    # Code to backup the Minecraft server
    # 開発中で未実装であることも伝える
    await interaction.response.send_message(
        "Backup Command Received! (Not implemented)"
    )


@tree.command(name="stop", description="Stops the Minecraft server")
@app_commands.default_permissions(administrator=True)
async def stop_server(interaction: discord.Interaction):
    # if minecraft server is already running
    if is_server_running():
        await interaction.response.send_message("Stop Command Received!")
        channel = interaction.channel
        sent_message = await channel.send("```fix\nStopping Minecraft server...\n```")
        # Code to stop the Minecraft server
        # use rcon to stop the server
        with mcrcon.MCRcon(server_address, server_password, rcon_port) as mcr:
            resp = mcr.command("stop")
            print(resp)
        # Wait for server to stop
        start_time = time.time()
        while is_server_running():
            if time.time() - start_time > 60:
                await sent_message.edit(
                    content="```arm\nMinecraft server failed to stop!\n```"
                )
                return
            await asyncio.sleep(1)
        # Change presence to show server is not running
        await client.change_presence(activity=discord.Game(name=""))
        await sent_message.edit(content="```fix\nMinecraft server stopped!\n```")
    else:
        await interaction.response.send_message("Minecraft server is not running!")


@tree.command(name="status", description="Checks the status of the Minecraft server")
async def status_server(interaction: discord.Interaction):
    if is_server_running():
        await interaction.response.send_message("Minecraft server is running!")
    else:
        await interaction.response.send_message("Minecraft server is not running!")


# Minecraft Server に接続しているプレイヤーの一覧を表示する
@tree.command(name="list", description="Lists the players on the Minecraft server")
async def list_server(interaction: discord.Interaction):
    if is_server_running():
        # 参加人数を確認する
        with mcrcon.MCRcon(server_address, server_password, rcon_port) as mcr:
            resp = mcr.command("list")
        # プレイヤーがいない場合
        if re.search(r"0 of a max of 20 players online", resp):
            await interaction.response.send_message("No players are playing!")
        # プレイヤーがいる場合
        else:
            # プレイヤーの一覧を取得する。online: のあとの文字列がプレイヤーの一覧
            player_list = re.search(r"online: (.*)", resp).group(1)
            # プレイヤーの一覧を改行で区切って、リストに格納する
            player_list = player_list.split(", ")
            player_count = len(player_list)
            # 表示のときは、改行を入れて見やすくする
            player_list = "\n".join(player_list)
            resp = f"```fix\n{player_count} players are playing!\n{player_list}\n```"
            await interaction.response.send_message(resp)
    else:
        await interaction.response.send_message("Minecraft server is not running!")


# 管理者のみが実行できるdiscord bot終了コマンド
@tree.command(name="exit", description="Stops the Discord bot")
@app_commands.default_permissions(administrator=True)
async def exit_bot(interaction: discord.Interaction):
    await interaction.response.send_message("Exit Command Received!")
    await client.close()


# 管理者のみが実行できるsayコマンド
@tree.command(name="say", description="Says a message on the Minecraft server")
@app_commands.default_permissions(administrator=True)
async def say_server(interaction: discord.Interaction, message: str):
    if is_server_running():
        # メッセージをサーバーに送信する
        with mcrcon.MCRcon(server_address, server_password, rcon_port) as mcr:
            mcr.command(f"say {message}")
        await interaction.response.send_message("Message sent!")
    else:
        await interaction.response.send_message("Minecraft server is not running!")


# 管理者のみが実行できるサーバー操作コマンド
@tree.command(name="command", description="Sends a command to the Minecraft server")
@app_commands.default_permissions(administrator=True)
async def say_server(interaction: discord.Interaction, message: str):
    if is_server_running():
        # メッセージの先頭に/がない場合は、/を追加する
        if message[0] != "/":
            message = "/" + message
        # メッセージをサーバーに送信する
        with mcrcon.MCRcon(server_address, server_password, rcon_port) as mcr:
            mcr.command(f"{message}")
        await interaction.response.send_message("Message sent!")
    else:
        await interaction.response.send_message("Minecraft server is not running!")


# Point Systemに登録する
@tree.command(name="register", description="Registers you to the point system")
async def register(interaction: discord.Interaction):
    # user_data.json からdiscord_idの紐付けを確認する
    result = file_io.is_registered(interaction.user.id, JSON_FILE_NAME)
    if result:
        await interaction.response.send_message("You are already registered!")
    else:
        # file_io.pyの関数を使ってdiscord_idを登録する
        file_io.add_player_data(interaction.user.id, None, 0, JSON_FILE_NAME)
        await interaction.response.send_message("Registration completed!")


# MinecraftのidとDiscordのidを紐付ける
@tree.command(
    name="link", description="Links your Minecraft account to your Discord account"
)
async def link_account(interaction: discord.Interaction, minecraft_id: str):
    # Minecraftサーバーが起動しているかどうかを確認する
    if not is_server_running():
        await interaction.response.send_message("Minecraft server is not running!")
        return
    # Minecraftサーバーに接続して、プレイヤーの一覧を取得する
    with mcrcon.MCRcon(server_address, server_password, rcon_port) as mcr:
        resp = mcr.command("list")
    # プレイヤーがいない場合
    if re.search(r"0 of a max of 20 players online", resp):
        await interaction.response.send_message(
            "Linking failed! No players are playing!"
        )
    # プレイヤーがいる場合
    else:
        await interaction.response.send_message(
            "Link Command Received! Please wait a moment..."
        )
        # プレイヤーの一覧を取得する。online: のあとの文字列がプレイヤーの一覧
        player_list = re.search(r"online: (.*)", resp).group(1)
        # プレイヤーの一覧を改行で区切って、リストに格納する
        player_list = player_list.split(", ")
        # プレイヤーの一覧にminecraft_idがあるかどうかを確認する
        if minecraft_id in player_list:
            # プレイヤーの一覧にminecraft_idがある場合
            # サーバーにランダムな4桁の数字の個人メッセージを送信
            random_number = random.randint(1000, 9999)
            with mcrcon.MCRcon(server_address, server_password, rcon_port) as mcr:
                mcr.command(
                    f'tellraw {minecraft_id} ["",{{"text":"Please send this number to the bot.","color":"yellow"}},{{"text":"\\n{random_number}","color":"aqua","bold":true}}]'
                )

            # プレイヤーからの個人メッセージを待つ
            def check(m):
                return (
                    m.author.id == interaction.user.id
                    and m.channel.type == discord.ChannelType.private
                )

            try:
                # dmを作成し、個人にメッセージを送信する
                dm = await interaction.user.create_dm()
                # マイクラ内に送られた４桁の数字を入力してもらう
                await dm.send(
                    "Please send the 4-digit number that was sent to you in Minecraft!"
                )
                msg = await client.wait_for("message", check=check, timeout=60)
            except asyncio.TimeoutError:
                dm = await interaction.user.create_dm()
                await dm.send("Linking failed! Timeout!")
                return
            # プレイヤーからの個人メッセージが4桁の数字であるかどうかを確認する
            try:
                msg_number = int(msg.content)
                if msg_number != random_number:
                    # value errorを発生させる
                    raise ValueError
            except ValueError:
                dm = await interaction.user.create_dm()
                await dm.send("Linking failed! Invalid number!")
                return
            # file_io.pyの関数を使ってminecraft_idとdiscord_idを紐付ける
            file_io.link(interaction.user.id, minecraft_id, JSON_FILE_NAME)
            # プレイヤーに紐付けが完了したことをdmで通知する
            dm = await interaction.user.create_dm()
            await dm.send("Linking completed!")
            # プレイヤーに紐付けが完了したことをdiscordに通知する
            await interaction.channel.send(
                f"```fix\n{interaction.user.name} linked {minecraft_id}!\n```"
            )
        else:
            # プレイヤーの一覧にminecraft_idがない場合
            await interaction.channel.send(
                "Linking failed! You are not logged in to Minecraft!"
            )


# MinecraftのidとDiscordのidが紐付いているかどうかを確認する
@tree.command(
    name="check",
    description="Checks if your Minecraft account is linked to your Discord account",
)
async def check_account(interaction: discord.Interaction):
    # user_data.json からminecraft_idとdiscord_idの紐付けを確認する
    result = file_io.is_linked(interaction.user.id, JSON_FILE_NAME)
    if result:
        await interaction.response.send_message("Your Minecraft ID is linked!")
    else:
        await interaction.response.send_message("Your Minecraft ID is not linked!")


# MinecraftのidとDiscordのidを紐付けを解除する
@tree.command(
    name="unlink",
    description="Unlinks your Minecraft account from your Discord account",
)
async def unlink_account(interaction: discord.Interaction):
    # user_data.json からminecraft_idとdiscord_idの紐付けを確認する
    result = file_io.is_linked(interaction.user.id, JSON_FILE_NAME)
    if result:
        # file_io.pyの関数を使ってminecraft_idとdiscord_idの紐付けを解除する
        file_io.link(interaction.user.id, None, JSON_FILE_NAME)
        await interaction.response.send_message("Unlinking completed!")
    else:
        await interaction.response.send_message("Your Minecraft ID is not linked!")


# サーバーポイントを確認する
@tree.command(name="point", description="Checks your server points")
async def check_point(interaction: discord.Interaction):
    # ポイントを取得する
    point = file_io.get_points(interaction.user.id, JSON_FILE_NAME)
    await interaction.response.send_message(f"Your points: ```fix\n{point}\n```")


# サーバーポイントで購入できるアイテムの一覧を表示する
@tree.command(name="mcshop", description="Shows the shop")
async def show_shop(interaction: discord.Interaction):
    # JSONからアイテムの情報を読み込む
    with open("shop_list.json", "r") as f:
        items_data = json.load(f)
    items_list = items_data.get("items", [])  # "items"キーのリストを取得
    # ユーザーにアイテムの一覧を表示する
    shop_embed = discord.Embed(
        title="Server Shop", description="Available Items for Purchase"
    )
    for item in items_list:
        shop_embed.add_field(
            name=f"ID: {item['id']}\n{item['name']} - Price: {item['price']} points",
            value=f"Description: {item['description']}",
            inline=False,
        )
    await interaction.response.send_message(embed=shop_embed)


# サーバーポイントでマイクラのアイテムを購入する
@tree.command(name="buy", description="Buy an item with your server points")
async def buy_item(interaction: discord.Interaction, item_id: str, amount: int = 1):
    # JSONからアイテムの情報を読み込む
    with open("shop_list.json", "r") as f:
        items_data = json.load(f)
    items_list = items_data.get("items", [])
    # マイクラサーバーが起動しているかどうかを確認する
    if not is_server_running():
        await interaction.response.send_message("Minecraft server is not running!")
        return
    # マイクラサーバーに接続して、プレイヤーの一覧を取得する
    with mcrcon.MCRcon(server_address, server_password, rcon_port) as mcr:
        resp = mcr.command("list")
    players = re.search(r"online: (.*)", resp).group(1).split(", ")
    # コマンド実行者のminecraft_idが紐づいているかどうかを確認する
    minecraft_id = file_io.get_minecraft_id(interaction.user.id, JSON_FILE_NAME)
    if minecraft_id is None:
        await interaction.response.send_message("Your Minecraft ID is not linked!")
        return
    # マイクラにログインしているかどうかを確認する
    if minecraft_id not in players:
        await interaction.response.send_message("You are not logged in to Minecraft!")
        return
    # アイテムのIDが存在するかどうかを確認する
    for item in items_list:
        if item["id"] == item_id:
            # discord_idに紐付いたポイントを取得する
            point = file_io.get_points(interaction.user.id, JSON_FILE_NAME)
            # ポイントが足りているかどうかを確認する
            if point >= item["price"] * amount:
                # 購入者にアイテムを付与するコマンドをminecraftに送信する
                with mcrcon.MCRcon(server_address, server_password, rcon_port) as mcr:
                    mcr.command(f"give {minecraft_id} {item['item_command']} {amount}")
                # ポイントを減らす
                file_io.add_points(
                    interaction.user.id, -item["price"] * amount, JSON_FILE_NAME
                )
                # プレイヤーにアイテムが購入されたことをメッセージで通知する
                await interaction.response.send_message("Purchase completed!")
                # プレイヤーにアイテムが購入されたことをdiscordに通知する
                channel = client.get_channel(channel_id)
                await channel.send(
                    f"```fix\n{interaction.user.name} purchased {item['name']}!\n```"
                )
                return
            else:
                await interaction.response.send_message(
                    "You do not have enough points!"
                )
                return


# Minecraft Server に接続しているプレイヤーを監視して、0人になったら5分後にサーバーを停止する
# 定期的に自動実行され、プレイヤーがいる場合はタイマーをリセットする。
async def check_player():
    while True:
        print("Checking for players...")
        if is_server_running():
            # プレイヤーが存在しているかどうかを確認する
            with mcrcon.MCRcon(server_address, server_password, rcon_port) as mcr:
                resp = mcr.command("list")
            # プレイヤーが存在しない場合は、5分後にサーバーを停止する
            if re.search(r"0 of a max of 20 players online", resp):
                # サーバーにプレイヤーがいないことをdiscordに通知する
                channel = client.get_channel(channel_id)
                await channel.send(
                    "```txt\nNo players are playing on the server.\nIf no players join within 5 minutes, the server will be stopped.```"
                )
                await asyncio.sleep(300)
                with mcrcon.MCRcon(server_address, server_password, rcon_port) as mcr:
                    resp = mcr.command("list")
                # 5分後にもプレイヤーがいない場合は、サーバーを停止する
                if (
                    re.search(r"0 of a max of 20 players online", resp)
                    and is_server_running()
                ):
                    # サーバーを停止するコマンドを実行する
                    with mcrcon.MCRcon(
                        server_address, server_password, rcon_port
                    ) as mcr:
                        resp = mcr.command("stop")
                    # Wait for server to stop
                    start_time = time.time()
                    while is_server_running():
                        if time.time() - start_time > 60:
                            # one more try
                            with mcrcon.MCRcon(
                                server_address, server_password, rcon_port
                            ) as mcr:
                                resp = mcr.command("stop")
                            start_time = time.time()
                        await asyncio.sleep(5)
                    # Change presence to show server is not running
                    await client.change_presence(activity=discord.Game(name=""))
                    # サーバーが停止したことをdiscordに通知する
                    await channel.send("```fix\nMinecraft server stopped!\n```")
            else:
                # プレイヤーがいる場合は、point_upを実行する
                player_list = re.search(r"online: (.*)", resp).group(1).split(", ")
                await point_up(player_list)
                # 5分後に再度確認する
                await asyncio.sleep(300)
                continue
        # 1分ごとに確認する
        await asyncio.sleep(60)


# Minecraft Serverに接続していれば紐づいたDiscordのidにサーバーポイントを付与する
async def point_up(minecraft_id_list):
    # discordサーバー参加者からminecraft_id_listに含まれるプレイヤーを探す
    for minecraft_id in minecraft_id_list:
        discord_id = file_io.get_discord_id(minecraft_id, JSON_FILE_NAME)
        # プレイヤーが見つかった場合
        if discord_id is not None:
            # discordサーバー参加者のdiscordのidにポイントを付与する
            file_io.add_points(discord_id, 10, JSON_FILE_NAME)


def is_server_running():
    # Code to check if the Minecraft server is running
    # マイクラサーバーがオンラインかどうかmcrconで確認する
    try:
        with mcrcon.MCRcon(server_address, server_password, rcon_port) as mcr:
            resp = mcr.command("list")
        return True
    except:
        return False


@client.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {client.user.name}")
    # Change presence to show server is not running
    await client.change_presence(activity=discord.Game(name=""))
    client.loop.create_task(check_player())


def main():
    # Discord Botを実行する
    client.run(TOKEN)


if __name__ == "__main__":
    main()
