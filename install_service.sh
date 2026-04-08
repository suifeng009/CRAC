#!/bin/bash

# ========================================================================
# 🌟 CRAC 考试查询助手 - Linux 服务级一键配置脚本 🌟
# ========================================================================

# 确保以 root/sudo 权限运行
if [ "$EUID" -ne 0 ]; then
  echo "❌ 请以 sudo 权限运行此脚本：sudo bash $0"
  exit 1
fi

PROJECT_DIR=$(cd "$(dirname "$0")"; pwd)
PROJECT_NAME="crac"
SERVICE_FILE="/etc/systemd/system/${PROJECT_NAME}.service"
USER_NAME=$(logname || echo $SUDO_USER || echo $USER)

echo "🔍 正在识别环境..."
echo "📂 项目路径: ${PROJECT_DIR}"
echo "👤 运行用户: ${USER_NAME}"

# --- [ 新增：安装前清理逻辑 ] ---
echo "🛑 正在清理旧版服务与进程..."
systemctl stop ${PROJECT_NAME}.service 2>/dev/null
pkill -f crac.py 2>/dev/null
echo "✅ 旧版进程已清理。"

# 验证 Python 环境
PYTHON_CMD=$(which python3)
if [ -z "$PYTHON_CMD" ]; then
    echo "❌ 错误: 未在系统中找到 python3"
    exit 1
fi

# 检查依赖项
echo "📦 检查 Python 依赖 (requests)..."
$PYTHON_CMD -c "import requests" &> /dev/null
if [ $? -ne 0 ]; then
    echo "⚠️ 正在安装依赖..."
    $PYTHON_CMD -m pip install requests urllib3 -i https://pypi.tuna.tsinghua.edu.cn/simple
fi

# 生成服务文件
echo "📝 自动生成系统服务配置文件..."
cat <<EOF > ${SERVICE_FILE}
[Unit]
Description=CRAC Exam Monitoring Service (Auto-Restart every 10 mins)
After=network.target

[Service]
Type=simple
User=${USER_NAME}
WorkingDirectory=${PROJECT_DIR}
ExecStart=${PYTHON_CMD} ${PROJECT_DIR}/crac.py
# 运行结束后自动重启（实现定时任务效果）
Restart=always
RestartSec=600

[Install]
WantedBy=multi-user.target
EOF

# 激活服务
echo "⚙️ 正在启用并启动服务..."
systemctl daemon-reload
systemctl enable ${PROJECT_NAME}.service

# --- [ 新增：首次运行提权标记 ] ---
touch ${PROJECT_DIR}/.first_run
chown ${USER_NAME}:${USER_NAME} ${PROJECT_DIR}/.first_run 2>/dev/null

systemctl restart ${PROJECT_NAME}.service

echo "========================================================================"
echo "✅ 配置完成！"
echo "ℹ️ 服务状态查看: systemctl status ${PROJECT_NAME}.service"
echo "ℹ️ 查看运行日志: journalctl -u ${PROJECT_NAME}.service -f"
echo "========================================================================"
