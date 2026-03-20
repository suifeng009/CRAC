import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
from datetime import datetime
import json
import os
import requests
import random
import urllib3
import sys
import winreg
import pystray
from PIL import Image, ImageDraw

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 获取路径：APP_DIR 用于存放配置文件和记录，RESOURCE_DIR 用于定位打包进 EXE 的图标资源
if getattr(sys, 'frozen', False):
    # 打包运行环境
    APP_DIR = os.path.dirname(sys.executable)
    RESOURCE_DIR = getattr(sys, '_MEIPASS', APP_DIR)
else:
    # 源代码运行环境
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    RESOURCE_DIR = APP_DIR
    
CONFIG_FILE = os.path.join(APP_DIR, 'config.json')
NOTIFIED_EXAMS_FILE = os.path.join(APP_DIR, 'notified_exams.json')
EXAM_LOG_FILE = os.path.join(APP_DIR, '已发现的考试记录.txt')
LOGO_ICON_PATH = os.path.join(RESOURCE_DIR, 'logo.ico')

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

class CRACMonitorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CRAC考试查询助手---XD (免登录极速版)")
        self.root.geometry("860x520")
        self.root.minsize(700, 500)
        
        # 居中显示窗口
        self.root.eval('tk::PlaceWindow . center')
        
        self.is_running = False
        self.monitor_thread = None
        self.tray_icon = None
        
        self.root.protocol('WM_DELETE_WINDOW', self.hide_window)
        
        self.init_ui()
        self.load_config()
        self.load_exam_history()

    def init_ui(self):
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # --- 配置区 ---
        config_frame = ttk.LabelFrame(main_frame, text="参数配置 (自动保存)", padding="10")
        config_frame.pack(fill=tk.X, pady=5)
        
        self.provinces_var = tk.StringVar(value="福建")
        self.cities_var = tk.StringVar()
        self.exam_type_var = tk.StringVar(value="")
        self.corpid_var = tk.StringVar()
        self.secret_var = tk.StringVar()
        self.agentid_var = tk.StringVar()
        
        # Grid 布局排版
        ttk.Label(config_frame, text="监控省份:").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Entry(config_frame, textvariable=self.provinces_var, width=18).grid(row=0, column=1, sticky=tk.EW, pady=4)
        ttk.Label(config_frame, text="(多省逗号分隔, 如:福建,浙江)", foreground="gray").grid(row=0, column=2, columnspan=2, sticky=tk.W, pady=4, padx=(15, 0))
        
        ttk.Label(config_frame, text="关注城市:").grid(row=1, column=0, sticky=tk.W, pady=4)
        ttk.Entry(config_frame, textvariable=self.cities_var, width=18).grid(row=1, column=1, sticky=tk.EW, pady=4)
        ttk.Label(config_frame, text="(留空代表全省，多个逗号分隔)", foreground="gray").grid(row=1, column=2, columnspan=2, sticky=tk.W, pady=4, padx=(15, 0))
        
        ttk.Label(config_frame, text="考试类别:").grid(row=2, column=0, sticky=tk.W, pady=4)
        type_frame = ttk.Frame(config_frame)
        type_frame.grid(row=2, column=1, columnspan=3, sticky=tk.W, pady=4)
        ttk.Radiobutton(type_frame, text="不限", variable=self.exam_type_var, value="").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(type_frame, text="A类", variable=self.exam_type_var, value="A").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(type_frame, text="B类", variable=self.exam_type_var, value="B").pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(config_frame, text="企微 CorpID:").grid(row=3, column=0, sticky=tk.W, pady=4)
        ttk.Entry(config_frame, textvariable=self.corpid_var, show="*").grid(row=3, column=1, columnspan=3, sticky=tk.EW, pady=4)
        
        ttk.Label(config_frame, text="企微 Secret:").grid(row=4, column=0, sticky=tk.W, pady=4)
        ttk.Entry(config_frame, textvariable=self.secret_var, show="*").grid(row=4, column=1, columnspan=3, sticky=tk.EW, pady=4)
        
        ttk.Label(config_frame, text="企微 AgentID:").grid(row=5, column=0, sticky=tk.W, pady=4)
        ttk.Entry(config_frame, textvariable=self.agentid_var, width=18).grid(row=5, column=1, sticky=tk.EW, pady=4)
        
        # 让输入框根据窗口拉伸自动填充
        config_frame.columnconfigure(1, weight=1)
        config_frame.columnconfigure(3, weight=1)
        
        # --- 控制区 ---
        control_frame = ttk.Frame(main_frame, padding="5")
        control_frame.pack(fill=tk.X, pady=10)
        
        self.btn_start = ttk.Button(control_frame, text="▶ 启动监控与自动巡检", command=self.start_monitor)
        self.btn_start.pack(side=tk.LEFT, padx=5, ipadx=10, ipady=3)
        
        self.btn_stop = ttk.Button(control_frame, text="⏹ 停止运行", command=self.stop_monitor, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=5, ipadx=10, ipady=3)

        self.btn_open_log = ttk.Button(control_frame, text="📂 历史发现", command=self.open_found_log)
        self.btn_open_log.pack(side=tk.LEFT, padx=5, ipadx=5, ipady=3)
        
        self.autostart_var = tk.BooleanVar(value=self.check_autostart())
        self.chk_autostart = ttk.Checkbutton(control_frame, text="开机自启(关闭隐藏)", variable=self.autostart_var, command=self.toggle_autostart)
        self.chk_autostart.pack(side=tk.LEFT, padx=5)
        
        self.status_label = ttk.Label(control_frame, text="状态: 闲置", foreground="gray", font=('Microsoft YaHei', 9, 'bold'))
        self.status_label.pack(side=tk.RIGHT, padx=5)

        # --- 底部并排展示区 ---
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.BOTH, expand=True, pady=2)

        # --- 日志区 (左侧) ---
        log_frame = ttk.LabelFrame(bottom_frame, text="运行动态与日志", padding="5")
        log_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, font=('Consolas', 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # --- 最新考试展示区 (右侧) ---
        latest_frame = ttk.LabelFrame(bottom_frame, text="🔔 最新匹配考试预警", padding="5")
        latest_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=(2, 0))
        
        self.latest_exam_text = scrolledtext.ScrolledText(latest_frame, wrap=tk.WORD, width=32, font=('Microsoft YaHei', 9), fg="red")
        self.latest_exam_text.insert(tk.END, "暂无新考试预警...")
        self.latest_exam_text.config(state=tk.DISABLED)
        self.latest_exam_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

    def open_found_log(self):
        if not os.path.exists(EXAM_LOG_FILE):
            with open(EXAM_LOG_FILE, 'w', encoding='utf-8') as f:
                f.write("=== CRAC 考试发现历史记录 ===\n\n")
        try:
            os.startfile(EXAM_LOG_FILE)
        except Exception as e:
            self.log(f"无法打开记录文件: {e}")

    def log(self, msg):
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        final_msg = f"[{time_str}] {msg}\n"
        def append_log():
            self.log_text.insert(tk.END, final_msg)
            self.log_text.see(tk.END)
        self.root.after(0, append_log)

    def check_autostart(self):
        try:
            key = winreg.HKEY_CURRENT_USER
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            registry_key = winreg.OpenKey(key, key_path, 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(registry_key, "CRACMonitor")
            winreg.CloseKey(registry_key)
            return True
        except FileNotFoundError:
            return False

    def toggle_autostart(self):
        enable = self.autostart_var.get()
        key = winreg.HKEY_CURRENT_USER
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "CRACMonitor"
        try:
            registry_key = winreg.OpenKey(key, key_path, 0, winreg.KEY_ALL_ACCESS)
            if enable:
                exe_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
                if getattr(sys, 'frozen', False):
                    cmd = f'"{exe_path}" --autostart'
                else:
                    cmd = f'"{sys.executable}" "{exe_path}" --autostart'
                winreg.SetValueEx(registry_key, app_name, 0, winreg.REG_SZ, cmd)
                self.log("✅ 已设置开机自动运行。")
            else:
                try:
                    winreg.DeleteValue(registry_key, app_name)
                    self.log("✅ 已取消开机自动运行。")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(registry_key)
        except Exception as e:
            self.log(f"⚠️ 设置开机启动失败: {e}")

    def hide_window(self):
        self.root.withdraw()
        if not self.tray_icon:
            threading.Thread(target=self.setup_tray, daemon=True).start()

    def show_window(self, icon, item):
        icon.stop()
        self.tray_icon = None
        self.root.after(0, self.root.deiconify)

    def quit_app(self, icon, item):
        icon.stop()
        self.is_running = False
        self.root.after(0, self.root.destroy)

    def setup_tray(self):
        if os.path.exists(LOGO_ICON_PATH):
            image = Image.open(LOGO_ICON_PATH)
        else:
            image = Image.new('RGB', (64, 64), color=(73, 109, 137))
            d = ImageDraw.Draw(image)
            d.text((10, 20), "CRAC", fill=(255, 255, 0))

        menu = pystray.Menu(
            pystray.MenuItem('显示界面', self.show_window, default=True),
            pystray.MenuItem('完全退出程序', self.quit_app)
        )
        self.tray_icon = pystray.Icon("CRACMonitor", image, "CRAC考试监控系统", menu)
        self.tray_icon.run()

    def load_exam_history(self):
        if os.path.exists(EXAM_LOG_FILE):
            try:
                with open(EXAM_LOG_FILE, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                if content:
                    if content.startswith("=== CRAC 考试发现历史记录 ==="):
                        content = content.replace("=== CRAC 考试发现历史记录 ===", "").strip()
                        
                    lines = content.split('\n')
                    if len(lines) > 40:
                        content = "... (以上为较早记录，请点击文件夹按钮查看)\n\n" + "\n".join(lines[-40:])
                        
                    if content.strip():
                        self.latest_exam_text.config(state=tk.NORMAL)
                        self.latest_exam_text.delete(1.0, tk.END)
                        self.latest_exam_text.insert(tk.END, content.strip())
                        self.latest_exam_text.see(tk.END)
                        self.latest_exam_text.config(state=tk.DISABLED)
            except Exception:
                pass

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                    self.provinces_var.set(cfg.get("provinces", "福建"))
                    self.cities_var.set(cfg.get("cities", ""))
                    self.exam_type_var.set(cfg.get("exam_type", ""))
                    self.corpid_var.set(cfg.get("corpid", ""))
                    self.secret_var.set(cfg.get("secret", ""))
                    self.agentid_var.set(cfg.get("agentid", ""))
                self.log("已加载上次的配置记录。")
            except Exception as e:
                self.log(f"⚠️ 读取配置失败: {e}")

    def save_config(self):
        cfg = {
            "provinces": self.provinces_var.get(),
            "cities": self.cities_var.get(),
            "exam_type": self.exam_type_var.get(),
            "corpid": self.corpid_var.get(),
            "secret": self.secret_var.get(),
            "agentid": self.agentid_var.get()
        }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=4)
        except Exception as e:
            self.log(f"⚠️ 保存配置失败: {e}")

    def start_monitor(self):
        self.save_config()
        self.is_running = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.status_label.config(text="● 运行中 (朝九晚五 10分钟/次)", foreground="green")
        
        self.monitor_thread = threading.Thread(target=self.run_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitor(self):
        self.is_running = False
        self.log("正在准备中止任务并退出休眠，请稍候...")
        self.btn_stop.config(state=tk.DISABLED)
        
        def wait_and_restore():
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.root.after(500, wait_and_restore)
            else:
                self.btn_start.config(state=tk.NORMAL)
                self.status_label.config(text="● 已停止", foreground="red")
                self.log("监控已完全停止。")
        self.root.after(500, wait_and_restore)

    def send_wechat_msg(self, content):
        corpid = self.corpid_var.get().strip()
        secret = self.secret_var.get().strip()
        agentid = self.agentid_var.get().strip()
        if not corpid or not secret or not agentid:
            self.log("⚠️ 企微推送参数不全，跳过推送。")
            return
            
        token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corpid}&corpsecret={secret}"
        try:
            res = requests.get(token_url, verify=False, timeout=10).json()
            if res.get('errcode') == 0:
                access_token = res.get('access_token')
                send_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
                payload = {
                    "touser": "@all",
                    "msgtype": "text",
                    "agentid": agentid,
                    "text": {"content": content},
                    "safe": 0
                }
                requests.post(send_url, json=payload, verify=False, timeout=10)
                self.log("✅ 企微推送成功！")
        except Exception as e:
            self.log(f"❌ 企微推送异常: {e}")

    def notify_desktop(self, title, msg):
        import winsound
        try:
            winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
        except:
            pass
            
        def show_msg():
            self.root.deiconify() 
            self.root.attributes('-topmost', True)
            self.root.attributes('-topmost', False)
            messagebox.showinfo(title, msg)
        self.root.after(0, show_msg)

    def fetch_province(self, province_name):
        target_cities = [c.strip() for c in self.cities_var.get().split(",") if c.strip()]
        target_type = self.exam_type_var.get()
        
        p_id = ""
        p_name = ""
        for name, id_val in PROVINCE_MAP.items():
            if province_name in name:
                p_id, p_name = id_val, name
                break
        if not p_id:
            self.log(f"⚠️ 未支持的省份名称或书写错误: {province_name}")
            return

        query_url = 'https://zhipu.allspectrum.cn:9528/CRAC/app/exam_exam/getExamList'
        payload = {"req": {"province": p_id, "page_no": 1, "page_size": 50, "type": target_type}, "req_meta": {"user_id": ""}}
        
        self.log(f"正在抓取【{p_name}】列表数据...")
        try:
            res = requests.post(query_url, headers=COMMON_HEADERS, json=payload, verify=False, timeout=10).json()
            
            if res.get("code") != 10000:
                self.log(f"❌ 接口请求失败 ({res.get('code')}): {res.get('msg')}")
                return

            exam_list = res.get("res", {}).get("list", [])
            history = []
            if os.path.exists(NOTIFIED_EXAMS_FILE):
                try:
                    with open(NOTIFIED_EXAMS_FILE, 'r') as f:
                        history = json.load(f)
                except:
                    pass

            found_new = False
            msg = f"📢 【{p_name}】发布新考试！\n"
            
            for exam in exam_list:
                eid = exam.get("id")
                if not eid or eid in history:
                    continue
                    
                exam_type = str(exam.get('type', ''))
                if target_type and target_type != exam_type:
                    continue
                    
                city = exam.get("city", {}).get("name", "未知")
                title = exam.get("adviceName", "")
                
                is_match = not target_cities
                if not is_match:
                    for t in target_cities:
                        if t in city or t in title:
                            is_match = True
                            break
                
                if is_match:
                    found_new = True
                    msg += (
                        f"\n⭐⭐ 报名时间: {exam.get('signUpStartDate', '未知')} ⭐⭐\n"
                        f"🎯 城市: {city} ({exam_type}类)\n"
                        f"⏰ 考试: {exam.get('examDate', '未知')}\n"
                        f"📍 地点: {exam.get('examArea', '未知')}\n"
                        f"📌 {title}\n"
                        f"{'-' * 20}"
                    )
                    history.append(eid)
            
            if found_new:
                self.send_wechat_msg(msg)
                with open(NOTIFIED_EXAMS_FILE, 'w') as f:
                    json.dump(history[-500:], f)
                
                self.log(f"💬 🚨发现【{p_name}】新匹配考试！详情如下：\n{msg}")
                
                time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                try:
                    with open(EXAM_LOG_FILE, 'a', encoding='utf-8') as f:
                        f.write(f"[{time_str}] 发现【{p_name}】新考试\n{msg}\n\n")
                except:
                    pass
                
                def update_latest():
                    self.latest_exam_text.config(state=tk.NORMAL)
                    self.latest_exam_text.delete(1.0, tk.END)
                    self.latest_exam_text.insert(tk.END, f"[{time_str}] 【{p_name}】发布:\n{msg}")
                    self.latest_exam_text.config(state=tk.DISABLED)
                self.root.after(0, update_latest)
                
                self.notify_desktop(f"🚨 发现【{p_name}】新考试", msg)
            else:
                self.log(f"👀 【{p_name}】暂无符合规则的新增考试。")
                
        except Exception as e:
            self.log(f"❌ 数据抓取中断: {str(e)}")

    def _sleep(self, seconds):
        """可被随时唤醒和中断的安全微秒级休眠"""
        steps = int(seconds * 10)
        for _ in range(steps):
            if not self.is_running:
                break
            time.sleep(0.1)

    def run_loop(self):
        self.log("🚀 监控中枢引擎启动成功 (免登录直连模式)！")
        is_first_run = True
        
        while self.is_running:
            now = datetime.now()
            # 【核心逻辑】只在 9:00 到 17:00 期间执行，若为首次开机则无条件允许一次提权检查
            if (9 <= now.hour < 17) or is_first_run:
                msg_time = "首次开机提权执行" if is_first_run and not (9 <= now.hour < 17) else "预定的 [朝九晚五] 时段"
                self.log(f"⏰ {now.strftime('%H:%M:%S')} 处于 {msg_time} ，启动本轮巡查...")
                
                provinces = [p.strip() for p in self.provinces_var.get().split(",") if p.strip()]
                for p in provinces:
                    if not self.is_running: break
                    self.fetch_province(p)
                    if p != provinces[-1]:
                        self.log("跨省缓冲节流中...")
                        self._sleep(random.uniform(5.0, 10.0))
                
                if not self.is_running: break
                
                is_first_run = False
                
                now = datetime.now()
                if not (9 <= now.hour < 17):
                    self.log("✅ 首次强制抓取完成！由于当前已非工作时间，回到交替挂起点...")
                    continue
                
                # 【核心逻辑】每过 10 分钟 (600秒) 获取一次数据
                wait_time = 600
                next_time = datetime.fromtimestamp(time.time() + wait_time)
                self.log(f"✅ 本轮巡检全部完成！进入休眠。预计下轮启动: {next_time.strftime('%H:%M:%S')}")
                self._sleep(wait_time)
                
            else:
                # 不在 9:00 - 17:00
                self.log(f"💤 当前时间 {now.strftime('%H:%M:%S')} 不在【朝九晚五】工作时间内，系统进入深度挂起状态...")
                # 每隔 5 分钟 (300秒) 醒来检查一次是否到了 9 点
                self._sleep(300)

if __name__ == "__main__":
    root = tk.Tk()
    # 设置窗口图标
    try:
        if os.path.exists(LOGO_ICON_PATH):
            root.iconbitmap(LOGO_ICON_PATH)
    except Exception:
        pass
    app = CRACMonitorGUI(root)
    
    if "--autostart" in sys.argv:
        # 触发自动启动并后台隐藏
        app.hide_window()
        app.root.after(1500, app.start_monitor)
        
    root.mainloop()
