import json
import os
import time
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

SERVER_ADDRESS = os.getenv("SERVER_ADDRESS")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
CHECK_INTERVAL = 30

last_known_players: set[str] = set()
HEADERS = {"User-Agent": "MinecraftPlayerMonitor/1.0"}


def current_time() -> str:
    return datetime.now().strftime("[%H:%M:%S]")


def send_discord_message(message: str):
    payload = {"content": message}
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, headers={"Content-Type": "application/json"})
        response.raise_for_status()
        print(f"{current_time()} Discord消息发送成功")
    except requests.exceptions.RequestException as e:
        print(f"{current_time()} 发送Discord消息失败: {e}")
    except Exception as e:
        print(f"{current_time()} 处理Discord消息时发生未知错误: {e}")


def check_all_players_status():
    global last_known_players
    url = f"https://api.mcstatus.io/v2/status/java/{SERVER_ADDRESS}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()

        data = response.json()

        current_online_players = set()
        server_online = data.get("online", False)

        if server_online:
            if "players" in data and data["players"] and "list" in data["players"]:
                current_online_players = {p["name_clean"] for p in data["players"]["list"]}
            elif data.get("players", {}).get("online", 0) == 0:
                print(f"{current_time()} 服务器 {SERVER_ADDRESS} 在线，但当前没有玩家")
                current_online_players = set()
            else:
                print(f"{current_time()} 服务器 {SERVER_ADDRESS} 在线，但无法获取玩家列表")
                current_online_players = set()

        elif not server_online:
            print(f"{current_time()} 服务器 {SERVER_ADDRESS} 当前离线")
            if last_known_players:
                for player in last_known_players:
                    message = f"🔴 {current_time()} 玩家 **{player}** 下线了 (服务器离线)"
                    send_discord_message(message)
                last_known_players.clear()
            return

        newly_online_players = current_online_players - last_known_players
        for player in newly_online_players:
            message = f"🟢 {current_time()} 玩家 **{player}** 上线了"
            send_discord_message(message)

        newly_offline_players = last_known_players - current_online_players
        for player in newly_offline_players:
            message = f"🔴 {current_time()} 玩家 **{player}** 下线了"
            send_discord_message(message)

        last_known_players = current_online_players

    except requests.exceptions.HTTPError as http_err:
        print(f"{current_time()} HTTP Error: {http_err} (Status Code: {http_err.response.status_code})")
        if http_err.response.status_code == 404:
            print(f"{current_time()} 检查服务器地址是否正确：{SERVER_ADDRESS}")
    except requests.exceptions.Timeout:
        print(f"{current_time()} Error: 请求超时")
    except requests.exceptions.ConnectionError:
        print(f"{current_time()} Error: 连接到 {SERVER_ADDRESS} 失败。可能是网络问题或服务器地址不正确")
    except json.JSONDecodeError:
        print(f"{current_time()} Error: 无法解码API响应的JSON。API可能返回了非JSON内容")
    except Exception as e:
        print(f"{current_time()} Error: 检查玩家状态时发生未知错误: {e}")


def main():
    print(f"{current_time()} 监控 {SERVER_ADDRESS} 上的所有玩家...")
    print(f"{current_time()} 首次检查中，仅记录当前在线玩家")
    check_all_players_status_initial()
    print(f"{current_time()} 开始实时监控玩家上线和下线事件...")

    while True:
        check_all_players_status()
        time.sleep(CHECK_INTERVAL)


def check_all_players_status_initial():
    global last_known_players
    url = f"https://api.mcstatus.io/v2/status/java/{SERVER_ADDRESS}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("online"):
            if "players" in data and data["players"] and "list" in data["players"]:
                last_known_players = {p["name_clean"] for p in data["players"]["list"]}
                print(f"{current_time()} 初始在线玩家: {', '.join(last_known_players) if last_known_players else '无'}")
            else:
                print(f"{current_time()} 服务器 {SERVER_ADDRESS} 在线，但首次检查时无玩家信息")
                last_known_players = set()
        else:
            print(f"{current_time()} 服务器 {SERVER_ADDRESS} 首次检查时离线")
            last_known_players = set()
    except requests.exceptions.RequestException as e:
        print(f"{current_time()} 首次检查时发生网络或API错误: {e}")
    except json.JSONDecodeError:
        print(f"{current_time()} 首次检查时无法解码API响应的JSON")
    except Exception as e:
        print(f"{current_time()} 首次检查时发生未知错误: {e}")
    time.sleep(1)


if __name__ == "__main__":
    main()
