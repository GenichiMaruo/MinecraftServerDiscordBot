import os
import re
import signal
import time
import subprocess
import random
import json
import asyncio
import mcrcon
import discord
from discord import app_commands
from discord.ext import tasks

import file_io
import trump_game_bj

TOKEN = None
SERVER_DIRECTORY = "./MINECRAFT/server"
SERVER_NAME = "Minecraft Server"
SERVER_SHELL = "run.bat"
SERVER_LOG = "logs/latest.log"
SERVER_PORT = 25565
JSON_FILE_NAME = "user_data.json"
COMMAND_CHANNEL_ID = None
INFO_CHANNEL_ID = None
SERVER_ADDRESS = None
RCON_PORT = None
SERVER_PASSWORD = None
INFO_MESSAGE_ID = None

intents = discord.Intents.default()
intents.reactions = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client=client)
last_execution_time = 0
# 起動処理実行中かどうかを確認する
is_starting = False
# 賭けのレート
rate_dicebet = None
rate_dicebet2 = None
rate_dicebet3 = None
# blackjackの実行中のゲームの実行者のdiscord_idリスト
blackjack_game = []

# config.jsonからdiscordのtokenとchannel_idを読み込む
try:
    with open("config.json", "r") as f:
        data = json.load(f)
        TOKEN = data["discord_token"]
        COMMAND_CHANNEL_ID = data["command_channel_id"]
        INFO_CHANNEL_ID = data["info_channel_id"]
        SERVER_ADDRESS = data["minecraft_server_ip"]
        RCON_PORT = data["minecraft_server_rcon_port"]
        SERVER_PASSWORD = data["minecraft_server_rcon_password"]
        INFO_MESSAGE_ID = data["info_message_id"]
    # IDがint型でない場合は、int型に変換する。Noneの場合は、Noneのままにする
    if COMMAND_CHANNEL_ID is not None:
        COMMAND_CHANNEL_ID = int(COMMAND_CHANNEL_ID)
    if INFO_CHANNEL_ID is not None:
        INFO_CHANNEL_ID = int(INFO_CHANNEL_ID)
    if INFO_MESSAGE_ID is not None:
        INFO_MESSAGE_ID = int(INFO_MESSAGE_ID)
    if RCON_PORT is not None:
        RCON_PORT = int(RCON_PORT)
except FileNotFoundError:
    print("config.json not found!")
    exit()

print("Starting Discord bot...")
# configの内容を確認
print(f"Discord token: {TOKEN}")
print(f"Discord command channel id: {COMMAND_CHANNEL_ID}")
print(f"Discord info channel id: {INFO_CHANNEL_ID}")
print(f"Minecraft server ip: {SERVER_ADDRESS}")
print(f"Minecraft server rcon port: {RCON_PORT}")
print(f"Minecraft server rcon password: {SERVER_PASSWORD}")

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
    # ログを出力する
    print(f"{get_date_str()} {interaction.user.name} {interaction.user.id}\thello")


# ネタコマンド
@tree.command(name="stap", description="Innovative unknown cell")
async def stap(interaction: discord.Interaction):
    res = None
    # 100分の1の確率でStap細胞が出現する
    if random.randint(0, 100) == 0:
        await interaction.response.send_message("Stap細胞はあります！")
        res = True
    else:
        await interaction.response.send_message("Stap細胞はありません…")
        res = False
    # ログを出力する
    print(f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tstap {res}")


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
    resp = f"{interaction.user.mention} rolled!\n"
    # discordのサイコロの絵文字を表示する
    dice_resp = ""
    for i in dice_list:
        dice_resp += f"{dice_emoji[i-1]}"
    resp += dice_resp
    await interaction.response.send_message(resp)
    # ログを出力する
    print(f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tdice")


# ヘルプコマンド
@tree.command(name="help", description="Shows the help message")
async def help(interaction: discord.Interaction):
    await interaction.response.send_message(
        "```fix\n"
        + "Minecraft Discord Bot\n"
        + "Commands:\n"
        + "/hello - Says hello to you\n"
        + "/stap - Innovative unknown cell\n"
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
        + "/point_all - Checks everyone's server points\n"
        + "/mcshop - Shows the shop\n"
        + "/buy - Buy an item with your server points\n"
        + "/givepoint - Give points to a player\n"
        + "/givepoint_admin - Give points to a player\n"
        + "/givepoint_all - Give points to everyone\n"
        + "/dicebet - Bet points on a dice roll. If win, get [bet_amount*5] points\n"
        + "```"
    )
    # ログを出力する
    print(f"{get_date_str()} {interaction.user.name} {interaction.user.id}\thelp")


@tree.command(name="start", description="Starts the Minecraft server")
async def start_server(interaction: discord.Interaction):
    global last_execution_time
    global process
    global is_starting
    channel = interaction.channel
    # 2分以内に実行された場合は、実行しない
    if time.time() - last_execution_time < 120:
        await interaction.response.send_message(
            "Please wait 2 minutes before starting the server again!"
        )
        return
    # 起動処理実行中の場合は、実行しない
    if is_starting:
        await interaction.response.send_message("Starting is in progress!")
        return
    # if minecraft server is already running
    if await is_server_running():
        await interaction.response.send_message("Minecraft server is already running!")
        return
    # Code to start the Minecraft server
    else:
        await interaction.response.send_message("Start Command Received!")
        sent_message = await channel.send("```fix\nStarting Minecraft server...\n```")
        await client.change_presence(activity=discord.Game(name="Starting..."))
        is_starting = True
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
        is_starting = False
        # Change presence to show server is running
        await client.change_presence(activity=discord.Game(name=SERVER_NAME))
    # ログを出力する
    print(f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tstart")


async def start_process():
    # shell scriptを実行して、サーバーを起動する
    process = subprocess.Popen(
        SERVER_SHELL,
        shell=True,
    )
    # Wait for server to start
    start_time = time.time()
    while not await is_server_running():
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
    # ログを出力する
    print(f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tbackup")


@tree.command(name="stop", description="Stops the Minecraft server")
@app_commands.default_permissions(administrator=True)
async def stop_server(interaction: discord.Interaction):
    # if minecraft server is already running
    if await is_server_running():
        await interaction.response.send_message("Stop Command Received!")
        channel = interaction.channel
        sent_message = await channel.send("```fix\nStopping Minecraft server...\n```")
        # Code to stop the Minecraft server
        # use rcon to stop the server
        with mcrcon.MCRcon(SERVER_ADDRESS, SERVER_PASSWORD, RCON_PORT) as mcr:
            resp = mcr.command("stop")
            print(resp)
        # Wait for server to stop
        start_time = time.time()
        while await is_server_running():
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
    # ログを出力する
    print(f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tstop")


@tree.command(name="status", description="Checks the status of the Minecraft server")
async def status_server(interaction: discord.Interaction):
    if await is_server_running():
        await interaction.response.send_message("Minecraft server is running!")
    else:
        await interaction.response.send_message("Minecraft server is not running!")
    # ログを出力する
    print(f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tstatus")


# Minecraft Server に接続しているプレイヤーの一覧を表示する
@tree.command(name="list", description="Lists the players on the Minecraft server")
async def list_server(interaction: discord.Interaction):
    if await is_server_running():
        # 参加人数を確認する
        player_list = await get_player_list()
        # プレイヤーがいない場合
        if len(player_list) == 0:
            await interaction.response.send_message("No players are playing!")
        # プレイヤーがいる場合
        else:
            player_count = len(player_list)
            # 表示のときは、改行を入れて見やすくする
            player_list = "\n".join(player_list)
            resp = f"```fix\n{player_count} players are playing!\n------\n{player_list}\n```"
            await interaction.response.send_message(resp)
    else:
        await interaction.response.send_message("Minecraft server is not running!")
    # ログを出力する
    print(f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tlist")


# 管理者のみが実行できるdiscord bot終了コマンド
@tree.command(name="exit", description="Stops the Discord bot")
@app_commands.default_permissions(administrator=True)
async def exit_bot(interaction: discord.Interaction):
    await interaction.response.send_message("Exit Command Received!")
    await client.close()
    # ログを出力する
    print(f"{get_date_str()} {interaction.user.name} {interaction.user.id}\texit")


# 管理者のみが実行できるsayコマンド
@tree.command(name="say", description="Says a message on the Minecraft server")
@app_commands.default_permissions(administrator=True)
async def say_server(interaction: discord.Interaction, message: str):
    if await is_server_running():
        # メッセージをサーバーに送信する
        with mcrcon.MCRcon(SERVER_ADDRESS, SERVER_PASSWORD, RCON_PORT) as mcr:
            mcr.command(f"say {message}")
        await interaction.response.send_message("Message sent!")
    else:
        await interaction.response.send_message("Minecraft server is not running!")
    # ログを出力する
    print(f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tsay")


# 管理者のみが実行できるサーバー操作コマンド
@tree.command(name="command", description="Sends a command to the Minecraft server")
@app_commands.default_permissions(administrator=True)
async def say_server(interaction: discord.Interaction, message: str):
    if await is_server_running():
        # メッセージの先頭に/がない場合は、/を追加する
        if message[0] != "/":
            message = "/" + message
        # メッセージをサーバーに送信する
        with mcrcon.MCRcon(SERVER_ADDRESS, SERVER_PASSWORD, RCON_PORT) as mcr:
            mcr.command(f"{message}")
        await interaction.response.send_message("Message sent!")
    else:
        await interaction.response.send_message("Minecraft server is not running!")
    # ログを出力する
    print(f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tcommand")


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
    # ログを出力する
    print(f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tregister")


# Point Systemに登録する(管理者のみ)
@tree.command(name="register_admin", description="Registers you to the point system")
@app_commands.default_permissions(administrator=True)
async def register_admin(interaction: discord.Interaction, user: discord.User):
    # user_data.json からdiscord_idの紐付けを確認する
    result = file_io.is_registered(user.id, JSON_FILE_NAME)
    if result:
        await interaction.response.send_message("The user is already registered!")
    else:
        # file_io.pyの関数を使ってdiscord_idを登録する
        file_io.add_player_data(user.id, None, 0, JSON_FILE_NAME)
        await interaction.response.send_message("Registration completed!")
    # ログを出力する
    print(
        f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tregister admin {user.name} {user.id}"
    )


# MinecraftのidとDiscordのidを紐付ける
@tree.command(
    name="link", description="Links your Minecraft account to your Discord account"
)
async def link_account(interaction: discord.Interaction, minecraft_id: str):
    # Minecraftサーバーが起動しているかどうかを確認する
    if not await is_server_running():
        await interaction.response.send_message("Minecraft server is not running!")
        return
    # Minecraftサーバーに接続して、プレイヤーの一覧を取得する
    player_list = await get_player_list()
    # プレイヤーがいない場合
    if len(player_list) == 0:
        await interaction.response.send_message("No players are playing!")
        return
    # プレイヤーがいる場合
    else:
        await interaction.response.send_message(
            "Link Command Received! Please wait a moment..."
        )
        # プレイヤーの一覧にminecraft_idがあるかどうかを確認する
        if minecraft_id in player_list:
            # プレイヤーの一覧にminecraft_idがある場合
            # サーバーにランダムな4桁の数字の個人メッセージを送信
            random_number = random.randint(1000, 9999)
            with mcrcon.MCRcon(SERVER_ADDRESS, SERVER_PASSWORD, RCON_PORT) as mcr:
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
    # ログを出力する
    print(f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tlink")


# MinecraftのidとDiscordのidを紐付ける(管理者のみ)
@tree.command(
    name="link_admin",
    description="Links your Minecraft account to your Discord account",
)
@app_commands.default_permissions(administrator=True)
async def link_account_admin(
    interaction: discord.Interaction, user: discord.User, minecraft_id: str
):
    # 認証なしでマイクラのidとdiscordのidを紐付ける
    if file_io.link(user.id, minecraft_id, JSON_FILE_NAME) is False:
        await interaction.response.send_message("Please register first!")
        return
    # プレイヤーに紐付けが完了したことをdiscordに通知する
    await interaction.channel.send(
        f"```fix\n{interaction.user.name} linked {minecraft_id}!\n```"
    )
    # ログを出力する
    print(
        f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tlink admin {user.name} {user.id}"
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
    # ログを出力する
    print(f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tcheck")


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
    # ログを出力する
    print(f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tunlink")


# サーバーポイントを確認する
@tree.command(name="point", description="Checks your server points")
async def check_point(interaction: discord.Interaction):
    # responseを送信する. コマンド送信者をメンションする
    await interaction.response.send_message(
        f"{interaction.user.mention} point command received!"
    )
    # ポイントを取得する
    point = file_io.get_points(interaction.user.id, JSON_FILE_NAME)
    # ポイントを3桁ごとにカンマを入れて表示する
    point = "{:,}".format(point)
    # ポイントを表示する. 誰のポイントかわかるようにする
    point_embed = discord.Embed(
        title=f"{interaction.user.name}'s Server Points",
        description=f"```fix\n{point}\n```",
    )
    # 色を設定する
    point_embed.colour = discord.Colour.orange()
    try:
        await interaction.channel.send(embed=point_embed)
    except:
        print("Failed to send embed")
    # ログを出力する
    print(f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tpoint")


# 全員のサーバーポイントを確認する(管理者のみ)
@tree.command(name="point_all", description="Checks everyone's server points")
@app_commands.default_permissions(administrator=True)
async def check_point_all(interaction: discord.Interaction):
    global client
    # responseを送信する. コマンド送信者をメンションする
    await interaction.response.send_message(
        f"{interaction.user.mention} point_all command received!"
    )
    # ポイントを取得する
    point_list = file_io.get_points_all(JSON_FILE_NAME)
    # ポイントが多い順に並び替える
    point_list.sort(key=lambda x: x[1], reverse=True)
    # ポイントを表示する
    resp = "```fix\n"
    for user_id, point in point_list:
        # ポイントを3桁ごとにカンマを入れて表示する
        point = "{:,}".format(point)
        # ポイントは最低9桁で右寄せする
        point = point.rjust(9)
        user = await client.fetch_user(user_id)
        resp += f"{user.name:12} : {point}\n"
    resp += "```"
    # embedを使って、ポイントを表示する
    point_embed = discord.Embed(title="Server Points", description=resp)
    # 色を設定する
    point_embed.colour = discord.Colour.orange()
    try:
        await interaction.channel.send(embed=point_embed)
    except:
        print("Failed to send embed")
    # ログを出力する
    print(f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tpoint_all")


# サーバーポイントで購入できるアイテムの一覧を表示する
@tree.command(name="mcshop", description="Shows the shop")
async def show_shop(interaction: discord.Interaction, page: int = 1):
    # JSONからアイテムの情報を読み込む
    with open("shop_list.json", "r") as f:
        items_data = json.load(f)
    items_list = items_data.get("items", [])  # "items"キーのリストを取得
    # ユーザーにアイテムの一覧を表示する
    shop_embed = discord.Embed(
        title="Server Shop", description="Available Items for Purchase"
    )

    # ページ数を計算する
    page_num = len(items_list) // 6 + 1
    if len(items_list) % 6 == 0:
        page_num -= 1
    # ページ数が範囲外の場合は、1ページ目を表示する
    if page < 1 or page > page_num:
        page = 1
    # 表示するアイテムの範囲を計算する
    start = (page - 1) * 6
    end = start + 6
    # 表示するアイテムの範囲を確認する
    if end > len(items_list):
        end = len(items_list)
    # 表示するアイテムの範囲を表示する
    shop_embed.set_footer(text=f"Page {page}/{page_num}")
    # アイテムの一覧を表示する
    for item in items_list:
        if start <= item["id"] - 1 < end:
            shop_embed.add_field(
                name=f"ID: {item['id']}\n{item['name']} - Price: {item['price']} points",
                value=f"Description: {item['description']}",
                inline=False,
            )
    await interaction.response.send_message(embed=shop_embed)
    # ログを出力する
    print(
        f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tmcshop {page}"
    )


# サーバーポイントでマイクラのアイテムを購入する
@tree.command(name="buy", description="Buy an item with your server points")
async def buy_item(interaction: discord.Interaction, item_id: int, amount: int = 1):
    # マイナスの個数を購入しようとしていないかどうかを確認する
    if amount < 0:
        await interaction.response.send_message("You cannot buy minus items!")
        # ログを出力する
        print(
            f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tbuy {item_id} {amount} failed (minus amount)"
        )
        return
    # JSONからアイテムの情報を読み込む
    with open("shop_list.json", "r") as f:
        items_data = json.load(f)
    items_list = items_data["items"]  # "items"キーのリストを取得
    # マイクラサーバーが起動しているかどうかを確認する
    if not await is_server_running():
        await interaction.response.send_message("Minecraft server is not running!")
        # ログを出力する
        print(
            f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tbuy {item_id} {amount} failed (server not running)"
        )
        return
    # マイクラサーバーに接続して、プレイヤーの一覧を取得する
    with mcrcon.MCRcon(SERVER_ADDRESS, SERVER_PASSWORD, RCON_PORT) as mcr:
        resp = mcr.command("list")
    players = re.search(r"online: (.*)", resp).group(1).split(", ")
    # コマンド実行者のminecraft_idが紐づいているかどうかを確認する
    minecraft_id = file_io.get_minecraft_id(interaction.user.id, JSON_FILE_NAME)
    if minecraft_id is None:
        await interaction.response.send_message("Your Minecraft ID is not linked!")
        # ログを出力する
        print(
            f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tbuy {item_id} {amount} failed (not linked)"
        )
        return
    # マイクラにログインしているかどうかを確認する
    if minecraft_id not in players:
        await interaction.response.send_message("You are not logged in to Minecraft!")
        # ログを出力する
        print(
            f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tbuy {item_id} {amount} failed (not logged in)"
        )
        return
    # アイテムのIDが存在するかどうかを確認する
    for item in items_list:
        if item["id"] == item_id:
            # discord_idに紐付いたポイントを取得する
            point = file_io.get_points(interaction.user.id, JSON_FILE_NAME)
            # ポイントが足りているかどうかを確認する
            if point >= item["price"] * amount:
                # 購入者にアイテムを付与するコマンドをminecraftに送信する
                print(
                    f"Sending command: give {minecraft_id} {item['item_command']} {amount}"
                )
                with mcrcon.MCRcon(SERVER_ADDRESS, SERVER_PASSWORD, RCON_PORT) as mcr:
                    mcr.command(f"give {minecraft_id} {item['item_command']} {amount}")
                # 成功しているかどうかを確認する
                with mcrcon.MCRcon(SERVER_ADDRESS, SERVER_PASSWORD, RCON_PORT) as mcr:
                    resp = mcr.command(f"clear {minecraft_id} {item['item_command']} 0")
                if re.search(r"Cleared 0 items", resp):
                    await interaction.response.send_message("Purchase failed!")
                    # ログを出力する
                    print(
                        f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tbuy {item_id} {amount} failed (minecraft command failed)"
                    )
                    return
                # ポイントを減らす
                file_io.add_points(
                    interaction.user.id, -item["price"] * amount, JSON_FILE_NAME
                )
                # プレイヤーにアイテムが購入されたことをメッセージで通知する
                resp_msg = f"{interaction.user.mention} purchase completed!\n```fix\nYou purchased {item['name']} x {amount}!\n```"
                await interaction.response.send_message(resp_msg)
                # ログを出力する
                print(
                    f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tbuy {item_id} {amount} success"
                )
                return
            else:
                await interaction.response.send_message(
                    "You do not have enough points!"
                )
                # ログを出力する
                print(
                    f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tbuy {item_id} {amount} failed (not enough points)"
                )
                return
    await interaction.response.send_message("Invalid item ID!")


# ポイントを渡す
@tree.command(name="givepoint", description="Give points to a player")
async def give_point(interaction: discord.Interaction, amount: int, user: discord.User):
    # ログを出力する
    print(
        f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tgivepoint {amount} {user.name}"
    )
    # 自分にポイントを渡そうとしていないかどうかを確認する
    if interaction.user.id == user.id:
        await interaction.response.send_message("You cannot give points to yourself!")
        return
    # minusのポイントを渡そうとしていないかどうかを確認する
    if amount < 0:
        await interaction.response.send_message("You cannot give minus points!")
        return
    # registerされているかどうかを確認する
    result = file_io.is_registered(interaction.user.id, JSON_FILE_NAME)
    if not result:
        await interaction.response.send_message("You are not registered!")
        return
    # ポイントが足りているかどうかを確認する
    point = file_io.get_points(interaction.user.id, JSON_FILE_NAME)
    if point < amount:
        await interaction.response.send_message("You do not have enough points!")
        return
    # ポイントを渡す相手がregisterされているかどうかを確認する
    result = file_io.is_registered(user.id, JSON_FILE_NAME)
    if not result:
        await interaction.response.send_message("The user is not registered!")
        return
    # ポイントを渡す
    await interaction.response.send_message("Give Command Received!")
    file_io.add_points(interaction.user.id, -amount, JSON_FILE_NAME)
    file_io.add_points(user.id, amount, JSON_FILE_NAME)
    await interaction.channel.send(
        f"```fix\n{interaction.user.name} gave {amount} points to {user.name}!\n```"
    )


# 管理者のみが実行できるポイントを渡すコマンド
@tree.command(name="givepoint_admin", description="Give points to a player")
@app_commands.default_permissions(administrator=True)
async def give_point_admin(
    interaction: discord.Interaction, amount: int, user: discord.User
):
    # ログを出力する
    print(
        f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tgivepoint_admin {amount} {user.name}"
    )
    # ポイントを渡す相手がregisterされているかどうかを確認する
    result = file_io.is_registered(user.id, JSON_FILE_NAME)
    if not result:
        await interaction.response.send_message("The user is not registered!")
        return
    # ポイントを渡す
    await interaction.response.send_message("Give Command Received!")
    file_io.add_points(user.id, amount, JSON_FILE_NAME)
    await interaction.channel.send(
        f"```fix\n{interaction.user.name} gave {amount} points to {user.name}!\n```"
    )


# 管理者のみが実行できる@everyoneにポイントを渡すコマンド
@tree.command(name="givepoint_all", description="Give points to everyone")
@app_commands.default_permissions(administrator=True)
async def give_point_all(interaction: discord.Interaction, amount: int):
    # ログを出力する
    print(
        f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tgivepoint_all {amount}"
    )
    await interaction.response.send_message("Give Command Received!")
    # ポイントを渡す
    file_io.add_points_all(amount, JSON_FILE_NAME)
    await interaction.channel.send(
        f"```fix\n{interaction.user.name} gave {amount} points to everyone!\n```"
    )


# サイコロでポイントを賭ける
@tree.command(
    name="dicebet",
    description="Bet points on a dice roll. If win, get [bet_amount*5] points",
)
async def dice_bet(interaction: discord.Interaction, amount: str, num: int):
    global rate_dicebet
    if amount == "all":
        amount = file_io.get_points(interaction.user.id, JSON_FILE_NAME)
    else:
        if not amount.isdigit():
            await interaction.response.send_message("Invalid amount!")
            return
        amount = int(amount)
    # minusのポイントを賭けようとしていないかどうかを確認する
    if amount < 0:
        await interaction.response.send_message("You cannot bet minus points!")
        return
    # registerされているかどうかを確認する
    result = file_io.is_registered(interaction.user.id, JSON_FILE_NAME)
    if not result:
        await interaction.response.send_message("You are not registered!")
        return
    # ポイントが足りているかどうかを確認する
    point = file_io.get_points(interaction.user.id, JSON_FILE_NAME)
    if point < amount:
        await interaction.response.send_message("You do not have enough points!")
        return
    # 選択したサイコロの目が1~6の間にあるかどうかを確認する
    if num < 1 or num > 6:
        await interaction.response.send_message("Invalid number!")
        return
    # embedを使って、賭けの結果を表示する
    dice_bet_embed = discord.Embed(
        title="Dice Bet",
        description=f"{interaction.user.mention} rolled!\n```fix\nYou chose {num}!\nBetting {amount} points!\n```",
    )
    # サイコロを振る
    dice_list = []
    for i in range(1):
        dice_list.append(random.randint(1, 6))
    # discordのサイコロの絵文字を表示する
    dice_resp = ""
    for i in dice_list:
        dice_resp += f"{dice_emoji[i-1]}"
    dice_bet_embed.add_field(name="Result", value=dice_resp, inline=False)
    # サイコロの目が一致した場合
    if dice_list[0] == num:
        # ポイントを増やす
        file_io.add_points(
            interaction.user.id, int(amount * 5 * rate_dicebet), JSON_FILE_NAME
        )
        dice_bet_embed.add_field(
            name="",
            value=f"```fix\n{interaction.user.name} won {int(amount*5*rate_dicebet)} points!\n```",
            inline=False,
        )
    # サイコロの目が一致しなかった場合
    else:
        # ポイントを減らす
        file_io.add_points(interaction.user.id, -amount, JSON_FILE_NAME)
        dice_bet_embed.add_field(
            name="",
            value=f"```fix\n{interaction.user.name} lost {amount} points!\n```",
            inline=False,
        )
        # 減らしたポイント分を全員に分配する
        player_num = file_io.get_player_num(JSON_FILE_NAME)
        if player_num > 1:
            player_num -= 1
            file_io.add_points_all(int(amount / player_num), JSON_FILE_NAME)
            # 賭けをしたプレイヤーに追加された分を減らす
            file_io.add_points(
                interaction.user.id, -int(amount / player_num), JSON_FILE_NAME
            )
            # 全員に何ポイントずつ追加されたかを表示する
            dice_bet_embed.add_field(
                name="Distribution",
                value=f"```fix\n{int(amount / player_num)} points were added to everyone!\n```",
                inline=False,
            )
    await interaction.response.send_message(embed=dice_bet_embed)
    # ログを出力する
    print(
        f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tdicebet {amount} {num}"
    )


# 複数のdiceの合計を賭ける
@tree.command(
    name="dicebet2",
    description="Bet points on a dice roll. If win, get [bet_amount*dice_count*5] points",
)
async def dice_bet2(
    interaction: discord.Interaction, amount: str, dice_count: int, num: int
):
    global rate_dicebet2
    if amount == "all":
        amount = file_io.get_points(interaction.user.id, JSON_FILE_NAME)
    else:
        if not amount.isdigit():
            await interaction.response.send_message("Invalid amount!")
            return
        amount = int(amount)
    # minusのポイントを賭けようとしていないかどうかを確認する
    if amount < 0:
        await interaction.response.send_message("You cannot bet minus points!")
        return
    # registerされているかどうかを確認する
    result = file_io.is_registered(interaction.user.id, JSON_FILE_NAME)
    if not result:
        await interaction.response.send_message("You are not registered!")
        return
    # ポイントが足りているかどうかを確認する
    point = file_io.get_points(interaction.user.id, JSON_FILE_NAME)
    if point < amount:
        await interaction.response.send_message("You do not have enough points!")
        return
    # 選択したサイコロの数が60以下かどうかを確認する
    if dice_count > 60:
        await interaction.response.send_message("Too many dice!")
        return
    if dice_count < 1:
        await interaction.response.send_message("Too few dice!")
        return
    # 選択した合計値が1~dice_count*6の間にあるかどうかを確認する
    if num < dice_count or num > dice_count * 6:
        await interaction.response.send_message("Invalid number!")
        return
    # サイコロを振る
    dice_list = []
    for i in range(dice_count):
        dice_list.append(random.randint(1, 6))
    # embedを使って、賭けの結果を表示する
    dice_bet_embed = discord.Embed(
        title="Dice Bet 2",
        description=f"{interaction.user.mention} rolled!\n```fix\nYou chose {num}!\nBetting {amount} points!\n```",
    )
    # discordのサイコロの絵文字を表示する
    dice_resp = ""
    for i in dice_list:
        dice_resp += f"{dice_emoji[i-1]}"
    dice_bet_embed.add_field(name="Result", value=dice_resp, inline=False)
    # サイコロの合計を表示する
    dice_bet_embed.add_field(
        name="", value=f"```fix\nSum: {sum(dice_list)}\n```", inline=False
    )
    # サイコロの目が一致した場合
    if sum(dice_list) == num:
        # ポイントを増やす（サイコロの数だけ増やす）
        file_io.add_points(
            interaction.user.id,
            int(amount * dice_count * 5 * rate_dicebet2),
            JSON_FILE_NAME,
        )
        dice_bet_embed.add_field(
            name="",
            value=f"```fix\n{interaction.user.name} won {int(amount*dice_count*5*rate_dicebet2)} points!\n```",
            inline=False,
        )
    # サイコロの目が一致しなかった場合
    else:
        # ポイントを減らす
        file_io.add_points(interaction.user.id, -amount, JSON_FILE_NAME)
        dice_bet_embed.add_field(
            name="",
            value=f"```fix\n{interaction.user.name} lost {amount} points!\n```",
            inline=False,
        )
        # 減らしたポイント分を全員に分配する
        player_num = file_io.get_player_num(JSON_FILE_NAME)
        if player_num > 1:
            player_num -= 1
            file_io.add_points_all(int(amount / player_num), JSON_FILE_NAME)
            # 賭けをしたプレイヤーに追加された分を減らす
            file_io.add_points(
                interaction.user.id, -int(amount / player_num), JSON_FILE_NAME
            )
            # 全員に何ポイントずつ追加されたかを表示する
            dice_bet_embed.add_field(
                name="Distribution",
                value=f"```fix\n{int(amount / player_num)} points were added to everyone!\n```",
                inline=False,
            )
    await interaction.response.send_message(embed=dice_bet_embed)
    # ログを出力する
    print(
        f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tdicebet2 {amount} {dice_count} {num}"
    )


# 2個のサイコロの合計が丁か半かを賭ける
@tree.command(
    name="dicebet3",
    description='"even" or "odd" on the sum of two dice',
)
async def dice_bet3(interaction: discord.Interaction, amount: str, choice: str):
    global rate_dicebet3
    if amount == "all":
        amount = file_io.get_points(interaction.user.id, JSON_FILE_NAME)
    else:
        if not amount.isdigit():
            await interaction.response.send_message("Invalid amount!")
            return
        amount = int(amount)
    # minusのポイントを賭けようとしていないかどうかを確認する
    if amount < 0:
        await interaction.response.send_message("You cannot bet minus points!")
        return
    # registerされているかどうかを確認する
    result = file_io.is_registered(interaction.user.id, JSON_FILE_NAME)
    if not result:
        await interaction.response.send_message("You are not registered!")
        return
    # ポイントが足りているかどうかを確認する
    point = file_io.get_points(interaction.user.id, JSON_FILE_NAME)
    if point < amount:
        await interaction.response.send_message("You do not have enough points!")
        return
    # 選択した合計値が"even"か"odd"かを確認する
    if choice != "even" and choice != "odd":
        await interaction.response.send_message("Invalid choice!")
        return
    # サイコロを振る
    dice_list = []
    for i in range(2):
        dice_list.append(random.randint(1, 6))
    # embedを使って、賭けの結果を表示する
    dice_bet_embed = discord.Embed(
        title="Dice Bet 3",
        description=f"{interaction.user.mention} rolled!\n```fix\nYou chose {choice}!\nBetting {amount} points!\n```",
    )
    # discordのサイコロの絵文字を表示する
    dice_resp = ""
    for i in dice_list:
        dice_resp += f"{dice_emoji[i-1]}"
    dice_bet_embed.add_field(name="Result", value=dice_resp, inline=False)
    # サイコロの合計が丁か半かを表示する
    if sum(dice_list) % 2 == 0:
        dice_bet_embed.add_field(name="", value=f"```fix\nSum: Even\n```", inline=False)
    else:
        dice_bet_embed.add_field(name="", value=f"```fix\nSum: Odd\n```", inline=False)
    # サイコロの合計が丁か半かを確認する
    if sum(dice_list) % 2 == 0 and choice == "even":
        # ポイントを増やす
        file_io.add_points(
            interaction.user.id, int(amount * rate_dicebet3), JSON_FILE_NAME
        )
        dice_bet_embed.add_field(
            name="",
            value=f"```fix\n{interaction.user.name} won {int(amount*rate_dicebet3)} points!\n```",
            inline=False,
        )
    elif sum(dice_list) % 2 == 1 and choice == "odd":
        # ポイントを増やす
        file_io.add_points(
            interaction.user.id, int(amount * rate_dicebet3), JSON_FILE_NAME
        )
        dice_bet_embed.add_field(
            name="",
            value=f"```fix\n{interaction.user.name} won {int(amount*rate_dicebet3)} points!\n```",
            inline=False,
        )
    else:
        # ポイントを減らす
        file_io.add_points(interaction.user.id, -amount, JSON_FILE_NAME)
        dice_bet_embed.add_field(
            name="",
            value=f"```fix\n{interaction.user.name} lost {amount} points!\n```",
            inline=False,
        )
        # 減らしたポイント分を全員に分配する
        player_num = file_io.get_player_num(JSON_FILE_NAME)
        if player_num > 1:
            player_num -= 1
            file_io.add_points_all(int(amount * 0.5 / player_num), JSON_FILE_NAME)
            # 賭けをしたプレイヤーに追加された分を減らす
            file_io.add_points(
                interaction.user.id, -int(amount * 0.5 / player_num), JSON_FILE_NAME
            )
            # 全員に何ポイントずつ追加されたかを表示する
            dice_bet_embed.add_field(
                name="Distribution",
                value=f"```fix\n{int(amount * 0.5 / player_num)} points were added to everyone!\n```",
                inline=False,
            )
    await interaction.response.send_message(embed=dice_bet_embed)
    # ログを出力する
    print(
        f"{get_date_str()} {interaction.user.name} {interaction.user.id}\tdicebet3 {amount} {choice}"
    )


# blackjackでポイントを賭ける
@tree.command(
    name="blackjack",
    description="Bet points on a blackjack game. If win, get [bet_amount*2] points",
)
async def blackjack(interaction: discord.Interaction, amount: str):
    global blackjack_game
    if amount == "all":
        amount = file_io.get_points(interaction.user.id, JSON_FILE_NAME)
    else:
        if not amount.isdigit():
            await interaction.response.send_message("Invalid amount!")
            return
        amount = int(amount)
    # minusのポイントを賭けようとしていないかどうかを確認する
    if amount < 0:
        await interaction.response.send_message("You cannot bet minus points!")
        return
    # registerされているかどうかを確認する
    result = file_io.is_registered(interaction.user.id, JSON_FILE_NAME)
    if not result:
        await interaction.response.send_message("You are not registered!")
        return
    # ポイントが足りているかどうかを確認する
    point = file_io.get_points(interaction.user.id, JSON_FILE_NAME)
    if point < amount:
        await interaction.response.send_message("You do not have enough points!")
        return
    # 賭けの最低額を確認する
    if amount < 100:
        await interaction.response.send_message("Minimum bet is 100 points!")
        return
    # すでに実行中のゲームがあるかどうかを確認する
    for game in blackjack_game:
        if game.get_player_id() == interaction.user.id:
            # ゲームがすでに実行中であることを通知する
            await interaction.response.send_message("You are already playing a game!")
            return
    # コマンドを受け取ったことをdiscordに通知する
    await interaction.response.send_message(
        f"{interaction.user.mention} Blackjack Command Received!"
    )
    # 掛け金を引く
    file_io.add_points(interaction.user.id, -amount, JSON_FILE_NAME)
    # ゲームを作成する
    game = trump_game_bj.GameBlackJack(interaction.user.id)
    # blackjack_playersに追加する
    blackjack_game.append(game)
    # discordにゲームembedを送信する。投稿は後で編集できるようにmessageオブジェクトを取得する
    channel = interaction.channel
    message = await channel.send(embed=game.get_embed())
    # メッセージidを保存する
    game.set_message_id(message.id)
    # ゲームを開始する
    game.start_game(amount=amount)
    # 投稿を更新する
    await message.edit(embed=game.get_embed())
    # 投稿にヒットとスタンドのリアクションをつける
    await message.add_reaction("🇭")
    await message.add_reaction("🇸")


async def create_error_embed(error_msg):
    embed = discord.Embed(title="Error", description=error_msg)
    # カラーを赤に設定する
    embed.colour = discord.Colour.red()
    return embed


# Minecraft Server に接続しているプレイヤーを監視して、0人になったら5分後にサーバーを停止する
# 定期的に自動実行され、プレイヤーがいる場合はタイマーをリセットする。
async def check_player():
    global is_starting
    while True:
        # ログを出力する
        print(f"{get_date_str()} Checking players")
        if await is_server_running():
            # アクティビティを変更して、サーバーが起動していることを表示する
            await client.change_presence(activity=discord.Game(name=SERVER_NAME))
            # プレイヤーが存在しているかどうかを確認する
            player_list = await get_player_list()
            # プレイヤーが存在しない場合は、5分後にサーバーを停止する
            if len(player_list) == 0:
                # サーバーにプレイヤーがいないことをdiscordに通知する
                channel = client.get_channel(COMMAND_CHANNEL_ID)
                if channel is not None:
                    await channel.send("```fix\nNo players are playing!\n```")
                await asyncio.sleep(300)
                # 再度プレイヤーがいるかどうかを確認する
                player_list = await get_player_list()
                # 5分後にもプレイヤーがいない場合は、サーバーを停止する
                if len(player_list) == 0:
                    # サーバーを停止するコマンドを実行する
                    with mcrcon.MCRcon(
                        SERVER_ADDRESS, SERVER_PASSWORD, RCON_PORT
                    ) as mcr:
                        resp = mcr.command("stop")
                    # Wait for server to stop
                    start_time = time.time()
                    while await is_server_running():
                        if time.time() - start_time > 60:
                            # one more try
                            with mcrcon.MCRcon(
                                SERVER_ADDRESS, SERVER_PASSWORD, RCON_PORT
                            ) as mcr:
                                resp = mcr.command("stop")
                            start_time = time.time()
                        await asyncio.sleep(5)
                    # Change presence to show server is not running
                    await client.change_presence(activity=discord.Game(name=""))
                    # サーバーが停止したことをdiscordに通知する
                    if channel is not None:
                        await channel.send("```fix\nServer stopped!\n```")
            else:
                # プレイヤーがいる場合は、point_upを実行する
                player_list = await get_player_list()
                if len(player_list) > 0:
                    await point_up(player_list)
                    # 5分後に再度確認する
                    await asyncio.sleep(300)
                    continue
        elif is_starting:
            # サーバーが起動中の場合は、アクティビティを変更して、サーバーが起動中であることを表示する
            await client.change_presence(activity=discord.Game(name="Starting..."))
        else:
            # アクティビティを変更して、サーバーが停止していることを表示する
            await client.change_presence(activity=discord.Game(name=""))
        # 1分ごとに確認する
        await asyncio.sleep(60)


# Minecraft Serverに接続していれば紐づいたDiscordのidにサーバーポイントを付与する
async def point_up(minecraft_id_list):
    # discordサーバー参加者からminecraft_id_listに含まれるプレイヤーを探す
    for minecraft_id in minecraft_id_list:
        discord_id = file_io.get_discord_id(minecraft_id, JSON_FILE_NAME)
        # プレイヤーが見つかった場合
        if discord_id is not None:
            print(f"Found {minecraft_id}!")
            # discordサーバー参加者のdiscordのidにポイントを付与する
            file_io.add_points(discord_id, 10, JSON_FILE_NAME)


async def is_server_running():
    # Code to check if the Minecraft server is running
    # マイクラサーバーがオンラインかどうかmcrconで確認する
    try:
        with mcrcon.MCRcon(SERVER_ADDRESS, SERVER_PASSWORD, RCON_PORT) as mcr:
            resp = mcr.command("list")
        return True
    except:
        return False


async def import_rate():
    global rate_dicebet, rate_dicebet2, rate_dicebet3
    try:
        # JSONからレートの情報を読み込む
        with open("rate.json", "r") as f:
            rate_data = json.load(f)
        rate_dicebet = rate_data.get("rate_dicebet", 1)
        rate_dicebet2 = rate_data.get("rate_dicebet2", 1)
        rate_dicebet3 = rate_data.get("rate_dicebet3", 1)
    except:
        # JSONが存在しない場合は、レートをランダムに変更する
        await change_rate()
        # JSONに書き込む
        with open("rate.json", "w") as f:
            json.dump(
                {
                    "rate_dicebet": rate_dicebet,
                    "rate_dicebet2": rate_dicebet2,
                    "rate_dicebet3": rate_dicebet3,
                },
                f,
                indent=4,
            )


# 賭けのレートをランダムに変更する
async def change_rate():
    global rate_dicebet, rate_dicebet2, rate_dicebet3
    # 0.7~1.2の間の乱数を生成する
    rate_dicebet = random.uniform(0.6, 1.2)
    rate_dicebet2 = random.uniform(0.6, 1.2)
    rate_dicebet3 = random.uniform(0.6, 1.2)
    # JSONに書き込む
    with open("rate.json", "w") as f:
        json.dump(
            {
                "rate_dicebet": rate_dicebet,
                "rate_dicebet2": rate_dicebet2,
                "rate_dicebet3": rate_dicebet3,
            },
            f,
            indent=4,
        )
    # ログを出力する
    print(
        f"{get_date_str()} Changed rate ({rate_dicebet:.2f},{rate_dicebet2:.2f},{rate_dicebet3:.2f})"
    )


# 1分ごとに実行する
@tasks.loop(seconds=60)
async def minute_loop():
    # 賭けのレートを前回のレート変更から30分後であれば変更する
    global rate_dicebet, rate_dicebet2, rate_dicebet3
    if minute_loop.current_loop % 30 == 0:
        await change_rate()
    # プレイヤーの一覧を取得する
    player_list = await get_player_list()
    # embedを編集する
    await edit_info_message(player_list, INFO_CHANNEL_ID, INFO_MESSAGE_ID)


# info_messageを投稿する
async def post_info_message():
    # プレイヤーの一覧を取得する
    player_list = await get_player_list()
    # embedを作成する
    info_embed = discord.Embed(title="Info", description="Dice Bet Rate and Players")
    # rateがnoneでない場合は、rateを表示する
    if (
        rate_dicebet is not None
        and rate_dicebet2 is not None
        and rate_dicebet3 is not None
    ):
        info_embed.add_field(
            name="Dice Bet Rate",
            value=f"```fix\nDice Bet:  {rate_dicebet:.2f}\nDice Bet2: {rate_dicebet2:.2f}\nDice Bet3: {rate_dicebet3:.2f}\n```",
            inline=False,
        )
    # プレイヤーの一覧を表示する
    player_list_str = ""
    # 現在のサーバーの稼働状況によってembedの色を変える
    if await is_server_running():
        info_embed.colour = discord.Colour.green()
        if len(player_list) == 0:
            player_list_str = "No players are playing!"
        else:
            for player in player_list:
                player_list_str += f"{player}\n"
    else:
        info_embed.colour = discord.Colour.red()
        player_list_str = "Minecraft server is not running!"
    info_embed.add_field(
        name="Players",
        value=f"```fix\n{player_list_str}\n```",
        inline=False,
    )
    # 投稿する
    channel = client.get_channel(INFO_CHANNEL_ID)
    message = await channel.send(embed=info_embed)
    # ログを出力する
    print(f"{get_date_str()} Posted info message")
    # info_message_idを更新する
    global INFO_MESSAGE_ID
    INFO_MESSAGE_ID = message.id
    # config.jsonのinfo_message_idを更新する
    try:
        with open("config.json", "r") as f:
            config_data = json.load(f)
        config_data["info_message_id"] = INFO_MESSAGE_ID
        with open("config.json", "w") as f:
            json.dump(config_data, f, indent=4)
    except:
        # ログを出力する
        print(f"{get_date_str()} Failed to update info_message_id")
        return
    # ログを出力する
    print(f"{get_date_str()} Updated info_message_id")


# Player_listを引数に取り、指定の投稿を編集して、賭けのレートとプレイヤーの一覧を表示する
async def edit_info_message(player_list, channel_id, info_message_id):
    # embedを作成する
    info_embed = discord.Embed(title="Info", description="Dice Bet Rate and Players")
    # 賭けのレートを表示する
    info_embed.add_field(
        name="Dice Bet Rate",
        value=f"```fix\nDice Bet:  {rate_dicebet:.2f}\nDice Bet2: {rate_dicebet2:.2f}\nDice Bet3: {rate_dicebet3:.2f}\n```",
        inline=False,
    )
    # プレイヤーの一覧を表示する
    player_list_str = ""
    # 現在のサーバーの稼働状況によってembedの色を変える
    if await is_server_running():
        info_embed.colour = discord.Colour.green()
        if len(player_list) == 0:
            player_list_str = "No players are playing!"
        else:
            for player in player_list:
                player_list_str += f"{player}\n"
    elif is_starting:
        info_embed.colour = discord.Colour.yellow()
        player_list_str = "Minecraft server is starting..."
    else:
        info_embed.colour = discord.Colour.red()
        player_list_str = "Minecraft server is not running!"
    info_embed.add_field(
        name="Players",
        value=f"```fix\n{player_list_str}\n```",
        inline=False,
    )
    # 投稿を編集する
    channel = client.get_channel(channel_id)
    message = await channel.fetch_message(info_message_id)
    await message.edit(embed=info_embed)
    # ログを出力する
    print(f"{get_date_str()} Edited info message")


# マイクラのサーバーに接続しているプレイヤーの一覧を取得する。サーバーに誰もいない場合は空のリストを返す
async def get_player_list():
    # マイクラサーバーが起動しているかどうかを確認する
    if not await is_server_running():
        return []
    # マイクラサーバーに接続して、プレイヤーの一覧を取得する
    try:
        with mcrcon.MCRcon(SERVER_ADDRESS, SERVER_PASSWORD, RCON_PORT) as mcr:
            resp = mcr.command("list")
        player_list = re.search(r"online: (.*)", resp).group(1).split(", ")
        if player_list[0] == "":
            return []
    except:
        return []
    return player_list


def get_date_str():
    return time.strftime("%Y-%m-%d %H:%M:%S")


@client.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {client.user.name}")
    # info_messageを投稿する
    if INFO_MESSAGE_ID is None:
        await post_info_message()
    # サーバーのディレクトリに移動する
    os.chdir(SERVER_DIRECTORY)
    # 賭けのレートを読み込む
    await import_rate()
    # 1分ごとに実行する
    minute_loop.start()
    # Change presence to show server is not running
    await client.change_presence(activity=discord.Game(name=""))
    client.loop.create_task(check_player())


# リアクションを受け取ったときに実行される
@client.event
async def on_raw_reaction_add(payload):
    # リアクションをしたメッセージを取得する
    channel = client.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    # リアクションをしたユーザーを取得する
    user = await client.fetch_user(payload.user_id)
    # リアクションをしたユーザーがBotの場合は無視する
    if user.bot:
        return
    # リアクションをしたメッセージがblackjackのゲームである場合
    if message.id in [game.message_id for game in blackjack_game]:
        # リアクションをしたユーザーがゲームのプレイヤーである場合
        for game in blackjack_game:
            if message.id == game.message_id and user.id == game.player_id:
                # リアクションに対応する処理を実行するまえにデバッグ用にリアクションの情報を出力する
                print(f"{get_date_str()} {user.name} {user.id} reacted to {game}")
                print(f"{get_date_str()} {payload.emoji.name}")
                # リアクションに対応する処理を実行する
                await game.react(payload)
                # メッセージを編集する
                await message.edit(embed=game.get_embed())
                # is_playingがFalseになった場合は、blackjack_gameから削除する
                if not game.is_playing:
                    blackjack_game.remove(game)
                    # gameオブジェクトを削除する
                    del game
                return


def main():
    # Discord Botを実行する
    client.run(TOKEN)


if __name__ == "__main__":
    main()
