import json

# Create a dictionary with the token and channel ID
data = {
    "discord_token": "YOUR_TOKEN_HERE",
    "discord_channel_id": "YOUR_CHANNEL_ID_HERE",
    "minecraft_server_ip": "localhost",
    "minecraft_server_port": 25565,
    "minecraft_server_rcon_port": 25575,
    "minecraft_server_rcon_password": "minecraft",
}

# Write the dictionary to a JSON file
with open("config.json", "w") as file:
    json.dump(data, file, indent=2)  # indentを使って見やすく整形
