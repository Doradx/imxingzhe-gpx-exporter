"""
Author: Dorad, ddxi@qq.com
Date: 2024-07-11 11:21:36 +08:00
LastEditors: Dorad, ddxi@qq.com
LastEditTime: 2024-07-11 13:00:51 +08:00
FilePath: \run.py
Description: 

Copyright (c) 2024 by Dorad (ddxi@qq.com), All Rights Reserved.
"""

import os, datetime
import argparse
import requests
from lxml import html
import rsa, base64, json, logging
from dateutil.relativedelta import relativedelta


parser = argparse.ArgumentParser(description="行者GPX批量导出-Dorad")

# 用户名
parser.add_argument("-u", "--username", required=True, help="用户名")
# 密码
parser.add_argument("-p", "--password", required=True, help="密码")
# 同步近多少个月的数据
parser.add_argument(
    "-m", "--month", default=12, type=int, help="同步近N个月的数据，默认为12"
)
# 输出文件夹
parser.add_argument("-o", "--output", default="gpx", help="输出文件夹，默认为gpx")
# 是否覆盖已有文件
parser.add_argument("-f", "--force", action="store_true", help="是否覆盖已有文件")

args = parser.parse_args()

# log
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# 初始化session
session = requests.Session()

session.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
)

# 功能函数
def login(username, password):
    login_url = "https://www.imxingzhe.com/user/login"
    response = session.get(login_url)
    rd = response.cookies.get("rd")
    pubkey = html.fromstring(response.text).xpath('//textarea[@id="pubkey"]/text()')[0]
    logging.info("rd: %s", rd, "pubkey: %s", pubkey)
    # 采用RSA加密密码
    password_with_salt = password + ";" + rd
    safe_password = base64.b64encode(
        rsa.encrypt(
            password_with_salt.encode(),
            rsa.PublicKey.load_pkcs1_openssl_pem(pubkey.encode()),
        )
    ).decode()
    data = {"account": username, "password": safe_password, "source": "web"}
    response = session.post(
        "https://www.imxingzhe.com/api/v4/account/login",
        data=json.dumps(data),
        headers={
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en,zh-CN;q=0.9,zh;q=0.8,en-US;q=0.7",
            "Content-Type": "application/json",
            "Referer": "https://www.imxingzhe.com/",
            "Origin": "https://www.imxingzhe.com",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "sec-ch-ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Microsoft Edge";v="126"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        },
    )
    if response.status_code != 200 or response.json().get("error_code"):
        logging.warning("Login failed: %s", response.json())
        return
    logging.info("Login success: %s", response.json())
    # 获取用户信息
    user_info = response.json()["data"]
    logging.info("User info: %s", user_info)
    return user_info


# 获取月份记录
def _get_month_record(user_id, year, month):
    url = f"https://www.imxingzhe.com/api/v4/user_month_info/?user_id={user_id}&year={year}&month={month}"
    response = session.get(url)
    if response.status_code != 200 or response.json().get("error_code"):
        logging.warning("Get month record failed: %s", response.json())
        return
    logging.info("Get month record success: %s", response.json())
    return response.json()["data"]


# 下载GPX文件, 并保存到指定文件夹
def _download_gpx(activity_id, output_folder):
    url = f"https://www.imxingzhe.com/xing/{activity_id}/gpx/"
    response = session.get(url)
    if response.status_code != 200:
        logging.warning("Download GPX failed: %s", response.json())
        return
    # 保存文件
    gpx = response.text
    # 将文件保存到指定文件夹
    filename = os.path.join(output_folder, f"{activity_id}.gpx")
    # 检查文件夹是否存在
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(gpx)
    logging.info("Download GPX success: %s", filename)
    return filename


# 轮询下载
def download_activities(user_id, month=12, output_folder='gpx'):
    for m in range(month):
        date = datetime.datetime.now() - relativedelta(months=m)
        activity_list = _get_month_record(user_id, date.year, date.month)
        for activity in activity_list['wo_info']:
            _download_gpx(activity["id"], output_folder)
        logging.info("Download activities success: %s", date.strftime("%Y-%m"))
    return

# login
user_info = login(args.username, args.password)
download_activities(user_id=user_info["userid"], month=args.month, output_folder=args.output)

