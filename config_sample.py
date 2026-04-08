
# --- [ 企业微信推送设置 ] ---
WECHAT_CORP_ID = ''     # 企业 ID (corpId)
WECHAT_SECRET = ''      # 自建应用 Secret
WECHAT_AGENT_ID = ''    # 自建应用 AgentId

# --- [ 钉钉推送设置 ] ---
DINGTALK_WEBHOOK = ''    # 钉钉机器人 Webhook URL
DINGTALK_SECRET = ''     # 钉钉机器人加签 Secret (选填，若钉钉未设置加签可留空)

# --- [ 监控规则设置 ] ---
TARGET_PROVINCES = ['福建']  # 监控省份列表，例如 ['福建', '上海']
TARGET_CITIES = []          # 监控城市列表，例如 ['泉州', '厦门']。留空 [] 则推送全省所有考试项目。
TARGET_EXAM_TYPE = ''       # 监控考试类别，例如 'A' 或 'B'。留空 '' 则表示不限。
