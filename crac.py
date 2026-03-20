#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
========================================================================
                        🌟 crac考试查询助手 (免登录极速版) 🌟
========================================================================

【简易使用教程】

1. 环境准备：
   - 确保安装了 Python 3。
   - 在终端/命令行运行：pip install requests (安装必需的网络库)。

2. 参数配置 (在下方的 [全局配置区] 修改)：
   - WECHAT_XXX: 填入你企业微信自建应用的 CorpID、Secret 和 AgentID。

3. 监控规则自定义：
   - TARGET_PROVINCES: 修改为你想要监控的省份，如 ['福建', '泉州']。
   - TARGET_CITIES: 填入关注的城市，如 ['泉州', '厦门']。
     * 特别注意：若设为空列表 []，则自动开启“全省模式”，推送该省所有考试。

4. 运行与测试：
   - 直接运行脚本即可：python crac.py。
   - 推送去重：脚本会自动生成 'notified_exams.json' 记录已推送的考试。
   - 强制重发测试：若想重复测试同一场考试，删掉该 json 文件即可。

5. 自动化部署 (推荐)：
   - 极简、轻量、完全免登录，0 封号风险，随便按你想要的频率执行即可。
========================================================================
"""

# ==========================================
# 🔻🔻🔻 全局配置区 🔻🔻🔻
# ==========================================
try:
    import config

    # --- [ 企业微信推送设置 ] ---
    WECHAT_CORP_ID = getattr(config, 'WECHAT_CORP_ID', '')
    WECHAT_SECRET = getattr(config, 'WECHAT_SECRET', '')
    WECHAT_AGENT_ID = getattr(config, 'WECHAT_AGENT_ID', '')

    # --- [ 监控规则设置 ] ---
    TARGET_PROVINCES = getattr(config, 'TARGET_PROVINCES', ['福建'])
    TARGET_CITIES = getattr(config, 'TARGET_CITIES', [])
except ImportError:
    print("⚠️ 未找到 config.py，使用脚本内置默认配置。")

    # --- [ 企业微信推送设置 ] ---
    WECHAT_CORP_ID = ''
    WECHAT_SECRET = ''
    WECHAT_AGENT_ID = ''

    # --- [ 监控规则设置 ] ---
    TARGET_PROVINCES = ['福建']
    TARGET_CITIES = []
# ==========================================
# 🔺🔺🔺 配置区结束 🔺🔺🔺
# ==========================================

import requests
import urllib3
import json
import time
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NOTIFIED_EXAMS_FILE = os.path.join(BASE_DIR, 'notified_exams.json')

PROVINCE_MAP = {
    "北京市": "8", "天津市": "25", "河北省": "42", "山西省": "222",
    "内蒙古自治区": "351", "辽宁省": "467", "吉林省": "582", "黑龙江省": "652",
    "上海市": "794", "江苏省": "811", "浙江省": "921", "安徽省": "1022",
    "福建省": "1144", "江西省": "1239", "山东省": "1351", "河南省": "1505",
    "湖北省": "1681", "湖南省": "1798", "广东省": "1935", "广西壮族自治区": "2079",
    "海南省": "2205", "重庆市": "2233", "四川省": "2272", "贵州省": "2477",
    "云南省": "2575", "西藏自治区": "2721", "陕西省": "2803", "甘肃省": "2921",
    "青海省": "3022", "宁夏回族自治区": "3075", "新疆维吾尔自治区": "3103",
    "台湾省": "3223", "香港特别行政区": "3224", "澳门特别行政区": "3225"
}

COMMON_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Content-Type': 'application/json'
}

def send_wechat_msg(content):
    if not WECHAT_CORP_ID or not WECHAT_SECRET or not WECHAT_AGENT_ID:
        print("⚠️ 未配置企业微信信息，跳过推送 (若不需要此功能可忽略)")
        return
        
    token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={WECHAT_CORP_ID}&corpsecret={WECHAT_SECRET}"
    try:
        res = requests.get(token_url, verify=False, timeout=10).json()
        if res.get('errcode') == 0:
            access_token = res.get('access_token')
            send_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
            payload = {
                "touser": "@all",
                "msgtype": "text",
                "agentid": WECHAT_AGENT_ID,
                "text": {"content": content},
                "safe": 0
            }
            requests.post(send_url, json=payload, verify=False, timeout=10)
            print("✅ 企微推送成功")
    except Exception as e:
        print(f"❌ 企微推送异常或网络错误: {e}")

def monitor_exams(province_input):
    p_id = ""
    p_name = ""
    for name, id_val in PROVINCE_MAP.items():
        if province_input in name:
            p_id, p_name = id_val, name
            break
    if not p_id:
        print(f"未能匹配省份: {province_input}")
        return

    query_url = 'https://zhipu.allspectrum.cn:9528/CRAC/app/exam_exam/getExamList'
    payload = {
        "req": {"province": p_id, "page_no": 1, "page_size": 50, "type": ""}, 
        "req_meta": {"user_id": ""}
    }
    
    print(f"正在抓取【{p_name}】列表数据...")
    try:
        res = requests.post(query_url, headers=COMMON_HEADERS, json=payload, verify=False, timeout=10).json()
        
        if res.get("code") != 10000:
            print(f"❌ 获取数据失败，接口返回: {res}")
            return

        exam_list = res.get("res", {}).get("list", [])
        history = []
        if os.path.exists(NOTIFIED_EXAMS_FILE):
            try:
                with open(NOTIFIED_EXAMS_FILE, 'r') as f:
                    history = json.load(f)
            except Exception as e:
                print(f"⚠️ 读取历史记录异常: {e}")

        found_new = False
        msg = f"📢 【{p_name}】发布新考试！\n"
        
        for exam in exam_list:
            eid = exam.get("id")
            if not eid or eid in history:
                continue
            city = exam.get("city", {}).get("name", "未知")
            title = exam.get("adviceName", "")
            is_match = not TARGET_CITIES
            if not is_match:
                for t in TARGET_CITIES:
                    if t in city or t in title:
                        is_match = True
                        break
            
            if is_match:
                found_new = True
                msg += (
                    f"\n⭐⭐ 报名时间: {exam.get('signUpStartDate', '未知')} ⭐⭐\n"
                    f"🎯 城市: {city} ({exam.get('type', '未知')}类)\n"
                    f"⏰ 考试: {exam.get('examDate', '未知')}\n"
                    f"📍 地点: {exam.get('examArea', '未知')}\n"
                    f"📌 {title}\n"
                    f"{'-' * 20}"
                )
                history.append(eid)
        
        if found_new:
            send_wechat_msg(msg)
            with open(NOTIFIED_EXAMS_FILE, 'w') as f:
                json.dump(history[-500:], f)
        else:
            print(f"👀 【{p_name}】暂无符合条件的新数据。")
            
    except Exception as e:
        print(f"❌ 抓取失败: {str(e)}")

if __name__ == '__main__':
    print("🚀 开始免登录抓取考试信息...")
    for idx, province in enumerate(TARGET_PROVINCES):
        monitor_exams(province)
        if idx < len(TARGET_PROVINCES) - 1:
            time.sleep(1.0) # 短暂延时即可