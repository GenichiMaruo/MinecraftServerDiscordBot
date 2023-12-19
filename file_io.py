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
    with open(file_path, "r") as file:
        data = json.load(file)

    # プレイヤー情報を探す
    for player_data in data["players"]:
        if player_data["discord_id"] == discord_id:
            return player_data

    # 見つからなかった場合はNoneを返す
    return None


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


# プレイヤーのポイントを取得する
def get_points(discord_id, file_path):
    player_data = get_player_data(discord_id, file_path)
    if player_data is None:
        return None
    else:
        return player_data["points"]


if __name__ == "__main__":
    # テスト用
    import os

    if os.path.exists("test.json"):
        os.remove("test.json")
    add_player_data(1, None, 0, "test.json")
    add_player_data(2, "test2", 0, "test.json")
    link(1, "test1", "test.json")
    print(get_player_data(1, "test.json"))
    print(get_player_data(2, "test.json"))
