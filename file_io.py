import json


def add_player_data(discord_id, minecraft_id, points, file_path):
    # 新しいプレイヤーの情報を辞書として作成
    player_data = {
        "discord_id": discord_id,
        "minecraft_id": minecraft_id,
        "points": points,
    }

    try:
        # 既存のデータを読み込み
        with open(file_path, "r") as file:
            data = json.load(file)
    except FileNotFoundError:
        # ファイルが存在しない場合は新しいデータを作成
        data = {"players": []}
        # ファイルに書き込み
        with open(file_path, "w") as file:
            json.dump(data, file, indent=2)

    # 既存のデータに引数のdiscord_idのデータがあれば上書き
    for i, player in enumerate(data["players"]):
        if player["discord_id"] == discord_id:
            data["players"][i] = player_data
            break
    else:
        # 既存のデータに引数のdiscord_idのデータがなければ追加
        data["players"].append(player_data)

    # ファイルに書き込み
    with open(file_path, "w") as file:
        json.dump(data, file, indent=2)  # indentを使って見やすく整形


def get_player_data(discord_id, file_path):
    # ファイルを読み込み
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
    except FileNotFoundError:
        # ファイルが存在しない場合はNoneを返す
        return None

    # プレイヤー情報を探す
    for player_data in data["players"]:
        if player_data["discord_id"] == discord_id:
            return player_data

    # 見つからなかった場合はNoneを返す
    return None


# jsonに登録されているかどうかを確認する
def is_registered(discord_id, file_path):
    player_data = get_player_data(discord_id, file_path)
    if player_data is None:
        return False
    else:
        return True


# マイクラIDが紐づいているかどうかを確認する
def is_linked(discord_id, file_path):
    player_data = get_player_data(discord_id, file_path)
    if player_data is None:
        return False
    elif player_data["minecraft_id"] is None:
        return False
    else:
        return True


# マイクラIDを紐づける
def link(discord_id, minecraft_id, file_path):
    player_data = get_player_data(discord_id, file_path)
    if player_data is None:
        return False
    else:
        player_data["minecraft_id"] = minecraft_id
        add_player_data(
            player_data["discord_id"],
            player_data["minecraft_id"],
            player_data["points"],
            file_path,
        )
        return True


# マイクラIDからDiscordIDを取得する
def get_discord_id(minecraft_id, file_path):
    with open(file_path, "r") as file:
        data = json.load(file)
    for player_data in data["players"]:
        if player_data["minecraft_id"] == minecraft_id:
            return player_data["discord_id"]
    return None


# DiscordIDからマイクラIDを取得する
def get_minecraft_id(discord_id, file_path):
    player_data = get_player_data(discord_id, file_path)
    if player_data is None:
        return None
    else:
        return player_data["minecraft_id"]


# プレイヤーのポイントを更新する
def add_points(discord_id, points, file_path):
    player_data = get_player_data(discord_id, file_path)
    if player_data is None:
        return False
    else:
        player_data["points"] += points
        add_player_data(
            player_data["discord_id"],
            player_data["minecraft_id"],
            player_data["points"],
            file_path,
        )
        return True


# プレイヤー全員にポイントを追加する
def add_points_all(points, file_path):
    with open(file_path, "r") as file:
        data = json.load(file)
    for player_data in data["players"]:
        player_data["points"] += points
    with open(file_path, "w") as file:
        json.dump(data, file, indent=2)
    return True


# プレイヤーのポイントを取得する
def get_points(discord_id, file_path):
    player_data = get_player_data(discord_id, file_path)
    if player_data is None:
        return None
    else:
        return player_data["points"]
    
# 全員のポイントを取得してリストで返す
def get_points_all(file_path):
    with open(file_path, "r") as file:
        data = json.load(file)
    # user_idとpointsを格納するリストを作成
    points_list = []
    for player_data in data["players"]:
        points_list.append([player_data["discord_id"], player_data["points"]])
    return points_list


# registerされているプレイヤーの数を取得する
def get_player_num(file_path):
    with open(file_path, "r") as file:
        data = json.load(file)
    return len(data["players"])


if __name__ == "__main__":
    # テスト用
    import os

    if os.path.exists("test.json"):
        os.remove("test.json")
    print(link(1, None, "test.json"))
