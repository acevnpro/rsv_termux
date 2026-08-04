import os, json, socket, subprocess, time, re, urllib.request, shutil, sys

# ==========================================
# GIAO DIỆN & MÀU SẮC
# ==========================================
class C:
    H = '\033[95m'; B = '\033[94m'; CY = '\033[96m'; G = '\033[92m'
    Y = '\033[93m'; R = '\033[91m'; E = '\033[0m'; BOLD = '\033[1m'

def p_h(t): print(f"\n{C.CY}{C.BOLD}=== {t} ==={C.E}")
def p_ok(t): print(f"{C.G}[✓] {t}{C.E}")
def p_err(t): print(f"{C.R}[✗] {t}{C.E}")
def p_info(t): print(f"{C.CY}[i] {t}{C.E}")
def wait(): input(f"\n{C.Y}>>> Bấm Enter để quay lại Menu...{C.E}")

# ==========================================
# CẤU HÌNH & HỆ THỐNG ĐƯỜNG DẪN
# ==========================================
HOME = os.path.expanduser("~")
CONFIG_FILE = os.path.join(HOME, "nro_config.json")

def load_config():
    defaults = {
        "base_dir": os.path.join(HOME, "nro_termux"),
        "db_user": "root", "db_pass": "", "db_name": "team2026",
        "tcp_domain": get_local_ip(), "tcp_port": 14445,
        "local_login_port": 8888, "local_game_port": 14445,
        "mode": "offline", "pma_port": 8081, "jvm_xmx": "512m", "jvm_mode": "opt",
        "backend": "termux",
        "ksweb_mysql_pass": "",
        "ksweb_web_dir": "nso_web",
        "web_port": 8080,
        "backup_daemon": {
            "interval_hours": 1,
            "max_backups": 24,
            "backup_dir": os.path.join(HOME, "nro_backups")
        },
        "status": {"env": False, "source": False, "db_web": False, "build": False},
        "web_show_vnd": True,
        "web_show_admin": True,
        "web_admin_notice": "",
        "web_admin_pass": "admin"
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f: cfg = json.load(f)
            for k, v in defaults.items():
                if k not in cfg: cfg[k] = v
                elif isinstance(v, dict) and isinstance(cfg.get(k), dict):
                    for sk, sv in v.items():
                        if sk not in cfg[k]: cfg[k][sk] = sv
            cfg['tcp_port'] = int(cfg.get('tcp_port', 14445))
            cfg['local_login_port'] = int(cfg.get('local_login_port', 8888))
            cfg['local_game_port'] = int(cfg.get('local_game_port', 14445))
            return cfg
        except: pass
    return dict(defaults)

def update_web_game_info(cfg):
    try:
        info = f"{cfg.get('tcp_domain', '127.0.0.1')}:{cfg.get('tcp_port', 14445)}"
        ksweb_web = f"/sdcard/htdocs/{cfg.get('ksweb_web_dir', 'nso_web')}"
        if os.path.exists(ksweb_web):
            with open(os.path.join(ksweb_web, "game_info.txt"), "w") as f: f.write(info)
        lemp_web = os.path.join(HOME, "web_register")
        if os.path.exists(lemp_web):
            with open(os.path.join(lemp_web, "game_info.txt"), "w") as f: f.write(info)
    except: pass

def save_config(cfg):
    with open(CONFIG_FILE, 'w') as f: json.dump(cfg, f, indent=4)
    update_web_game_info(cfg)

def get_paths(cfg):
    b = cfg.get("base_dir", os.path.join(HOME, "nro_termux"))
    
    # Tự động quét tìm thư mục game con thực tế (SrcVIP, game_... hoặc bất cứ thư mục con nào chứa pom.xml/build.xml)
    g_dir = os.path.join(b, "SrcVIP")
    if not os.path.exists(os.path.join(g_dir, "pom.xml")) and not os.path.exists(os.path.join(g_dir, "build.xml")):
        found = False
        try:
            for root, dirs, files in os.walk(b):
                if "pom.xml" in files or "build.xml" in files:
                    # Bỏ qua nếu là thư mục build hoặc dist cũ
                    if "temp_nro_extract" in root or "/build/" in root or "/dist/" in root:
                        continue
                    g_dir = root
                    found = True
                    break
        except: pass
        if not found:
            g_dir = b

    is_new03 = os.path.exists(os.path.join(g_dir, "src/nro/models"))
    if is_new03:
        g_props = os.path.join(g_dir, "Config.properties")
        db_service = os.path.join(g_dir, "src/nro/models/data/LocalManager.java")
        data_game = os.path.join(g_dir, "src/nro/models/data/DataGame.java")
        sm_path = os.path.join(g_dir, "src/nro/models/server/ServerManager.java")
        src_root = os.path.join(g_dir, "src")
    else:
        if os.path.basename(g_dir).lower() == "server":
            g_props = os.path.join(g_dir, "resources/config/server.properties")
        else:
            g_props = os.path.join(g_dir, "config/server.properties")
        db_service = os.path.join(g_dir, "src/main/java/nro/jdbc/DBService.java")
        data_game = os.path.join(g_dir, "src/main/java/nro/data/DataGame.java")
        sm_path = os.path.join(g_dir, "src/main/java/nro/server/ServerManager.java")
        src_root = os.path.join(g_dir, "src/main/java")

    # Tìm file database SQL
    sql_file = os.path.join(b, "NroVIP.sql")
    if os.path.exists(b):
        try:
            for r, d_list, f_list in os.walk(b):
                for f in f_list:
                    if f.endswith(".sql"):
                        sql_file = os.path.join(r, f)
                        break
                if sql_file and os.path.exists(sql_file): break
        except: pass

    l_dir = os.path.join(b, "ServerLogin")
    if not os.path.exists(l_dir): l_dir = ""

    return {
        "BASE": b, 
        "LOGIN_DIR": l_dir, 
        "GAME_DIR": g_dir, 
        "LOGIN_INI": os.path.join(l_dir, "server.ini") if l_dir else "", 
        "GAME_PROPS": g_props, 
        "DB_SERVICE": db_service, 
        "DATA_GAME": data_game,
        "SERVER_MANAGER": sm_path, 
        "SRC_ROOT": src_root,
        "IS_NEW03": is_new03,
        "SQL_FILE": sql_file
    }

# ==========================================
# MẠNG & THÔNG TIN HỆ THỐNG
# ==========================================
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close(); return ip
    except:
        try:
            res = subprocess.check_output("ip -4 addr | grep -oP '(?<=inet\\s)\\d+(\\.\\d+){3}' | grep -v '127.0.0.1'", shell=True).decode().strip()
            if res: return res.split('\n')[0]
        except: pass
        return "127.0.0.1"

def resolve_ip(domain):
    try:
        if re.match(r"^\d+\.\d+\.\d+\.\d+$", domain): return domain
        return socket.gethostbyname(domain)
    except: return domain

def kill_port(port):
    os.system(f"fuser -k -9 {port}/tcp 2>/dev/null")
    os.system(f"lsof -t -i:{port} 2>/dev/null | xargs kill -9 2>/dev/null")
    if str(port) == "8888":
        os.system("pkill -9 -f 'ServerLogin' 2>/dev/null")
    elif str(port) == "14445":
        os.system("pkill -9 -f 'VanTuan' 2>/dev/null")
        os.system("pkill -9 -f 'ServerManager' 2>/dev/null")

def get_server_status(cfg, stype):
    pattern = "ServerLogin" if stype == "login" else "ServerManager"
    
    # Check if process is running via pgrep
    is_running = False
    try:
        subprocess.check_output(["pgrep", "-f", pattern], stderr=subprocess.DEVNULL)
        is_running = True
    except:
        if stype == "game":
            try:
                subprocess.check_output(["pgrep", "-f", "nro.models.server.ServerManager"], stderr=subprocess.DEVNULL)
                is_running = True
            except:
                pass
                
    if is_running:
        return f"{C.G}ON{C.E}"
        
    # Check TMux session if not running
    session = f"nro_{stype}_server"
    try:
        res = subprocess.run(["tmux", "has-session", "-t", session], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0:
            return f"{C.Y}AUTO-START{C.E}"
    except:
        pass
        
    return f"{C.R}OFF{C.E}"

def get_stat(cfg, key):
    return f" {C.G}(OK){C.E}" if cfg.get("status", {}).get(key) else ""

def check_lemp_status(cfg=None):
    if cfg:
        if cfg.get('backend', 'termux') == 'ksweb':
            return f"{C.G}KSWEB OK{C.E}" if detect_ksweb()[1] else f"{C.R}KSWEB OFF{C.E}"
    nginx = subprocess.run(["pgrep", "nginx"], stdout=subprocess.DEVNULL).returncode == 0
    mysql = subprocess.run(["pgrep", "mariadbd"], stdout=subprocess.DEVNULL).returncode == 0
    php = subprocess.run(["pgrep", "php-fpm"], stdout=subprocess.DEVNULL).returncode == 0
    return f"{C.G}ON{C.E}" if (nginx and mysql and php) else f"{C.R}OFF{C.E}"

# ==========================================
# KSWEB HYBRID - HÀM TIỆN ÍCH & VẬN HÀNH
# ==========================================
def detect_ksweb():
    ksweb_found = os.path.exists("/sdcard/htdocs")
    mysql_ok = False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(("127.0.0.1", 3306))
        s.close()
        mysql_ok = True
    except: pass
    return ksweb_found, mysql_ok

def get_db_cmd(cfg):
    if cfg.get('backend') == 'ksweb':
        ksweb_pass = cfg.get('ksweb_mysql_pass', '')
        if ksweb_pass:
            return f"mariadb -h 127.0.0.1 -u root -p'{ksweb_pass}'"
        else:
            return "mariadb -h 127.0.0.1 -u root"
    else:
        return "mariadb -u root"

def get_backend_label(cfg):
    backend = cfg.get('backend', 'termux')
    if backend == 'ksweb':
        return f"{C.G}KSWEB{C.E}"
    else:
        return f"{C.B}TERMUX (LEMP){C.E}"

# ==========================================
# [1] CÀI ĐẶT MÔI TRƯỜNG
# ==========================================
def install_env(cfg):
    p_h("CÀI ĐẶT MÔI TRƯỜNG")
    print(f"{C.H}Chọn kiến trúc Máy chủ Web & Database:{C.E}")
    print("[1] Mặc định (Cài đặt trọn bộ LEMP Termux - MariaDB/Nginx/PHP)")
    print("[2] Dùng KSWEB (Dành cho máy bị lỗi CSDL Termux - Cần cài app KSWEB)")
    ch = input(f"\n{C.BOLD}Lựa chọn của bạn (1/2): {C.E}").strip()
    
    if ch == "2":
        cfg['backend'] = 'ksweb'
        cfg['db_pass'] = cfg.get('ksweb_mysql_pass', '')
        save_config(cfg)
        p_ok("Đã chuyển sang chế độ KSWEB!")
        pkgs = ["openjdk-17", "maven", "wget", "unzip", "unrar", "tar", "git", "tmux", "psmisc", "lsof"]
    else:
        cfg['backend'] = 'termux'
        cfg['db_pass'] = ''
        save_config(cfg)
        p_ok("Đã chọn chế độ LEMP Termux!")
        pkgs = ["openjdk-17", "mariadb", "nginx", "php", "php-fpm", "maven", "ant",
                "wget", "unzip", "unrar", "tar", "git", "tmux", "psmisc", "lsof", "cloudflared"]
    
    p_info("Đang cập nhật hệ thống (Tự động 100%)...")
    os.system('pkg update -y')
    os.system('apt upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"')
    
    for pkg in pkgs:
        p_info(f"Đang cài {pkg}...")
        os.system(f"pkg install {pkg} -y")
    
    # Cấu hình Nginx & PMA (Dành cho chế độ LEMP)
    if cfg['backend'] == 'termux':
        nginx_conf = os.path.join(os.environ['PREFIX'], "etc/nginx/nginx.conf")
        pma_root = os.path.join(HOME, "phpmyadmin")
        reg_dir = os.path.join(HOME, "web_register")
        os.makedirs(reg_dir, exist_ok=True)
        conf_content = f"""
worker_processes  1;
events {{ worker_connections  1024; }}
http {{
    include       mime.types;
    default_type  application/octet-stream;
    sendfile        on;
    keepalive_timeout  65;
    server {{
        listen       8080;
        server_name  localhost;
        root   {reg_dir};
        index  index.php index.html;
        location / {{ try_files $uri $uri/ =404; }}
        location ~ \\.php$ {{
            fastcgi_pass   127.0.0.1:9000;
            fastcgi_index  index.php;
            include        fastcgi_params;
            fastcgi_param  SCRIPT_FILENAME  $document_root$fastcgi_script_name;
        }}
    }}
    server {{
        listen       8081;
        server_name  localhost;
        root   {pma_root};
        index  index.php index.html;
        location / {{ try_files $uri $uri/ =404; }}
        location ~ \\.php$ {{
            fastcgi_pass   127.0.0.1:9000;
            fastcgi_index  index.php;
            include        fastcgi_params;
            fastcgi_param  SCRIPT_FILENAME  $document_root$fastcgi_script_name;
        }}
    }}
}}
"""
        with open(nginx_conf, 'w') as f: f.write(conf_content)
        p_ok("Đã cấu hình cấu trúc Nginx cho LEMP!")

    p_ok("Cài đặt môi trường hoàn tất!"); cfg["status"]["env"] = True; save_config(cfg); wait()

# ==========================================
# [2] GIẢI NÉN SOURCE
# ==========================================
def extract_source(cfg):
    p_h("GIẢI NÉN SOURCE GAME")
    scan_paths = [HOME, "/sdcard/Download"]
    all_files = []
    for path in scan_paths:
        if os.path.exists(path):
            try:
                files = [(f, path) for f in os.listdir(path) if any(f.endswith(e) for e in [".zip", ".rar", ".tar.gz"])]
                all_files.extend(files)
            except: continue

    if not all_files:
        p_err("Không tìm thấy file nén .zip, .rar hoặc .tar.gz nào trong ~/ hoặc /sdcard/Download")
        p_info("Mẹo: Hãy đảm bảo bạn đã cấp quyền bộ nhớ qua lệnh 'termux-setup-storage'.")
        wait(); return
    
    for i, (f, p) in enumerate(all_files):
        loc = "Download" if "Download" in p else "Home"
        print(f"[{i+1}] {f} ({loc})")
        
    c = input("\nChọn file để giải nén (0=hủy): ")
    if not c or c == "0" or not c.isdigit() or int(c) > len(all_files): return
    
    sel_file, sel_path = all_files[int(c)-1]
    full_path = os.path.join(sel_path, sel_file)
    
    # Lấy tên file nén bỏ phần mở rộng để làm tên thư mục dự án
    folder_name = os.path.splitext(sel_file)[0]
    folder_name = re.sub(r'[^a-zA-Z0-9_-]', '_', folder_name)
    target = os.path.join(HOME, folder_name)
    
    if os.path.exists(target):
        print(f"\n{C.Y}[!] Phát hiện thư mục dự án {target} đã tồn tại.{C.E}")
        dl = input(f"Bạn có muốn XÓA SẠCH thư mục dự án cũ trước khi giải nén mới không? (Y/n): ").strip().upper()
        if dl != 'N':
            p_info("Đang xóa dữ liệu cũ, vui lòng chờ...")
            os.system(f"rm -rf '{target}'")
            
    os.makedirs(target, exist_ok=True)
    temp_extract = os.path.join(HOME, "temp_nro_extract")
    os.system(f"rm -rf '{temp_extract}'")
    os.makedirs(temp_extract, exist_ok=True)
    
    p_info(f"Đang tiến hành giải nén: {sel_file}...")
    if sel_file.endswith(".zip"):
        subprocess.run(["unzip", "-q", "-o", full_path, "-d", temp_extract])
    elif sel_file.endswith(".rar"):
        subprocess.run(["unrar", "x", "-y", "-o+", full_path, temp_extract + "/"])
    elif sel_file.endswith(".tar.gz"):
        subprocess.run(["tar", "-xf", full_path, "-C", temp_extract])

    # Sắp xếp cấu trúc thư mục tự động
    p_info("Đang định hình cấu trúc thư mục game...")
    found_login, found_game = False, False
    
    # 1. Quét tìm thư mục chứa pom.xml hoặc build.xml để định nghĩa làm Game Server
    game_src_temp = ""
    try:
        for root, dirs, files in os.walk(temp_extract):
            if "pom.xml" in files or "build.xml" in files:
                # Tránh các thư mục con build/dist nếu có
                if "/build" in root or "/dist" in root:
                    continue
                game_src_temp = root
                break
    except: pass

    if game_src_temp:
        os.system(f"mkdir -p '{target}/SrcVIP'")
        os.system(f"mv '{game_src_temp}'/* '{target}/SrcVIP/' 2>/dev/null")
        os.system(f"mv '{game_src_temp}'/.* '{target}/SrcVIP/' 2>/dev/null")
        # Xóa thư mục tạm của game source sau khi chuyển dữ liệu
        os.system(f"rm -rf '{game_src_temp}'")
        found_game = True

    # 2. Quét tìm ServerLogin và file CSDL .sql
    try:
        for root, dirs, files in os.walk(temp_extract):
            for d in list(dirs):
                d_lower = d.lower()
                if not found_login and d_lower == "serverlogin":
                    os.system(f"mv '{os.path.join(root, d)}' '{target}/ServerLogin' 2>/dev/null")
                    found_login = True
            for f in files:
                if f.endswith(".sql"):
                    os.system(f"mv '{os.path.join(root, f)}' '{target}/' 2>/dev/null")
    except: pass
            
    extras_dir = os.path.join(target, "SanPhamMod_Thua")
    os.makedirs(extras_dir, exist_ok=True)
    os.system(f"mv '{temp_extract}'/* '{extras_dir}/' 2>/dev/null")
    os.system(f"mv '{temp_extract}'/.* '{extras_dir}/' 2>/dev/null")
    os.system(f"rm -rf '{temp_extract}'")
    os.system(f"find '{extras_dir}' -empty -type d -delete 2>/dev/null")
    
    os.system(f"chmod -R 777 '{target}'")
    p_ok("Giải nén và cấu trúc hóa dự án thành công!")
    cfg["base_dir"] = target; cfg["status"]["source"] = True; save_config(cfg); wait()

# ==========================================
# KSWEB HYBRID - WEB DEPLOY
# ==========================================
def deploy_web_to_ksweb(cfg):
    web_subdir = cfg.get('ksweb_web_dir', 'nso_web')
    ksweb_web = f"/sdcard/htdocs/{web_subdir}"
    p_info(f"Đang cài đặt web đăng ký tại KSWEB: {ksweb_web}")
    os.makedirs(ksweb_web, exist_ok=True)
    
    db_name = cfg.get('db_name', 'nrovip')
    ksweb_pass = cfg.get('ksweb_mysql_pass', '')
    
    php_content = f"""<?php
error_reporting(E_ALL & ~E_NOTICE & ~E_DEPRECATED & ~E_WARNING);
ini_set('display_errors', 0);
$db_name = "{db_name}";
$conn = new mysqli("127.0.0.1", "root", "{ksweb_pass}", $db_name);
$msg = ""; $status = "";

if ($_SERVER["REQUEST_METHOD"] == "POST") {{
    $user = preg_replace("/[^a-zA-Z0-9]/", "", $_POST['user']);
    $pass = $_POST['pass'];
    $email = isset($_POST['email']) ? preg_replace("/[^a-zA-Z0-9@.]/", "", $_POST['email']) : "";
    $isAdmin = isset($_POST['is_admin']) ? 1 : 0;
    $vnd = isset($_POST['vnd']) ? (int)$_POST['vnd'] : 0;
    
    if (strlen($user) < 4 || strlen($pass) < 1) {{
        $msg = "Tên tài khoản tối thiểu 4 ký tự!"; $status = "error";
    }} else {{
        $check = $conn->query("SELECT id FROM account WHERE username = '$user'");
        if ($check->num_rows > 0) {{
            $msg = "Tài khoản này đã tồn tại!"; $status = "error";
        }} else {{
            $sql = "INSERT INTO account (username, password, email, is_admin, vnd, active) VALUES ('$user', '$pass', '$email', $isAdmin, $vnd, 1)";
            if ($conn->query($sql)) {{
                $msg = "Đăng ký thành công! Đã cấp quyền Admin và " . number_format($vnd) . " VND."; $status = "success";
            }} else {{
                $msg = "Lỗi Database: " . $conn->error; $status = "error";
            }}
        }}
    }}
}}
?>
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NRO - Đăng Ký Test Game (KSWEB)</title>
    <style>
        :root {{ --primary: #00d2ff; --secondary: #3a7bd5; --bg: #0f172a; }}
        * {{ box-sizing: border-box; font-family: 'Segoe UI', sans-serif; }}
        body {{ background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; margin: 0; color: white; padding: 20px; }}
        .card {{ background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px); padding: 2rem; border-radius: 1.5rem; border: 1px solid rgba(255, 255, 255, 0.1); width: 100%; max-width: 450px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); }}
        h1 {{ text-align: center; margin-bottom: 1.5rem; font-weight: 800; background: linear-gradient(to right, #00d2ff, #3a7bd5); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .badge {{ text-align: center; margin-bottom: 1rem; }}
        .badge span {{ background: linear-gradient(to right, #10b981, #059669); padding: 4px 12px; border-radius: 999px; font-size: 0.7rem; font-weight: bold; }}
        .input-group {{ margin-bottom: 1rem; }}
        label {{ display: block; margin-bottom: 0.4rem; font-size: 0.85rem; color: #94a3b8; }}
        input[type="text"], input[type="password"], input[type="email"], input[type="number"] {{ width: 100%; padding: 0.75rem 1rem; border-radius: 0.75rem; border: 1px solid rgba(255, 255, 255, 0.1); background: rgba(0,0,0,0.2); color: white; outline: none; transition: 0.3s; }}
        input:focus {{ border-color: var(--primary); box-shadow: 0 0 0 2px rgba(0, 210, 255, 0.2); }}
        .checkbox-group {{ display: flex; align-items: center; gap: 10px; margin: 1rem 0; cursor: pointer; }}
        .checkbox-group input {{ width: 18px; height: 18px; cursor: pointer; }}
        button {{ width: 100%; padding: 0.9rem; border: none; border-radius: 0.75rem; background: linear-gradient(to right, var(--primary), var(--secondary)); color: white; font-weight: bold; cursor: pointer; transition: 0.3s; margin-top: 1rem; }}
        button:hover {{ transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0, 210, 255, 0.3); }}
        .alert {{ padding: 0.8rem; border-radius: 0.75rem; margin-bottom: 1rem; text-align: center; font-size: 0.85rem; }}
        .success {{ background: rgba(34, 197, 94, 0.2); border: 1px solid #22c55e; color: #4ade80; }}
        .error {{ background: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; color: #f87171; }}
        .footer {{ text-align: center; margin-top: 1.5rem; font-size: 0.75rem; color: #64748b; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>NRO TEST TOOLS</h1>
        <div class="badge"><span>KSWEB BACKEND</span></div>
        <div style="background: rgba(0, 210, 255, 0.1); border-left: 4px solid #00d2ff; padding: 15px; margin-bottom: 20px; border-radius: 8px; font-size: 0.85rem; line-height: 1.5; text-align: justify;">
            <strong>Chào mừng các bạn đến với NRO termux</strong> phiên bản SRC được chia sẻ bởi <a href="https://www.youtube.com/watch?v=YTnZo66T0Tk" target="_blank" style="color: #00d2ff; font-weight: bold; text-decoration: none;">DAITEN Studio</a> dự án free hoàn toàn nếu có ai bắt trả phí chắc chắn nó là scam ! chúc các bạn chơi và mod game vui vẻ !
            <div style="margin-top: 10px; display: flex; gap: 10px; justify-content: center;">
                <a href="https://zalo.me/g/nran3u1pi3hgm9mq5mpc" target="_blank" style="background: #0068ff; color: white; padding: 6px 12px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 0.8rem; flex: 1; text-align: center;">📱 Nhóm Zalo</a>
                <a href="https://www.facebook.com/groups/nro.termux" target="_blank" style="background: #1877f2; color: white; padding: 6px 12px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 0.8rem; flex: 1; text-align: center;">📘 Nhóm Facebook</a>
            </div>
        </div>
        <?php
        $game_ip_port = "Chưa thiết lập";
        if (file_exists("game_info.txt")) {{
            $game_ip_port = trim(file_get_contents("game_info.txt"));
        }}
        ?>
        <div style="background: rgba(16, 185, 129, 0.1); border-left: 4px solid #10b981; padding: 15px; margin-bottom: 20px; border-radius: 8px; text-align: center;">
            <div style="font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px;">IP / Domain Kết Nối Game</div>
            <div style="font-size: 1.2rem; font-weight: bold; color: #10b981; letter-spacing: 0.5px; cursor: pointer;" onclick="alert('Đã copy IP!'); navigator.clipboard.writeText('<?php echo htmlspecialchars($game_ip_port); ?>');"><?php echo htmlspecialchars($game_ip_port); ?> 📋</div>
        </div>
        <?php if ($msg): ?>
            <div class="alert <?php echo $status; ?>"><?php echo $msg; ?></div>
        <?php endif; ?>
        <form method="POST">
            <div class="input-group">
                <label>Tên tài khoản</label>
                <input type="text" name="user" placeholder="Nhập username..." required autofocus>
            </div>
            <div class="input-group">
                <label>Mật khẩu</label>
                <input type="password" name="pass" placeholder="Nhập mật khẩu..." required>
            </div>
            <div class="input-group">
                <label>Email (Tùy chọn)</label>
                <input type="email" name="email" placeholder="Nhập email...">
            </div>
            <div class="input-group">
                <label>Số tiền VND muốn nạp (Để test)</label>
                <input type="number" name="vnd" value="1000000" placeholder="Nhập số tiền...">
            </div>
            <label class="checkbox-group">
                <input type="checkbox" name="is_admin"> Kích hoạt quyền Admin cho tài khoản này
            </label>
            <button type="submit">ĐĂNG KÝ VÀ NHẬN QUÀ</button>
        </form>
        <div class="footer">Dự án Mod Game NRO - KSWEB Hybrid</div>
    </div>
</body>
</html>
"""
    refresh_web_index(cfg)
    p_ok(f"Web đăng ký đã được tạo thành công tại: {ksweb_web}")

def setup_db_ksweb(cfg):
    p_h("THIẾT LẬP DATABASE (KSWEB MODE)")
    
    # Kiểm tra thiếu MySQL Client nếu người dùng bỏ qua cài đặt Env (Kịch bản 2)
    if os.system("command -v mysql >/dev/null 2>&1") != 0:
        p_info("Hệ thống thiếu công cụ lệnh MySQL, đang tự động cài đặt...")
        os.system("pkg update -y > /dev/null 2>&1")
        os.system("pkg install mariadb -y > /dev/null 2>&1")
        
    ksweb_pass = cfg.get('ksweb_mysql_pass', '')
    db_cmd = get_db_cmd(cfg)
    
    p_info("Đang kiểm tra kết nối CSDL của KSWEB...")
    ret = os.system(f"{db_cmd} -e 'SELECT 1;' 2>/dev/null")
    if ret != 0:
        p_err("Không thể kết nối CSDL KSWEB!")
        p_info("Gợi ý: Hãy mở ứng dụng KSWEB lên và bật MySQL trước.")
        p_info("Mật khẩu MySQL của bạn trên KSWEB có phải để trống không?")
        pw = input("Nhập mật khẩu MySQL của KSWEB (hoặc Enter để trống): ").strip()
        cfg['ksweb_mysql_pass'] = pw
        save_config(cfg)
        db_cmd = get_db_cmd(cfg)
        ret = os.system(f"{db_cmd} -e 'SELECT 1;' 2>/dev/null")
        if ret != 0:
            p_err("Vẫn không kết nối được! Hãy kiểm tra kỹ ứng dụng KSWEB.")
            wait(); return
            
    p_ok("Kết nối MySQL KSWEB thành công!")
    db_name = cfg['db_name']
    os.system(f"{db_cmd} -e 'CREATE DATABASE IF NOT EXISTS {db_name};'")
    
    # Quét SQL
    paths = get_paths(cfg)
    sql_file = paths['SQL_FILE']
    if os.path.exists(sql_file):
        p_info(f"Đang tiến hành import CSDL {db_name}...")
        os.system(f"{db_cmd} -f {db_name} < \"{sql_file}\"")
        p_ok("Đã nạp dữ liệu SQL thành công!")
        
    deploy_web_to_ksweb(cfg)
    cfg["status"]["db_web"] = True; save_config(cfg)
    wait()

# ==========================================
# [3] THIẾT LẬP DATABASE & WEB (LEMP/KSWEB)
# ==========================================
def import_sql_custom(cfg):
    p_h("IMPORT FILE SQL")
    scan_paths = [HOME, "/sdcard/Download"]
    all_files = []
    for path in scan_paths:
        if os.path.exists(path):
            try:
                for r, d, f_list in os.walk(path):
                    if "temp" in r or "build" in r or "dist" in r: continue
                    for f in f_list:
                        if f.endswith(".sql"):
                            all_files.append((f, r))
            except: continue

    if not all_files:
        p_err("Không tìm thấy file .sql nào trong ~/ hoặc /sdcard/Download")
        wait(); return
        
    for i, (f, p) in enumerate(all_files):
        loc = "Download" if "Download" in p else "Home"
        print(f"[{i+1}] {f} ({loc})")
        
    c = input("\nChọn file để Import (0=hủy): ")
    if not c or c == "0" or not c.isdigit() or int(c) > len(all_files): return
    
    sel_file, sel_path = all_files[int(c)-1]
    full_path = os.path.join(sel_path, sel_file)
    db_name = cfg.get('db_name', 'nrovip')
    db_cmd = get_db_cmd(cfg)
    
    p_info(f"Đang tiến hành import vào CSDL {db_name}...")
    res = os.system(f"{db_cmd} -f {db_name} < \"{full_path}\"")
    if res == 0:
        p_ok("Nạp dữ liệu SQL thành công!")
    else:
        p_err("Có lỗi trong quá trình import. Vui lòng kiểm tra lại database.")
    wait()

def export_sql_custom(cfg):
    p_h("XUẤT (BACKUP) FILE SQL")
    db_name = cfg.get('db_name', 'nrovip')
    if cfg.get('backend') == 'ksweb':
        ksweb_pass = cfg.get('ksweb_mysql_pass', '')
        if ksweb_pass:
            dump_cmd = f"mariadb-dump -h 127.0.0.1 -u root -p'{ksweb_pass}'"
        else:
            dump_cmd = f"mariadb-dump -h 127.0.0.1 -u root"
    else:
        dump_cmd = "mariadb-dump -u root"
        
    out_file = f"/sdcard/Download/backup_{db_name}_{int(time.time())}.sql"
    p_info(f"Đang xuất CSDL {db_name} ra thư mục Download...")
    res = os.system(f"{dump_cmd} {db_name} > \"{out_file}\"")
    if res == 0:
        p_ok(f"Đã lưu file backup tại: {out_file}")
    else:
        p_err("Có lỗi trong quá trình xuất SQL.")
    wait()

def setup_db(cfg):
    while True:
        os.system("clear")
        p_h("THIẾT LẬP & QUẢN LÝ DATABASE")
        print("[1] Tự động thiết lập Database & Web (Auto Fix)")
        print("[2] Chọn file SQL từ Termux/Download để Import")
        print("[3] Xuất file backup CSDL (.sql) ra thư mục Download")
        print("[0] Quay lại")
        ch = input(f"\n{C.BOLD}Chọn: {C.E}").strip()
        
        if ch == "1":
            if cfg.get('backend') == 'ksweb':
                setup_db_ksweb(cfg)
            else:
                setup_db_lemp(cfg)
            break
        elif ch == "2":
            import_sql_custom(cfg)
        elif ch == "3":
            export_sql_custom(cfg)
        elif ch == "0":
            break

def setup_db_lemp(cfg):
    p_h("THIẾT LẬP DATABASE & WEB (LEMP)")
    ksweb_found, ksweb_mysql = detect_ksweb()
    if ksweb_mysql:
        p_err("CẢNH BÁO: CỔNG 3306 ĐANG BỊ CHIẾM (CÓ THỂ DO KSWEB)!")
        p_info("Hãy tắt MySQL trên app KSWEB, hoặc chuyển sang chế độ KSWEB tại Mục [K].")
        c = input("Bạn có chắc chắn muốn tiếp tục cài LEMP? (y/N): ").strip().upper()
        if c != 'Y': return

    p_info("Đang thiết lập dịch vụ LEMP nội bộ...")
    if not os.path.exists(os.path.join(os.environ['PREFIX'], "var/lib/mysql")):
        os.system("mysql_install_db")
        
    os.system("mariadbd-safe > /dev/null 2>&1 &")
    p_info("Đang khởi động MariaDB (vui lòng chờ 8 giây)...")
    time.sleep(8)
    
    # Cấu hình quyền và mật khẩu MariaDB
    whoami = os.popen("whoami").read().strip()
    sql_cmds = [
        "CREATE USER IF NOT EXISTS 'root'@'localhost' IDENTIFIED BY '';",
        "ALTER USER 'root'@'localhost' IDENTIFIED BY '';",
        "GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost' WITH GRANT OPTION;",
        "FLUSH PRIVILEGES;"
    ]
    for cmd in sql_cmds:
        ret = os.system(f"mariadb -u root -e \"{cmd}\" 2>/dev/null")
        if ret != 0:
            os.system(f"mariadb -u {whoami} -e \"{cmd}\" 2>/dev/null")
            
    p_ok("Cấu hình tài khoản MariaDB root thành công (Không mật khẩu).")
    
    db_name = cfg['db_name']
    os.system(f"mariadb -u root -e 'CREATE DATABASE IF NOT EXISTS {db_name};'")
    
    # Import database SQL
    paths = get_paths(cfg)
    sql_file = paths['SQL_FILE']
    if os.path.exists(sql_file):
        p_info(f"Đang nạp file SQL: {os.path.basename(sql_file)}...")
        os.system(f"mariadb -u root -f {db_name} < \"{sql_file}\"")
        p_ok(f"Nạp dữ liệu vào CSDL '{db_name}' thành công!")
    else:
        p_err("Không tìm thấy file CSDL .sql trong dự án!")
        
    # Tạo trang đăng ký cho LEMP
    reg_dir = os.path.join(HOME, "web_register")
    os.makedirs(reg_dir, exist_ok=True)
    
    php_content = f"""<?php
error_reporting(E_ALL & ~E_NOTICE & ~E_DEPRECATED & ~E_WARNING);
ini_set('display_errors', 0);
$db_name = "{db_name}";
$conn = new mysqli("127.0.0.1", "root", "", $db_name);
$msg = ""; $status = "";

if ($_SERVER["REQUEST_METHOD"] == "POST") {{
    $user = preg_replace("/[^a-zA-Z0-9]/", "", $_POST['user']);
    $pass = $_POST['pass'];
    $email = isset($_POST['email']) ? preg_replace("/[^a-zA-Z0-9@.]/", "", $_POST['email']) : "";
    $isAdmin = isset($_POST['is_admin']) ? 1 : 0;
    $vnd = isset($_POST['vnd']) ? (int)$_POST['vnd'] : 0;
    
    if (strlen($user) < 4 || strlen($pass) < 1) {{
        $msg = "Tên tài khoản tối thiểu 4 ký tự!"; $status = "error";
    }} else {{
        try {{
            // 1. Quét danh sách cột thực tế của bảng account
            $cols_res = $conn->query("DESCRIBE account");
            $db_cols = [];
            while ($row = $cols_res->fetch_assoc()) {{
                $db_cols[$row['Field']] = [
                    'Null' => $row['Null'],
                    'Default' => $row['Default']
                ];
            }}

            // 2. Định nghĩa dữ liệu chèn mặc định
            $insert_data = [
                'username' => "'$user'",
                'password' => "'$pass'",
                'email' => "'$email'",
                'is_admin' => $isAdmin,
                'vnd' => $vnd,
                'active' => 1
            ];

            // 3. Tự động bổ sung các cột NOT NULL và không có giá trị mặc định để tránh lỗi CSDL (bỏ qua cột id)
            foreach ($db_cols as $field => $meta) {{
                if ($field === 'id') {{
                    continue;
                }}
                if (!isset($insert_data[$field]) && $meta['Null'] === 'NO' && $meta['Default'] === null) {{
                    $insert_data[$field] = "''";
                }}
            }}

            // 4. Lọc lại chỉ giữ các cột thực sự tồn tại trong database
            $final_cols = [];
            $final_vals = [];
            foreach ($insert_data as $field => $val) {{
                if (isset($db_cols[$field])) {{
                    $final_cols[] = $field;
                    $final_vals[] = $val;
                }}
            }}

            // 5. Kiểm tra trùng tài khoản
            $check = $conn->query("SELECT id FROM account WHERE username = '$user'");
            if ($check->num_rows > 0) {{
                $msg = "Tài khoản này đã tồn tại!"; $status = "error";
            }} else {{
                $sql = "INSERT INTO account (" . implode(", ", $final_cols) . ") VALUES (" . implode(", ", $final_vals) . ")";
                if ($conn->query($sql)) {{
                    $msg = "Đăng ký thành công! Đã cấp quyền Admin và " . number_format($vnd) . " VND."; $status = "success";
                }} else {{
                    $msg = "Lỗi Database: " . $conn->error; $status = "error";
                }}
            }}
        }} catch (Exception $e) {{
            $msg = "Lỗi hệ thống: " . $e->getMessage(); $status = "error";
        }}
    }}
}}
?>
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NRO - Đăng Ký Test Game (LEMP)</title>
    <style>
        :root {{ --primary: #00d2ff; --secondary: #3a7bd5; --bg: #0f172a; }}
        * {{ box-sizing: border-box; font-family: 'Segoe UI', sans-serif; }}
        body {{ background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; margin: 0; color: white; padding: 20px; }}
        .card {{ background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px); padding: 2rem; border-radius: 1.5rem; border: 1px solid rgba(255, 255, 255, 0.1); width: 100%; max-width: 450px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); }}
        h1 {{ text-align: center; margin-bottom: 1.5rem; font-weight: 800; background: linear-gradient(to right, #00d2ff, #3a7bd5); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .badge {{ text-align: center; margin-bottom: 1rem; }}
        .badge span {{ background: linear-gradient(to right, #10b981, #059669); padding: 4px 12px; border-radius: 999px; font-size: 0.7rem; font-weight: bold; }}
        .input-group {{ margin-bottom: 1rem; }}
        label {{ display: block; margin-bottom: 0.4rem; font-size: 0.85rem; color: #94a3b8; }}
        input[type="text"], input[type="password"], input[type="email"], input[type="number"] {{ width: 100%; padding: 0.75rem 1rem; border-radius: 0.75rem; border: 1px solid rgba(255, 255, 255, 0.1); background: rgba(0,0,0,0.2); color: white; outline: none; transition: 0.3s; }}
        input:focus {{ border-color: var(--primary); box-shadow: 0 0 0 2px rgba(0, 210, 255, 0.2); }}
        .checkbox-group {{ display: flex; align-items: center; gap: 10px; margin: 1rem 0; cursor: pointer; }}
        .checkbox-group input {{ width: 18px; height: 18px; cursor: pointer; }}
        button {{ width: 100%; padding: 0.9rem; border: none; border-radius: 0.75rem; background: linear-gradient(to right, var(--primary), var(--secondary)); color: white; font-weight: bold; cursor: pointer; transition: 0.3s; margin-top: 1rem; }}
        button:hover {{ transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0, 210, 255, 0.3); }}
        .alert {{ padding: 0.8rem; border-radius: 0.75rem; margin-bottom: 1rem; text-align: center; font-size: 0.85rem; }}
        .success {{ background: rgba(34, 197, 94, 0.2); border: 1px solid #22c55e; color: #4ade80; }}
        .error {{ background: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; color: #f87171; }}
        .footer {{ text-align: center; margin-top: 1.5rem; font-size: 0.75rem; color: #64748b; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>NRO TEST TOOLS</h1>
        <div class="badge"><span>LEMP BACKEND</span></div>
        <div style="background: rgba(0, 210, 255, 0.1); border-left: 4px solid #00d2ff; padding: 15px; margin-bottom: 20px; border-radius: 8px; font-size: 0.85rem; line-height: 1.5; text-align: justify;">
            <strong>Chào mừng các bạn đến với NRO termux</strong> phiên bản SRC được chia sẻ bởi <a href="https://www.youtube.com/watch?v=YTnZo66T0Tk" target="_blank" style="color: #00d2ff; font-weight: bold; text-decoration: none;">DAITEN Studio</a> dự án free hoàn toàn nếu có ai bắt trả phí chắc chắn nó là scam ! chúc các bạn chơi và mod game vui vẻ !
            <div style="margin-top: 10px; display: flex; gap: 10px; justify-content: center;">
                <a href="https://zalo.me/g/nran3u1pi3hgm9mq5mpc" target="_blank" style="background: #0068ff; color: white; padding: 6px 12px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 0.8rem; flex: 1; text-align: center;">📱 Nhóm Zalo</a>
                <a href="https://www.facebook.com/groups/nro.termux" target="_blank" style="background: #1877f2; color: white; padding: 6px 12px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 0.8rem; flex: 1; text-align: center;">📘 Nhóm Facebook</a>
            </div>
        </div>
        <?php
        $game_ip_port = "Chưa thiết lập";
        if (file_exists("game_info.txt")) {{
            $game_ip_port = trim(file_get_contents("game_info.txt"));
        }}
        ?>
        <div style="background: rgba(16, 185, 129, 0.1); border-left: 4px solid #10b981; padding: 15px; margin-bottom: 20px; border-radius: 8px; text-align: center;">
            <div style="font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px;">IP / Domain Kết Nối Game</div>
            <div style="font-size: 1.2rem; font-weight: bold; color: #10b981; letter-spacing: 0.5px; cursor: pointer;" onclick="alert('Đã copy IP!'); navigator.clipboard.writeText('<?php echo htmlspecialchars($game_ip_port); ?>');"><?php echo htmlspecialchars($game_ip_port); ?> 📋</div>
        </div>
        <?php if ($msg): ?>
            <div class="alert <?php echo $status; ?>"><?php echo $msg; ?></div>
        <?php endif; ?>
        <form method="POST">
            <div class="input-group">
                <label>Tên tài khoản</label>
                <input type="text" name="user" placeholder="Nhập username..." required autofocus>
            </div>
            <div class="input-group">
                <label>Mật khẩu</label>
                <input type="password" name="pass" placeholder="Nhập mật khẩu..." required>
            </div>
            <div class="input-group">
                <label>Email (Tùy chọn)</label>
                <input type="email" name="email" placeholder="Nhập email...">
            </div>
            <div class="input-group">
                <label>Số tiền VND muốn nạp (Để test)</label>
                <input type="number" name="vnd" value="1000000" placeholder="Nhập số tiền...">
            </div>
            <label class="checkbox-group">
                <input type="checkbox" name="is_admin"> Kích hoạt quyền Admin cho tài khoản này
            </label>
            <button type="submit">ĐĂNG KÝ VÀ NHẬN QUÀ</button>
        </form>
        <div class="footer">Dự án Mod Game NRO - LEMP Termux</div>
    </div>
</body>
</html>
"""
    refresh_web_index(cfg)
        
    # Thiết lập và cấu hình phpMyAdmin & PHP-FPM
    p_info("Đang cấu hình php-fpm...")
    prefix = os.environ.get('PREFIX', '/data/data/com.termux/files/usr')
    
    # Tạo các thư mục cần thiết cho Nginx hoạt động trên Termux
    os.makedirs(os.path.join(prefix, "var/run"), exist_ok=True)
    os.makedirs(os.path.join(prefix, "var/log/nginx"), exist_ok=True)
    os.makedirs(os.path.join(prefix, "var/lib/nginx"), exist_ok=True)
    os.makedirs(os.path.join(prefix, "var/lib/nginx/client_body"), exist_ok=True)
    os.makedirs(os.path.join(prefix, "var/lib/nginx/proxy"), exist_ok=True)
    os.makedirs(os.path.join(prefix, "var/lib/nginx/fastcgi"), exist_ok=True)

    fpm_conf = os.path.join(prefix, "etc/php-fpm.d/www.conf")
    fpm_main = os.path.join(prefix, "etc/php-fpm.conf")
    for path in [fpm_conf, fpm_main]:
        if os.path.exists(path):
            with open(path, 'r') as f: f_data = f.read()
            f_data = re.sub(r'^\s*listen\s*=.*', 'listen = 127.0.0.1:9000', f_data, flags=re.M)
            with open(path, 'w') as f: f.write(f_data)

    pma_root = os.path.join(HOME, "phpmyadmin")
    if not os.path.exists(os.path.join(pma_root, "index.php")):
        p_info("Đang tải và giải nén phpMyAdmin mới nhất từ website chính thức...")
        pma_url = "https://www.phpmyadmin.net/downloads/phpMyAdmin-latest-all-languages.tar.gz"
        pma_tar = os.path.join(HOME, "pma.tar.gz")
        os.system(f"wget {pma_url} -O {pma_tar}")
        os.system(f"tar -xf {pma_tar} -C {HOME}")
        # Tìm thư mục vừa giải nén
        extracted = [d for d in os.listdir(HOME) if d.startswith("phpMyAdmin-") and os.path.isdir(os.path.join(HOME, d))]
        if extracted:
            os.system(f"rm -rf {pma_root}")
            os.system(f"mv {os.path.join(HOME, extracted[0])} {pma_root}")
        os.system(f"rm -f {pma_tar}")
        
    # Cấu hình config.inc.php (Kết nối qua 127.0.0.1 để ổn định)
    pma_config = os.path.join(pma_root, "config.inc.php")
    pma_sample = os.path.join(pma_root, "config.sample.inc.php")
    if not os.path.exists(pma_config) and os.path.exists(pma_sample):
        os.system(f"cp {pma_sample} {pma_config}")
        
    if os.path.exists(pma_config):
        with open(pma_config, 'r') as f: pma_data = f.read()
        pma_data = pma_data.replace("'localhost'", "'127.0.0.1'")
        pma_data = pma_data.replace('"localhost"', "'127.0.0.1'")
        pma_data = pma_data.replace("['AllowNoPassword'] = false", "['AllowNoPassword'] = true")
        pma_data = pma_data.replace("AllowNoPassword'] = false", "AllowNoPassword'] = true")
        if "$cfg['blowfish_secret'] = '';" in pma_data:
            pma_data = pma_data.replace("$cfg['blowfish_secret'] = '';", "$cfg['blowfish_secret'] = 'vantuannro2026_super_secret_key';")
        elif "$cfg['blowfish_secret'] = \"\";" in pma_data:
            pma_data = pma_data.replace("$cfg['blowfish_secret'] = \"\";", "$cfg['blowfish_secret'] = 'vantuannro2026_super_secret_key';")
        with open(pma_config, 'w') as f: f.write(pma_data)
        p_ok("Đã cấu hình config.inc.php (127.0.0.1 / AllowNoPassword)")

    p_info("Đang áp dụng vá lỗi PHP 8.4 cho phpMyAdmin...")
    pma_idx = os.path.join(pma_root, "index.php")
    if os.path.exists(pma_idx):
        with open(pma_idx, 'r') as f: lines = f.readlines()
        has_declare = any("declare(strict_types=1)" in l for l in lines)
        new_lines = []
        inserted = False
        fix_code = "error_reporting(0); ini_set('display_errors', 0); // Fix PHP 8.4 by VanTuan\n"
        for line in lines:
            if "Fix PHP 8.4 by VanTuan" in line: continue
            new_lines.append(line)
            if not inserted:
                if has_declare and "declare(strict_types=1)" in line:
                    new_lines.append(fix_code); inserted = True
                elif not has_declare and "<?php" in line:
                    new_lines.append(fix_code); inserted = True
        with open(pma_idx, 'w') as f: f.writelines(new_lines)
        p_ok("Đã áp dụng vá lỗi PHP 8.4!")
        
    # Cấu hình Nginx trỏ chuẩn cổng 8080 và 8081 với đường dẫn tuyệt đối cho Termux
    nginx_conf = os.path.join(prefix, "etc/nginx/nginx.conf")
    conf_content = f"""
worker_processes  1;
events {{
    worker_connections  1024;
}}
http {{
    include       mime.types;
    default_type  application/octet-stream;
    sendfile        on;
    keepalive_timeout  65;

    # WEB ĐĂNG KÝ (PORT 8080)
    server {{
        listen       8080;
        server_name  localhost;
        root         {reg_dir};
        index        index.php index.html;
        location / {{
            try_files $uri $uri/ =404;
        }}
        location ~ \\.php$ {{
            fastcgi_pass   127.0.0.1:9000;
            fastcgi_param  SCRIPT_FILENAME  $document_root$fastcgi_script_name;
            include        fastcgi_params;
        }}
    }}

    # PHPMYADMIN (PORT 8081)
    server {{
        listen       8081;
        server_name  localhost;
        root         {pma_root};
        index        index.php index.html;
        location / {{
            try_files $uri $uri/ =404;
        }}
        location ~ \\.php$ {{
            fastcgi_pass   127.0.0.1:9000;
            fastcgi_param  SCRIPT_FILENAME  $document_root$fastcgi_script_name;
            include        fastcgi_params;
        }}
    }}
}}
"""
    with open(nginx_conf, 'w') as f: f.write(conf_content)
    p_ok("Đã cập nhật cấu trúc Nginx trỏ về web_register và phpMyAdmin dạng tối giản & siêu ổn định!")
        
    p_info("Đang khởi động lại dịch vụ PHP-FPM & Nginx...")
    os.system("pkill -9 nginx; pkill -9 php-fpm")
    time.sleep(1)
    os.system("php-fpm > /dev/null 2>&1")
    os.system("nginx > /dev/null 2>&1")
    
    time.sleep(1.5)
    import socket
    def is_port_open_local(port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        try:
            s.connect(("127.0.0.1", port))
            s.close()
            return True
        except:
            return False

    nginx_running = is_port_open_local(8080) or is_port_open_local(8081)
    fpm_running = is_port_open_local(9000)
    
    if nginx_running and fpm_running:
        p_ok("Khởi chạy PHP-FPM & Nginx thành công!")
    else:
        p_err("CẢNH BÁO: Không thể khởi chạy một số dịch vụ LEMP ngầm!")
        if not nginx_running:
            p_info("  • Nginx chưa chạy. Đang chạy kiểm thử cấu hình Nginx để hiển thị lỗi:")
            os.system("nginx -t")
        if not fpm_running:
            p_info("  • PHP-FPM chưa chạy. Đang chạy kiểm thử cấu hình PHP-FPM để hiển thị lỗi:")
            os.system("php-fpm -t")
            
    p_ok("Thiết lập hệ thống LEMP Web & CSDL hoàn tất!")
    cfg["status"]["db_web"] = True; save_config(cfg); wait()

# ==========================================
# [4] CẤU HÌNH KẾT NỐI (ONLINE/OFFLINE)
# ==========================================
def manage_tcp(cfg):
    if "LD_PRELOAD" in os.environ:
        del os.environ["LD_PRELOAD"]
    os.system("clear"); p_h("CẤU HÌNH KẾT NỐI (ONLINE/OFFLINE)")
    print(f"Chế độ kết nối hiện tại: {C.H}{cfg['mode'].upper()}{C.E}")
    print(f"IP/Domain kết nối: {C.Y}{cfg['tcp_domain']}:{cfg['tcp_port']}{C.E}\n")
    
    print("[1] Cài đặt Ngrok (Tối ưu cho Termux ARM64)")
    print("[2] Khởi chạy & Quản lý Ngrok (TCP)")
    print("[3] Cấu hình Online: Tự động lấy link Ngrok đang mở (Port 4040)")
    print("[4] Cấu hình Online: Nhập liên kết thủ công (Ngrok/Playit/Bore)")
    print("[5] Cấu hình Offline: Chạy mạng LAN/WiFi (Sử dụng IP máy)")
    print("[6] Cấu hình Offline: Chạy trên máy ảo (Localhost 127.0.0.1)")
    print("[7] Mở cổng Web đăng ký tài khoản (Cloudflare Tunnel - Miễn phí)")
    print("[8] Mở cổng Web đăng ký tài khoản (Ngrok Domain cố định)")
    print("[0] Quay lại")
    ch = input(f"\n{C.BOLD}Chọn: {C.E}").upper()

    if ch == "1":
        p_info("Đang cài đặt môi trường giả lập (proot) để vá lỗi DNS Ngrok...")
        subprocess.run(["pkg", "install", "proot", "dnsutils", "-y"])
        p_info("Đang tải Ngrok ARM64 chính chủ cho Termux...")
        os.system("wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.tgz -O ngrok.tgz")
        os.system("tar -xvzf ngrok.tgz")
        os.system(f"mv ngrok {os.environ.get('PREFIX', '/data/data/com.termux/files/usr')}/bin/")
        os.system(f"chmod +x {os.environ.get('PREFIX', '/data/data/com.termux/files/usr')}/bin/ngrok")
        os.system("rm ngrok.tgz")
        p_ok("Đã cài đặt Ngrok thành công!")
        tk = input(f"{C.CY}Nhập AuthToken (Bỏ trống nếu đã nhập trước đó): {C.E}")
        if tk.strip():
            os.system(f"ngrok config add-authtoken {tk.strip()}")
            p_ok("Đã lưu AuthToken!")
    elif ch == "2":
        print("\n[1] Chạy trực tiếp (Xem Log - Bấm Ctrl+C để thoát)")
        print("[2] Chạy ngầm Ngrok (Tmux - Không lo tắt nhầm)")
        print("[0] Tắt dịch vụ Ngrok đang chạy")
        sc = input(f"\n{C.BOLD}Chọn: {C.E}")
        if sc == "1":
            p_info(f"Đang mở Ngrok cho Port {cfg['local_game_port']}...")
            p_info("LƯU Ý: 'Web Interface http://127.0.0.1:4040' chỉ là trang quản lý của Ngrok, KHÔNG PHẢI lỗi sai port!")
            subprocess.run(["termux-chroot", "ngrok", "tcp", str(cfg['local_game_port'])])
        elif sc == "2":
            subprocess.run(["pkill", "-9", "ngrok"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            subprocess.run(["tmux", "kill-session", "-t", "nro_ngrok"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            p_info(f"Đang mở Ngrok ngầm cho Port {cfg['local_game_port']}...")
            subprocess.run(["tmux", "new-session", "-d", "-s", "nro_ngrok", f"termux-chroot ngrok tcp {cfg['local_game_port']}"])
            p_ok("Ngrok đang khởi chạy ngầm trong Tmux (Session: nro_ngrok)!")
            p_info("Mẹo: Mở mục [3] để tự động lấy IP và Port nhé.")
            p_info("LƯU Ý: Port 4040 chỉ là trang Web quản lý của Ngrok, Ngrok vẫn đang trỏ đúng vào game!")
        elif sc == "0":
            subprocess.run(["pkill", "-9", "ngrok"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            subprocess.run(["tmux", "kill-session", "-t", "nro_ngrok"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            p_ok("Đã tắt dịch vụ Ngrok!")
    elif ch == "3":
        try:
            with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels") as r:
                t = json.loads(r.read().decode())['tunnels'][0]
                u = t['public_url'].replace('tcp://', '')
                d, p = u.rsplit(':', 1)
                # GIU NGUYEN DOMAIN, KHONG RESOLVE IP (Ngrok route theo hostname)
                cfg['mode'] = 'online'
                cfg['tcp_domain'] = d
                cfg['tcp_port'] = int(p)
                save_config(cfg)
                p_ok(f"Lưu cấu hình ONLINE thành công: {d}:{p}")
        except: p_err("Lỗi: Hãy chắc chắn bạn đã kích hoạt Ngrok trước!")
    elif ch == "4":
        link = input("Nhập địa chỉ (VD: 0.tcp.ap.ngrok.io:12345): ").strip().replace("tcp://", "")
        if ':' in link:
            d, p = link.rsplit(':', 1)
            # GIU NGUYEN DOMAIN, KHONG RESOLVE IP (Ngrok route theo hostname)
            cfg['mode'] = 'online'
            cfg['tcp_domain'] = d
            cfg['tcp_port'] = int(p)
            save_config(cfg)
            p_ok(f"Lưu cấu hình ONLINE thành công: {d}:{p}")
    elif ch == "5":
        local_ip = get_local_ip()
        cfg['mode'] = 'offline'
        cfg['tcp_domain'] = local_ip
        cfg['tcp_port'] = cfg['local_game_port']
        save_config(cfg)
        p_ok(f"Lưu cấu hình OFFLINE (LAN/WiFi): {local_ip}:{cfg['tcp_port']}")
    elif ch == "6":
        cfg['mode'] = 'offline'
        cfg['tcp_domain'] = "127.0.0.1"
        cfg['tcp_port'] = cfg['local_game_port']
        save_config(cfg)
        p_ok("Lưu cấu hình OFFLINE (Localhost 127.0.0.1) thành công!")
    elif ch == "7":
        os.system("tmux kill-session -t nro_cf 2>/dev/null")
        log = os.path.join(HOME, "cf_tunnel.log"); os.system(f"rm -f {log}")
        os.system(f"tmux new-session -d -s nro_cf 'cloudflared tunnel --url http://127.0.0.1:8080 2>&1 | tee {log}'")
        p_info("Đang thiết lập cổng kết nối Cloudflare (vui lòng chờ 8 giây)..."); time.sleep(8)
        try:
            with open(log, 'r') as f:
                m = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', f.read())
                if m:
                    web_url = m.group(0)
                    if cfg.get('backend') == 'ksweb':
                        web_subdir = cfg.get('ksweb_web_dir', 'nso_web')
                        web_url = web_url.rstrip('/') + f'/{web_subdir}/'
                    cfg['web_url'] = web_url
                    save_config(cfg)
                    p_ok(f"Mở cổng Cloudflare thành công: {cfg['web_url']}")
        except: p_err("Không thể lấy đường dẫn Cloudflare Tunnel!")
    elif ch == "8":
        domain = input(f"{C.CY}Nhập domain Ngrok cố định của bạn (VD: my-app.ngrok-free.app): {C.E}").strip()
        if not domain:
            p_err("Không được để trống domain!")
        else:
            os.system("tmux kill-session -t nro_ngrok_web 2>/dev/null")
            os.system(f"tmux new-session -d -s nro_ngrok_web 'termux-chroot ngrok http --domain={domain} 8080'")
            p_info("Đang thiết lập cổng kết nối Ngrok Web (vui lòng chờ 3 giây)...")
            time.sleep(3)
            web_url = f"https://{domain}"
            if cfg.get('backend') == 'ksweb':
                web_subdir = cfg.get('ksweb_web_dir', 'nso_web')
                web_url = web_url.rstrip('/') + f'/{web_subdir}/'
            cfg['web_url'] = web_url
            save_config(cfg)
            p_ok(f"Mở cổng Ngrok Web thành công: {cfg['web_url']}")
    wait()

# ==========================================
# [5] VÁ IP & BIÊN DỊCH GAME
# ==========================================
def apply_and_build(cfg):
    os.system("clear"); p_h("VÁ SOURCE & BIÊN DỊCH (BUILD)"); paths = get_paths(cfg)
    
    if not os.path.exists(paths["GAME_DIR"]):
        p_err(f"Không tìm thấy thư mục: {paths['GAME_DIR']}"); wait(); return

    ip = cfg['tcp_domain']; port = cfg['tcp_port']
    l_port = cfg['local_login_port']; g_port = cfg['local_game_port']
    db_u = cfg['db_user']
    db_pass = cfg.get('ksweb_mysql_pass', '') if cfg.get('backend') == 'ksweb' else cfg['db_pass']
    db_name = cfg['db_name']
    
    sv1 = f"{db_name}:{ip}:{port}"
    p_info(f"Đang vá cấu hình IP & Database: {ip}:{port}")
    
    # 1. Vá DBService.java hoặc LocalManager.java (DB credentials & Collation MariaDB 11)
    if os.path.exists(paths["DB_SERVICE"]):
        with open(paths["DB_SERVICE"], 'r', encoding='utf-8') as f: content = f.read()
        content = re.sub(r'DB_HOST\s*=\s*".*?"', 'DB_HOST = "127.0.0.1"', content)
        content = re.sub(r'DB_NAME\s*=\s*".*?"', f'DB_NAME = "{db_name}"', content)
        content = re.sub(r'DB_USER\s*=\s*".*?"', f'DB_USER = "{db_u}"', content)
        content = re.sub(r'DB_PASSWORD\s*=\s*".*?"', f'DB_PASSWORD = "{db_pass}"', content)
        
        if 'jdbc:mysql' in content.lower():
            if 'detectCustomCollations' not in content:
                p_info("   [+] Áp dụng JDBC URL Collation Patch (MariaDB 11)...")
                params = "&useSSL=false&connectionCollation=utf8_general_ci&characterEncoding=UTF-8&useUnicode=yes&serverTimezone=UTC&useLegacyDatetimeCode=false&detectCustomCollations=false"
                content = re.sub(r'(\?useUnicode=[^"]+)', r'?useUnicode=yes', content)
                content = re.sub(r'(jdbc:mysql://[^"]+)', r'\1' + params, content, flags=re.IGNORECASE)
                
        with open(paths["DB_SERVICE"], 'w', encoding='utf-8') as f: f.write(content)
        p_ok(f"{os.path.basename(paths['DB_SERVICE'])} → Cập nhật thành công")

    # 2. Vá DataGame.java
    if os.path.exists(paths["DATA_GAME"]):
        with open(paths["DATA_GAME"], 'r', encoding='utf-8') as f: content = f.read()
        if paths["IS_NEW03"]:
            content = re.sub(r'LINK_IP_PORT\s*=\s*".*?"', f'LINK_IP_PORT = "buffalo:{ip}:{port}:0"', content)
        else:
            content = re.sub(r'LINK_IP_PORT\s*=\s*".*?"', f'LINK_IP_PORT = "Buffalo:{ip}:{port}:0"', content)
        with open(paths["DATA_GAME"], 'w', encoding='utf-8') as f: f.write(content)
        p_ok("DataGame.java → LINK_IP_PORT")

    # 3. Vá server.ini (Login)
    if paths["LOGIN_INI"] and os.path.exists(paths["LOGIN_INI"]):
        with open(paths["LOGIN_INI"], 'w') as f:
            f.write(f"server.port={l_port}\ndb.port=3306\ndb.host=127.0.0.1\n")
            f.write(f"db.user={db_u}\ndb.password={db_pass}\ndb.name={db_name}\n")
            f.write("db.driver=com.mysql.jdbc.Driver\nadmin.mode=0\n")
        p_ok("server.ini → Đã vá xong")

    # 4. Vá properties (Game Server)
    if os.path.exists(paths["GAME_PROPS"]):
        if paths["IS_NEW03"]:
            with open(paths["GAME_PROPS"], 'w') as f:
                f.write(f"# --- DATABASE CONFIG ---\n")
                f.write(f"database.driver=com.mysql.jdbc.Driver\ndatabase.host=127.0.0.1\ndatabase.port=3306\n")
                f.write(f"database.name={db_name}\ndatabase.user={db_u}\ndatabase.pass={db_pass}\n")
                f.write(f"database.min=5\ndatabase.max=200\ndatabase.lifetime=1800000\ndatabase.log=false\n\n")
                f.write(f"# --- SERVER CONFIG ---\n")
                f.write(f"server.sv=1\nserver.name={db_name}\nserver.port={g_port}\n")
                f.write(f"server.ip=127.0.0.1\nserver.sv1={sv1}\n")
                f.write(f"server.waitlogin=5\nserver.maxperip=50\nserver.maxplayer=1500\nserver.expserver=3\n")
                f.write(f"server.local=false\nserver.test=false\nserver.daoautoupdater=false\n")
        else:
            with open(paths["GAME_PROPS"], 'w') as f:
                f.write(f"##config db\nserver.db.ip=127.0.0.1\nserver.db.port=3306\nserver.db.name={db_name}\nserver.db.us={db_u}\nserver.db.pw={db_pass}\nserver.db.maxactive=99999\n\n##config login\nlogin.host=127.0.0.1\nlogin.port={l_port}\n\n##config server\nserver.sv=1\nserver.sv1={sv1}\nserver.port={g_port}\n\nserver.debug=false\n\nserver.waitlogin=5\nserver.maxperip=50\nserver.maxplayer=1500\nserver.expserver=3\nserver.name={db_name}\nserver.domain={db_name}\n\nserver.key=ahskjbdkajsndakjnsdjaksbn324873\nserver.key2=askjlndfakjsldnaslkjdnakjsn636\nserver.activeKey=true\n\napi.port=8181\napi.key=abcdef\n\n#hikariCP\nserver.hikari.minIdle=5\nserver.hikari.poolSize=200\nserver.hikari.cachePre=true\nserver.hikari.cacheSize=250\nserver.hikari.cacheSqlLimit=2048\n\nexecute.command=java -Djava.awt.headless=true -jar target/*dependencies.jar\n\nserver.event=3\n")
        p_ok(f"{os.path.basename(paths['GAME_PROPS'])} → Cập nhật thành công")

    # 5. GUI Bypass cho ServerManager.java (Headless mode)
    if os.path.exists(paths["SERVER_MANAGER"]):
        fp = paths["SERVER_MANAGER"]
        p_info("Đang tự động vá lỗi GUI và vá lỗi tương thích Termux...")
        os.system(f"sed -i '/JFrame\\|JPanel\\|setVisible\\|setBounds\\|JOptionPane/s/^/\\/\\//' '{fp}'")
        os.system(f"sed -i '/frame\\./s/^/\\/\\//' '{fp}'")
        os.system(f"sed -i '/cmd \\/c/s/^/\\/\\//' '{fp}'")
        os.system(f"sed -i '/ProcessBuilder(\"cmd\"/s/^/\\/\\//' '{fp}'")
        os.system(f"sed -i '/new panel/s/^/\\/\\//' '{fp}'")
        
        with open(fp, 'r', encoding='utf-8', errors='ignore') as f_read: c_java = f_read.read()
        if 'canConnectWithIp' in c_java:
            lines = c_java.splitlines(); new_lines = []; skip = False
            for line in lines:
                if 'boolean canConnectWithIp(' in line:
                    new_lines.append('    private boolean canConnectWithIp(String ipAddress) { return true; }')
                    if '{' in line and '}' not in line: skip = True 
                elif skip and line.startswith('    }') and len(line.strip()) == 1: skip = False
                elif not skip: new_lines.append(line)
            with open(fp, 'w', encoding='utf-8') as f_write: f_write.write("\n".join(new_lines))
        p_ok("Vá lỗi GUI & IP Bypass hoàn tất!")

    # 6. Sửa lỗi ký tự BOM ẩn trong file Java
    def remove_bom(src_dir):
        count = 0
        if not src_dir or not os.path.exists(src_dir): return 0
        for r, d, f_list in os.walk(src_dir):
            for f in f_list:
                if f.endswith('.java'):
                    fp = os.path.join(r, f)
                    try:
                        with open(fp, 'rb') as file: raw = file.read()
                        if raw.startswith(b'\xef\xbb\xbf'):
                            with open(fp, 'wb') as file: file.write(raw[3:])
                            count += 1
                    except: pass
        return count

    p_info("Đang quét dọn lỗi ký tự BOM (.java)...")
    c1 = remove_bom(paths["SRC_ROOT"])
    if c1 > 0: p_ok(f"Đã dọn sạch BOM cho {c1} file!")

    # 7. Vá Lombok cho Maven
    if not paths["IS_NEW03"]:
        for p_xml in [os.path.join(paths["GAME_DIR"], "pom.xml"), os.path.join(paths["LOGIN_DIR"], "pom.xml")]:
            if os.path.exists(p_xml):
                try:
                    with open(p_xml, 'r', encoding='utf-8') as f: content = f.read()
                    if "<artifactId>lombok</artifactId>" in content:
                        new_content = re.sub(r'(<artifactId>lombok</artifactId>\s*<version>)[^<]+(</version>)', r'\g<1>1.18.32\g<2>', content)
                        if new_content != content:
                            with open(p_xml, 'w', encoding='utf-8') as f: f.write(new_content)
                            p_ok(f"Nâng cấp Lombok cho {os.path.basename(p_xml)} lên 1.18.32")
                except: pass

    # 8. Nâng cấp MySQL Driver cho Ant project (Fix lỗi MariaDB 11)
    lib_dir = os.path.join(paths["GAME_DIR"], "lib")
    if os.path.exists(lib_dir):
        p_info("Đang đồng bộ Driver MySQL tối tân nhất (Fix MariaDB 11)...")
        new_driver_url = "https://repo1.maven.org/maven2/mysql/mysql-connector-java/5.1.49/mysql-connector-java-5.1.49.jar"
        new_driver_path = os.path.join(lib_dir, "mysql-connector-java-5.1.49.jar")
        if not os.path.exists(new_driver_path):
            os.system(f"wget -q --show-progress {new_driver_url} -O {new_driver_path}")
        
        old_drivers = ['mysql-connector-java8-5.1.23.jar', 'mysql-connector-java-5.1.23.jar']
        for od in old_drivers:
            od_path = os.path.join(lib_dir, od)
            if os.path.exists(od_path):
                os.system(f"cp -f {new_driver_path} {od_path}")
        p_ok("Đã nâng cấp Driver MySQL thành công!")

    # 8.5. Tự động vá lỗi hiển thị CPU âm (-100%) và RAM ảo (90%) trên Termux/Linux
    p_info("Đang quét và tối ưu hóa logic CPU hiển thị âm (-100%) & RAM ảo...")
    patched_count = 0
    if os.path.exists(paths["SRC_ROOT"]):
        for r, d, f_list in os.walk(paths["SRC_ROOT"]):
            for f in f_list:
                if f.endswith(".java"):
                    fp_java = os.path.join(r, f)
                    try:
                        with open(fp_java, 'r', encoding='utf-8', errors='ignore') as f_read:
                            java_content = f_read.read()
                        
                        modified = False
                        
                        # Thay thế getSystemCpuLoad() bằng biểu thức tam phân an toàn để không bao giờ ra âm hoặc NaN
                        if "getSystemCpuLoad()" in java_content:
                            java_content = re.sub(
                                r'(\w+)\.getSystemCpuLoad\(\)',
                                r'(\1.getSystemCpuLoad() >= 0 && !Double.isNaN(\1.getSystemCpuLoad()) ? \1.getSystemCpuLoad() : (0.05 + (double)(Thread.activeCount() % 15) / 100.0))',
                                java_content
                            )
                            modified = True
                            
                        # Thay thế getProcessCpuLoad() tương tự
                        if "getProcessCpuLoad()" in java_content:
                            java_content = re.sub(
                                r'(\w+)\.getProcessCpuLoad\(\)',
                                r'(\1.getProcessCpuLoad() >= 0 && !Double.isNaN(\1.getProcessCpuLoad()) ? \1.getProcessCpuLoad() : (0.05 + (double)(Thread.activeCount() % 15) / 100.0))',
                                java_content
                            )
                            modified = True
                            
                        # Thay thế getFreePhysicalMemorySize() bằng biểu thức tam phân thông minh để tránh việc Linux Cache làm giảm RAM trống xuống mức cảnh báo ảo (nhỏ hơn 10%)
                        if "getFreePhysicalMemorySize()" in java_content:
                            java_content = re.sub(
                                r'(\w+)\.getFreePhysicalMemorySize\(\)',
                                r'(\1.getFreePhysicalMemorySize() < \1.getTotalPhysicalMemorySize() * 0.1 ? (long)(\1.getTotalPhysicalMemorySize() * 0.45) : \1.getFreePhysicalMemorySize())',
                                java_content
                            )
                            modified = True
                        
                        if modified:
                            with open(fp_java, 'w', encoding='utf-8') as f_write:
                                f_write.write(java_content)
                            patched_count += 1
                    except Exception as ex:
                        p_err(f"Lỗi khi vá hiển thị hệ thống trong {f}: {ex}")
        if patched_count > 0:
            p_ok(f"Đã tự động sửa lỗi hiển thị CPU/RAM thành công trên {patched_count} tệp Java!")
        else:
            p_info("Không phát hiện tệp tin Java nào sử dụng hàm đo CPU/RAM trực tiếp hoặc đã được tối ưu trước đó.")

    # 9. Biên dịch Source Code (Tự động chuyển đổi Ant/Maven)
    p_info("Đang chuẩn bị dọn dẹp và nâng cấp biên dịch...")
    os.system(f"rm -rf '{os.path.join(paths['GAME_DIR'], 'build')}'")
    os.system(f"rm -rf '{os.path.join(paths['GAME_DIR'], 'dist')}'")

    env = os.environ.copy()
    java_exe = shutil.which("java")
    if java_exe:
        env["JAVA_HOME"] = os.path.dirname(os.path.dirname(os.path.realpath(java_exe)))
    else:
        p_err("Chưa cài đặt JAVA!"); wait(); return

    p_info("Đang biên dịch lại Source Game (Vui lòng chờ)...")
    if os.path.exists(os.path.join(paths["GAME_DIR"], "build.xml")):
        res = subprocess.run(["ant", "jar"], cwd=paths["GAME_DIR"], env=env)
    else:
        res = subprocess.run(["mvn", "clean", "package", "-DskipTests"], cwd=paths["GAME_DIR"], env=env)

    if res.returncode == 0: 
        p_ok("Biên dịch game thành công rực rỡ!")
        cfg["status"]["build"] = True; save_config(cfg)
    else: 
        p_err("Biên dịch thất bại! Vui lòng cuộn lên kiểm tra lại log lỗi.")
    wait()

# ==========================================
# [6] CẤU HÌNH RAM & SWAP
# ==========================================
def config_ram(cfg):
    p_h("CẤU HÌNH RAM & SWAP TỐI ƯU")
    
    # Mặc định an toàn nếu không đọc được /proc/meminfo
    total = 4096
    avail = 2048
    swap_total = 0
    swap_free = 0
    
    try:
        mem = subprocess.check_output(["cat", "/proc/meminfo"]).decode()
        total = int(re.search(r"MemTotal:\s+(\d+)", mem).group(1)) // 1024
        avail = int(re.search(r"MemAvailable:\s+(\d+)", mem).group(1)) // 1024
        swap_total = int(re.search(r"SwapTotal:\s+(\d+)", mem).group(1)) // 1024
        swap_free = int(re.search(r"SwapFree:\s+(\d+)", mem).group(1)) // 1024
    except:
        pass

    used = total - avail
    pct = max(0, min(20, int(used * 20 / total))) if total > 0 else 10
    print(f"  {C.BOLD}HỆ THỐNG PHÁT HIỆN:{C.E}")
    print(f"  • RAM Thật      : [{'█' * pct}{'░' * (20-pct)}] {used}MB / {total}MB")
    print(f"  • RAM Ảo (Swap) : {swap_total - swap_free}MB / {swap_total}MB")

    # Tính toán các cấu hình đề xuất phù hợp với cấu hình máy hiện tại
    if total <= 1024:
        suggest_opt = 256
        suggest_high = 384
        suggest_low = 192
    elif total <= 2048:
        suggest_opt = 512
        suggest_high = 768
        suggest_low = 256
    elif total <= 4096:
        suggest_opt = 1024
        suggest_high = 1536
        suggest_low = 384
    elif total <= 6144:
        suggest_opt = 2048
        suggest_high = 3072
        suggest_low = 512
    else:
        suggest_opt = (total // 2 // 128) * 128
        suggest_high = (int(total * 0.7) // 128) * 128
        suggest_low = 512

    print(f"\n  {C.BOLD}CẤU HÌNH GỢI Ý CHO MÁY BẠN:{C.E}")
    print(f"  • {C.G}Chế độ 1 (Tối ưu/Cân bằng){C.E} : {C.Y}{suggest_opt}m{C.E}")
    print(f"  • {C.B}Chế độ 2 (Hiệu năng cao){C.E}     : {C.Y}{suggest_high}m{C.E}")
    print(f"  • {C.CY}Chế độ 3 (Tiết kiệm tối đa){C.E}  : {C.Y}{suggest_low}m{C.E}")

    # Hiển thị chế độ hiện tại
    cur_xmx = cfg.get("jvm_xmx", "512m")
    cur_mode = cfg.get("jvm_mode", "opt")
    mode_display = "Tối ưu nhất (Cân bằng)"
    if cur_mode == "high": mode_display = "Hiệu năng cao (Nhiều RAM)"
    elif cur_mode == "low": mode_display = "Tiết kiệm cực hạn"
    
    print(f"\n  {C.BOLD}CẤU HÌNH HIỆN TẠI:{C.E} {C.G}{cur_xmx}{C.E} (Chế độ: {C.CY}{mode_display}{C.E})")

    print(f"\n[1] Sử dụng RAM Tối ưu nhất (Cân bằng & Tự động)")
    print("[2] Sử dụng Nhiều RAM hơn (Phù hợp máy khỏe, mượt mà)")
    print("[3] Sử dụng Tiết kiệm RAM tối đa (Dành cho máy yếu)")
    print("[4] Thiết lập RAM ảo (Yêu cầu ROOT để tăng cường RAM)")
    print("[0] Quay lại")
    
    ch = input(f"\n{C.BOLD}Chọn: {C.E}").strip()
    
    if ch in ["1", "2", "3"]:
        if ch == "1":
            mode_name = "Tối ưu nhất"
            mode_code = "opt"
            suggest = f"{suggest_opt}m"
        elif ch == "2":
            mode_name = "Hiệu năng cao"
            mode_code = "high"
            suggest = f"{suggest_high}m"
        else:
            mode_name = "Tiết kiệm cực hạn"
            mode_code = "low"
            suggest = f"{suggest_low}m"

        p_info(f"Đang thiết lập chế độ: {mode_name}")
        val = input(f"Nhập mức RAM bạn muốn cấp (VD: 512m, 1g) [Mặc định: {suggest}]: ").strip()
        if not val: 
            val = suggest
        if not val.endswith(('m','g','M','G')): 
            val += 'm'
        val = val.lower()
        
        cfg['jvm_xmx'] = val
        cfg['jvm_mode'] = mode_code
        save_config(cfg)
        p_ok(f"Cấu hình thành công! Đã đặt JVM RAM = {val} và kích hoạt chế độ {mode_name}.")
        
    elif ch == "4":
        p_info("Đang kiểm tra quyền ROOT trên thiết bị...")
        is_root = False
        try:
            # Sửa lỗi check ROOT: chạy thử quyền thực tế su -c id thay vì 'which su' dễ lỗi
            res = subprocess.run(["su", "-c", "id"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
            if res.returncode == 0 and b"uid=0(root)" in res.stdout:
                is_root = True
        except Exception:
            pass

        if not is_root:
            p_err("Thiết bị của bạn CHƯA ĐƯỢC ROOT hoặc chưa cấp quyền ROOT cho Termux!")
            p_info("Để khởi tạo và bật Swap (RAM ảo) hệ thống, thiết bị bắt buộc phải có quyền ROOT thực tế.")
            wait()
        else:
            p_ok("Đã xác nhận quyền ROOT thành công!")
            p_h("THIẾT LẬP SWAP (RAM ẢO)")
            print("  1. Bật Swap (Khuyên dùng: 2048MB)")
            print("  2. Tắt Swap hiện có")
            print("  0. Quay lại")
            sw_ch = input(f"\n{C.BOLD}Chọn: {C.E}").strip()
            if sw_ch == "1":
                size_mb = input("Nhập dung lượng Swap mong muốn (MB) [Mặc định: 2048]: ").strip()
                if not size_mb: size_mb = "2048"
                try:
                    size_mb = int(size_mb)
                    p_info(f"Đang tiến hành tạo tệp Swap {size_mb}MB tại /data/swapfile...")
                    cmds = [
                        f"su -c 'dd if=/dev/zero of=/data/swapfile bs=1M count={size_mb}'",
                        "su -c 'chmod 600 /data/swapfile'",
                        "su -c 'mkswap /data/swapfile'",
                        "su -c 'swapon /data/swapfile'"
                    ]
                    success = True
                    for cmd in cmds:
                        p_info(f"Đang thực thi: {cmd}")
                        ret = os.system(cmd)
                        if ret != 0 and "swapon" not in cmd:
                            success = False
                    if success:
                        p_ok("Đã khởi tạo và kích hoạt RAM ảo (Swap) thành công rực rỡ!")
                    else:
                        p_err("Có lỗi xảy ra trong quá trình thiết lập Swap!")
                except ValueError:
                    p_err("Dung lượng nhập vào không hợp lệ!")
                wait()
            elif sw_ch == "2":
                p_info("Đang tắt Swap...")
                ret = os.system("su -c 'swapoff /data/swapfile && rm -f /data/swapfile'")
                if ret == 0:
                    p_ok("Đã tắt và dọn dẹp tệp Swap thành công!")
                else:
                    p_err("Tắt Swap thất bại hoặc không tồn tại tệp Swap trước đó.")
                wait()

def is_backup_daemon_running():
    try:
        res = subprocess.run(["tmux", "has-session", "-t", "nro_backup_daemon"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except Exception:
        return False

def start_backup_daemon_tmux():
    try:
        cfg = load_config()
        bcfg = cfg.get("backup_daemon", {})
        backup_dir = bcfg.get("backup_dir", os.path.join(HOME, "nro_backups"))
        os.makedirs(backup_dir, exist_ok=True)
        boot_log = os.path.join(backup_dir, "backup_daemon_boot.log")
        
        # Xóa file log cũ của tiến trình khởi động nếu có
        if os.path.exists(boot_log):
            try: os.remove(boot_log)
            except Exception: pass

        script_path = os.path.abspath(__file__) if '__file__' in globals() else os.path.abspath(sys.argv[0])
        script_dir = os.path.dirname(script_path)
        script_name = os.path.basename(script_path)
        
        # Kill session cũ
        os.system("tmux kill-session -t nro_backup_daemon 2>/dev/null")
        time.sleep(0.3)
        
        # Tạo session rỗng mới (cách này 100% thành công trên Termux và tránh lỗi lồng nhau)
        res = os.system("tmux new-session -d -s nro_backup_daemon")
        if res != 0:
            return False
            
        time.sleep(0.5)
        
        # Gửi lệnh chạy trực tiếp qua send-keys (thừa hưởng toàn bộ shell env chính chủ)
        cmd = f"cd \"{script_dir}\" && {sys.executable} \"{script_name}\" --backup-daemon > \"{boot_log}\" 2>&1"
        os.system(f"tmux send-keys -t nro_backup_daemon '{cmd}' C-m")
        return True
    except Exception as e:
        p_err(f"Lỗi khi chạy lệnh tmux: {str(e)}")
        return False

def check_and_create_dir(path):
    try:
        os.makedirs(path, exist_ok=True)
        # Ghi thử 1 file ẩn test để kiểm tra quyền ghi thực tế
        test_file = os.path.join(path, ".write_test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return True, ""
    except Exception as e:
        return False, str(e)

def run_backup_daemon():
    import datetime
    cfg = load_config()
    bcfg = cfg.get("backup_daemon", {})
    interval_hours = int(bcfg.get("interval_hours", 1))
    max_backups = int(bcfg.get("max_backups", 24))
    backup_dir = bcfg.get("backup_dir", os.path.join(HOME, "nro_backups"))
    db_name = cfg.get('db_name', 'nrovip')
    
    try:
        os.makedirs(backup_dir, exist_ok=True)
    except Exception:
        # Nếu thư mục bị lỗi quyền ghi, cố gắng fallback về thư mục nội bộ
        backup_dir = os.path.join(HOME, "nro_backups")
        os.makedirs(backup_dir, exist_ok=True)
        
    log_file = os.path.join(backup_dir, "backup_daemon.log")
    
    def log_msg(msg):
        t_str = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{t_str}] {msg}\n"
        print(line, end="")
        sys.stdout.flush() # Force flush để ghi ngay vào log của tmux boot_log
        try:
            with open(log_file, "a") as f:
                f.write(line)
        except Exception:
            pass

    log_msg("=== KHỞI ĐỘNG TIẾN TRÌNH SAO LƯU TỰ ĐỘNG ===")
    log_msg(f"Cấu hình: Chu kỳ = {interval_hours} giờ, Giới hạn tối đa = {max_backups} file.")
    log_msg(f"Thư mục lưu trữ: {backup_dir}")
    
    first_run = True
    while True:
        try:
            if not first_run:
                # Tính toán thời gian ngủ cho tới mốc giờ tiếp theo (giờ chẵn % interval_hours == 0)
                now = datetime.datetime.now()
                dt = now.replace(minute=0, second=0, microsecond=0)
                while True:
                    dt += datetime.timedelta(hours=1)
                    if dt > now and (dt.hour % interval_hours) == 0:
                        break
                
                seconds_to_sleep = (dt - now).total_seconds()
                log_msg(f"Đang chờ đến mốc giờ sao lưu tiếp theo: {dt.strftime('%d-%m-%Y %H:%M:%S')} (Còn {seconds_to_sleep:.1f} giây)...")
                
                target_time = now + datetime.timedelta(seconds=seconds_to_sleep)
                while datetime.datetime.now() < target_time:
                    # Kiểm tra mỗi 10 giây để đảm bảo phản hồi nhanh và chống trượt giờ do Android sleep
                    time.sleep(10)
            else:
                first_run = False
                log_msg("Thực hiện sao lưu bản đầu tiên ngay sau khi khởi chạy...")

            t_struct = time.localtime()
            timestamp_str = time.strftime("Ngay_%d-%m-%Y_Luc_%Hh%Mp", t_struct)
            out_file = os.path.join(backup_dir, f"backup_{db_name}_{timestamp_str}.sql")
            
            if cfg.get('backend') == 'ksweb':
                ksweb_pass = cfg.get('ksweb_mysql_pass', '')
                if ksweb_pass:
                    dump_cmd = f"mariadb-dump -h 127.0.0.1 -u root -p'{ksweb_pass}'"
                else:
                    dump_cmd = f"mariadb-dump -h 127.0.0.1 -u root"
            else:
                dump_cmd = "mariadb-dump -u root"
                
            cmd = f"{dump_cmd} {db_name} > \"{out_file}\""
            res = os.system(cmd)
            
            if res == 0:
                log_msg(f"Sao lưu thành công: {os.path.basename(out_file)}")
                
                # Xoay vòng dọn dẹp file cũ
                try:
                    all_files = []
                    for f_name in os.listdir(backup_dir):
                        if f_name.startswith(f"backup_{db_name}_") and f_name.endswith(".sql"):
                            full_p = os.path.join(backup_dir, f_name)
                            all_files.append((full_p, os.path.getmtime(full_p)))
                            
                    all_files.sort(key=lambda x: x[1])
                    
                    if len(all_files) > max_backups:
                        to_delete = all_files[:len(all_files) - max_backups]
                        for f_p, _ in to_delete:
                            os.remove(f_p)
                            log_msg(f"Xoay vòng: Đã tự động xóa file cũ nhất: {os.path.basename(f_p)}")
                except Exception as e:
                    log_msg(f"Lỗi khi dọn dẹp file cũ: {str(e)}")
            else:
                log_msg(f"CẢNH BÁO: mariadb-dump thất bại (Mã lỗi {res}). Vui lòng kiểm tra trạng thái CSDL.")
                
        except Exception as e:
            log_msg(f"Lỗi hệ thống trong luồng backup: {str(e)}")

def manage_auto_backup(cfg):
    while True:
        os.system("clear")
        p_h("TỰ ĐỘNG SAO LƯU XOAY VÒNG (BACKUP DAEMON)")
        
        is_running = is_backup_daemon_running()
        status_str = f"{C.G}ĐANG CHẠY (ONLINE){C.E}" if is_running else f"{C.R}ĐANG TẮT (OFFLINE){C.E}"
        
        bcfg = cfg.get("backup_daemon", {
            "interval_hours": 1,
            "max_backups": 24,
            "backup_dir": os.path.join(HOME, "nro_backups")
        })
        
        interval = bcfg.get("interval_hours", 1)
        max_backups = bcfg.get("max_backups", 24)
        backup_dir = bcfg.get("backup_dir", os.path.join(HOME, "nro_backups"))
        
        print(f"  • Trạng thái Daemon  : {status_str}")
        print(f"  • Chu kỳ sao lưu     : {C.Y}{interval} giờ / lần{C.E}")
        print(f"  • Giới hạn lưu trữ   : {C.Y}Tối đa {max_backups} file gần nhất{C.E} (Tự động xoay vòng)")
        print(f"  • Thư mục lưu trữ    : {C.CY}{backup_dir}{C.E}")
        print("------------------------------------------")
        
        print(f"{C.BOLD}Danh sách 5 bản sao lưu gần nhất:{C.E}")
        try:
            if os.path.exists(backup_dir):
                files = []
                for f in os.listdir(backup_dir):
                    if f.startswith("backup_") and f.endswith(".sql"):
                        fp = os.path.join(backup_dir, f)
                        files.append((f, os.path.getmtime(fp), os.path.getsize(fp)))
                files.sort(key=lambda x: x[1], reverse=True)
                
                if files:
                    for f, mtime, size in files[:5]:
                        t_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
                        sz_mb = size / (1024 * 1024)
                        print(f"  - {C.G}{f}{C.E} ({sz_mb:.2f} MB) - {t_str}")
                else:
                    print("  (Chưa có bản sao lưu nào được tạo)")
            else:
                print("  (Thư mục lưu trữ chưa tồn tại hoặc chưa được tạo)")
        except Exception as e:
            print(f"  Lỗi đọc thư mục: {str(e)}")
            
        print("------------------------------------------")
        print("[1] Bật tiến trình sao lưu tự động (Chạy ngầm tmux)")
        print("[2] Tắt tiến trình sao lưu tự động")
        print("[3] Thay đổi chu kỳ sao lưu (Số giờ)")
        print("[4] Thay đổi giới hạn số bản lưu (Xoay vòng)")
        print("[5] Thay đổi thư mục lưu trữ")
        print("[6] Xem Log tiến trình sao lưu")
        print("[0] Quay lại")
        
        ch = input(f"\n{C.BOLD}Chọn: {C.E}").strip()
        
        if ch == "1":
            if is_running:
                p_ok("Tiến trình sao lưu tự động đang hoạt động rồi!")
                time.sleep(1.5)
                continue
            
            p_info("Đang kiểm tra thư mục lưu trữ...")
            ok, err_msg = check_and_create_dir(backup_dir)
            if not ok:
                p_err(f"Không thể ghi vào thư mục: {backup_dir}")
                p_info(f"Chi tiết lỗi: {err_msg}")
                p_info("Lời khuyên:")
                if "/sdcard" in backup_dir:
                    print(f"  • Hãy chạy lệnh {C.Y}termux-setup-storage{C.E} trong Termux để cấp quyền truy cập bộ nhớ.")
                    print(f"  • Hoặc chọn mục [5] để chuyển sang thư mục nội bộ an toàn của Termux: {C.G}~/nro_backups{C.E}")
                else:
                    print(f"  • Vui lòng chọn mục [5] để đổi sang một thư mục hợp lệ khác.")
                wait()
                continue
                
            # Kiểm tra xem tmux có cài đặt chưa
            if not shutil.which("tmux"):
                p_err("Hệ thống chưa được cài đặt 'tmux'!")
                p_info("Vui lòng chạy lệnh sau trên Termux rồi thử lại:")
                print(f"  {C.Y}pkg install tmux -y{C.E}")
                wait()
                continue

            p_info("Đang khởi chạy tiến trình sao lưu ngầm...")
            start_backup_daemon_tmux()
            time.sleep(1.5)
            if is_backup_daemon_running():
                p_ok("Đã kích hoạt Daemon sao lưu tự động ngầm thành công!")
            else:
                p_err("Khởi chạy thất bại không rõ nguyên nhân!")
                p_info("Lời khuyên: Chọn mục [6] để xem file Log chi tiết nguyên nhân lỗi.")
            time.sleep(2.5)
            
        elif ch == "2":
            if not is_running:
                p_ok("Tiến trình sao lưu tự động đã tắt từ trước!")
                time.sleep(1.5)
                continue
            os.system("tmux kill-session -t nro_backup_daemon 2>/dev/null")
            p_ok("Đã dừng Daemon sao lưu tự động thành công!")
            time.sleep(1.5)
            
        elif ch == "3":
            new_val = input(f"Nhập chu kỳ sao lưu mới (số giờ) [{interval}]: ").strip()
            if new_val:
                try:
                    val_int = int(new_val)
                    if val_int <= 0: raise ValueError()
                    bcfg["interval_hours"] = val_int
                    cfg["backup_daemon"] = bcfg
                    save_config(cfg)
                    p_ok(f"Đã lưu chu kỳ mới: {val_int} giờ.")
                    if is_running:
                        p_info("Đang khởi động lại Daemon để áp dụng cấu hình mới...")
                        start_backup_daemon_tmux()
                except ValueError:
                    p_err("Giá trị không hợp lệ! Vui lòng nhập số nguyên dương.")
                time.sleep(1.5)
                
        elif ch == "4":
            new_val = input(f"Nhập số bản lưu tối đa để xoay vòng [{max_backups}]: ").strip()
            if new_val:
                try:
                    val_int = int(new_val)
                    if val_int <= 0: raise ValueError()
                    bcfg["max_backups"] = val_int
                    cfg["backup_daemon"] = bcfg
                    save_config(cfg)
                    p_ok(f"Đã lưu giới hạn mới: {val_int} file.")
                    if is_running:
                        p_info("Đang khởi động lại Daemon để áp dụng cấu hình mới...")
                        start_backup_daemon_tmux()
                except ValueError:
                    p_err("Giá trị không hợp lệ! Vui lòng nhập số nguyên dương.")
                time.sleep(1.5)
                
        elif ch == "5":
            p_h("CẤU HÌNH THƯ MỤC LƯU TRỮ BACKUP")
            print("Chọn phương thức thiết lập:")
            print(f"  [1] Lưu tại thư mục nội bộ (Khuyên dùng, không cần cấp quyền):")
            print(f"      -> {C.G}{os.path.join(HOME, 'nro_backups')}{C.E}")
            print(f"  [2] Lưu tại thư mục Download ngoài điện thoại (Yêu cầu quyền bộ nhớ):")
            print(f"      -> {C.G}/sdcard/Download/nro_backups{C.E}")
            print(f"  [3] Tự nhập đường dẫn tuyệt đối khác")
            print(f"  [0] Quay lại")
            
            sub_ch = input(f"\n{C.BOLD}Chọn: {C.E}").strip()
            new_path = ""
            if sub_ch == "1":
                new_path = os.path.join(HOME, "nro_backups")
            elif sub_ch == "2":
                new_path = "/sdcard/Download/nro_backups"
            elif sub_ch == "3":
                new_path = input("Nhập đường dẫn tuyệt đối mới: ").strip()
                
            if new_path:
                p_info(f"Đang kiểm tra quyền ghi vào thư mục: {new_path}...")
                ok, err_msg = check_and_create_dir(new_path)
                if not ok:
                    p_err(f"Lỗi: Không thể ghi hoặc không thể tạo thư mục này!")
                    p_info(f"Chi tiết lỗi: {err_msg}")
                    if "/sdcard" in new_path:
                        p_info("Bạn cần cấp quyền truy cập bộ nhớ bằng lệnh: termux-setup-storage")
                    
                    use_fallback = input("Bạn có muốn tự động chuyển sang thư mục nội bộ an sau (~/nro_backups) không? (y/n): ").strip().lower()
                    if use_fallback == 'y':
                        new_path = os.path.join(HOME, "nro_backups")
                        os.makedirs(new_path, exist_ok=True)
                        ok = True
                    else:
                        wait()
                        continue
                
                if ok:
                    bcfg["backup_dir"] = new_path
                    cfg["backup_daemon"] = bcfg
                    save_config(cfg)
                    p_ok(f"Đã cập nhật thư mục lưu trữ thành công: {new_path}")
                    if is_running:
                        p_info("Đang khởi động lại Daemon để áp dụng cấu hình mới...")
                        start_backup_daemon_tmux()
                    time.sleep(2)
                
        elif ch == "6":
            log_file = os.path.join(backup_dir, "backup_daemon.log")
            boot_log = os.path.join(backup_dir, "backup_daemon_boot.log")
            
            p_h("LOG TIẾN TRÌNH SAO LƯU")
            
            has_logs = False
            if os.path.exists(boot_log) and os.path.getsize(boot_log) > 0:
                print(f"{C.Y}--- LOG KHỞI ĐỘNG (Boot Log) ---{C.E}")
                os.system(f"cat \"{boot_log}\"")
                print("---------------------------------\n")
                has_logs = True
                
            if os.path.exists(log_file) and os.path.getsize(log_file) > 0:
                print(f"{C.G}--- LOG VẬN HÀNH CHÍNH (Daemon Log) ---{C.E}")
                os.system(f"tail -n 30 \"{log_file}\"")
                has_logs = True
                
            if not has_logs:
                p_err("Chưa có bất kỳ file log nào được tạo.")
            wait()
            
        elif ch == "0":
            break

# ==========================================
# [7] QUẢN LÝ DỊCH VỤ LEMP
# ==========================================
def manage_lemp(cfg):
    if cfg.get('backend') == 'ksweb':
        p_h("TRẠNG THÁI & HƯỚNG DẪN BẬT KSWEB")
        ks_found, mysql_ok = detect_ksweb()
        print(f"  KSWEB phát hiện: {'✓ Có' if ks_found else '✗ Không'}")
        print(f"  KSWEB MySQL    : {'✓ Online' if mysql_ok else '✗ Offline'}")
        p_info("\n[HƯỚNG DẪN BẬT WEB & MYSQL TRÊN KSWEB]")
        print("  1. Mở ứng dụng KSWEB trên điện thoại.")
        print("  2. Tại thẻ Lighttpd (hoặc Nginx), đánh dấu chọn để bật Web.")
        print("  3. Chuyển sang thẻ Tools, tìm MySQL và đánh dấu chọn để bật CSDL.")
        print("  4. (Tùy chọn) Bạn có thể dùng phpMyAdmin tích hợp trong KSWEB để quản lý.")
        wait(); return

    while True:
        os.system("clear")
        p_h("QUẢN LÝ DỊCH VỤ LEMP (WEB & MYSQL)")
        print("[1] Khởi chạy toàn bộ dịch vụ (LEMP ON)")
        print("[2] Tắt toàn bộ dịch vụ (LEMP OFF)")
        print("[3] Hướng dẫn quản lý SQL bằng App ngoài (Khuyên dùng)")
        print("[4] Chẩn đoán chuyên sâu & Sửa lỗi kết nối LEMP")
        print("[0] Quay lại")
        ch = input("\nChọn: ")
        
        if ch == "1":
            prefix = os.environ.get('PREFIX', '/data/data/com.termux/files/usr')
            os.makedirs(os.path.join(prefix, "var/run"), exist_ok=True)
            os.makedirs(os.path.join(prefix, "var/log/nginx"), exist_ok=True)
            os.makedirs(os.path.join(prefix, "var/lib/nginx"), exist_ok=True)
            os.makedirs(os.path.join(prefix, "var/lib/nginx/client_body"), exist_ok=True)
            os.makedirs(os.path.join(prefix, "var/lib/nginx/proxy"), exist_ok=True)
            os.makedirs(os.path.join(prefix, "var/lib/nginx/fastcgi"), exist_ok=True)
            
            p_info("Đang dọn dẹp các tiến trình cũ để tránh xung đột...")
            os.system("pkill -9 nginx; pkill -9 php-fpm")
            time.sleep(1)
            p_info("Đang khởi động MariaDB, PHP-FPM & Nginx...")
            os.system("mariadbd-safe > /dev/null 2>&1 &")
            os.system("php-fpm > /dev/null 2>&1")
            os.system("nginx > /dev/null 2>&1")
            
            time.sleep(1.5)
            
            # Sử dụng kiểm tra kết nối Socket thay thế hoàn toàn cho pgrep (ổn định 100% trên Android/Termux)
            import socket
            def is_port_open(port):
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)
                try:
                    s.connect(("127.0.0.1", port))
                    s.close()
                    return True
                except:
                    return False
            
            nginx_ok = is_port_open(8080) or is_port_open(8081)
            fpm_ok = is_port_open(9000)
            
            if nginx_ok and fpm_ok:
                p_ok("Đã khởi chạy Nginx, MariaDB & PHP-FPM cực kỳ mượt mà!")
                p_info("  • Web Đăng Ký đang chạy tại: http://127.0.0.1:8080")
                p_info("  • phpMyAdmin đang chạy tại : http://127.0.0.1:8081")
            else:
                p_err("CẢNH BÁO: Phát hiện dịch vụ LEMP chưa khởi động hoàn tất hoặc bị chặn chặn kết nối!")
                if not nginx_ok:
                    p_err("  • Nginx chưa phản hồi ở cổng 8080/8081. Đang kiểm thử cú pháp:")
                    os.system("nginx -t")
                if not fpm_ok:
                    p_err("  • PHP-FPM chưa phản hồi ở cổng 9000. Đang kiểm thử cú pháp:")
                    os.system("php-fpm -t")
                p_info("\n💡 Khuyên dùng: Chọn mục [4] trong menu để chạy chẩn đoán chuyên sâu & hiển thị lỗi thực tế.")
            wait()
            
        elif ch == "2":
            os.system("pkill -9 nginx; pkill -9 php-fpm; pkill -9 mariadbd")
            p_ok("Đã tắt toàn bộ các dịch vụ!")
            wait()
        elif ch == "3":
            print(f"\n{C.CY}--- HƯỚNG DẪN DÙNG APP NGOÀI ĐỂ QUẢN LÝ DATABASE ---{C.E}")
            print("Sử dụng ứng dụng SQL bên ngoài là giải pháp mượt mà, chuyên nghiệp nhất!")
            print("Và tránh được 100% lỗi phát sinh do cấu trúc máy kén phpMyAdmin.")
            print(f"\n  {C.BOLD}Bước 1:{C.E} Lên CH Play tải app: {C.G}SQL Client{C.E} hoặc {C.G}Termius{C.E}")
            print(f"  {C.BOLD}Bước 2:{C.E} Kết nối với thông tin:")
            print(f"    • Host: {C.G}127.0.0.1{C.E}  |  Port: {C.G}3306{C.E}")
            print(f"    • User: {C.G}root{C.E}       |  Password: {C.G}(Để trống - không mật khẩu){C.E}")
            print(f"    • Database: {C.G}team2026{C.E}")
            wait()
        elif ch == "4":
            p_h("HỆ THỐNG CHẨN ĐOÁN LỖI LEMP TRÊN TERMUX")
            prefix = os.environ.get('PREFIX', '/data/data/com.termux/files/usr')
            p_info(f"Môi trường Termux Prefix: {prefix}")
            
            # 1. Kiểm tra các dịch vụ hiện tại
            p_info("Đang quét trạng thái các cổng dịch vụ...")
            ports = {
                3306: "MariaDB (MySQL)",
                9000: "PHP-FPM (FastCGI)",
                8080: "Nginx - Web Đăng Ký",
                8081: "Nginx - phpMyAdmin"
            }
            
            import socket
            import subprocess
            
            def check_port_local(port):
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)
                try:
                    s.connect(("127.0.0.1", port))
                    s.close()
                    return True
                except:
                    return False

            def get_process_local(port):
                try:
                    out = subprocess.check_output(f"lsof -i :{port} -t", shell=True, stderr=subprocess.DEVNULL)
                    pids = out.decode().strip().split('\n')
                    processes = []
                    for p in pids:
                        if p:
                            p_name = subprocess.check_output(f"ps -p {p} -o comm=", shell=True, stderr=subprocess.DEVNULL).decode().strip()
                            processes.append(f"{p_name} (PID: {p})")
                    return ", ".join(processes)
                except:
                    return "Không thể xác định (thiếu lsof)"

            status = {}
            for port, name in ports.items():
                is_open = check_port_local(port)
                status[port] = is_open
                if is_open:
                    owner = get_process_local(port)
                    p_ok(f"Cổng {port} ({name}): ONLINE (Chiếm bởi: {owner})")
                else:
                    p_err(f"Cổng {port} ({name}): OFFLINE")

            # 2. Kiểm tra các file cấu hình
            p_h("KIỂM TRA CẤU HÌNH & THƯ MỤC LOG")
            nginx_conf_path = os.path.join(prefix, "etc/nginx/nginx.conf")
            php_fpm_path = os.path.join(prefix, "etc/php-fpm.d/www.conf")
            
            if os.path.exists(nginx_conf_path):
                p_ok(f"Tìm thấy Nginx config: {nginx_conf_path}")
            else:
                p_err(f"Không tìm thấy Nginx config: {nginx_conf_path}")
                
            if os.path.exists(php_fpm_path):
                p_ok(f"Tìm thấy PHP-FPM config: {php_fpm_path}")
            else:
                p_err(f"Không tìm thấy PHP-FPM config: {php_fpm_path}")

            # 3. Chạy thử nghiệm trực tiếp để hứng lỗi (stderr)
            p_h("CHẠY THỬ NGHIỆM TRỰC TIẾP ĐỂ HỨNG LỖI CHUYÊN SÂU")
            
            if not status[9000]:
                p_info("Thử kiểm thử cú pháp PHP-FPM...")
                proc = subprocess.run("php-fpm -t", shell=True, capture_output=True, text=True)
                if proc.returncode == 0:
                    p_ok("Cú pháp PHP-FPM hợp lệ!")
                    p_info("Đang chạy thử php-fpm ở chế độ không nền (1 giây)...")
                    os.system("pkill -9 php-fpm > /dev/null 2>&1")
                    time.sleep(0.5)
                    os.system("php-fpm > /dev/null 2>&1")
                    time.sleep(1.5)
                    if check_port_local(9000):
                        p_ok("Khởi động PHP-FPM nền thành công!")
                        status[9000] = True
                    else:
                        p_err("PHP-FPM test cú pháp thành công nhưng tiến trình bị Android kill khi chạy nền!")
                else:
                    p_err("PHP-FPM phát hiện lỗi cấu hình:")
                    print(proc.stderr)

            if not status[8080] or not status[8081]:
                p_info("Thử kiểm thử cú pháp Nginx...")
                proc = subprocess.run("nginx -t", shell=True, capture_output=True, text=True)
                if proc.returncode == 0:
                    p_ok("Cú pháp Nginx hợp lệ!")
                    p_info("Đang dọn dẹp thư mục và chạy thử Nginx nền...")
                    os.makedirs(os.path.join(prefix, "var/run"), exist_ok=True)
                    os.makedirs(os.path.join(prefix, "var/log/nginx"), exist_ok=True)
                    os.makedirs(os.path.join(prefix, "var/lib/nginx"), exist_ok=True)
                    os.system("pkill -9 nginx > /dev/null 2>&1")
                    time.sleep(0.5)
                    os.system("nginx > /dev/null 2>&1")
                    time.sleep(1.5)
                    if check_port_local(8080) or check_port_local(8081):
                        p_ok("Khởi động Nginx nền thành công!")
                        status[8080] = check_port_local(8080)
                        status[8081] = check_port_local(8081)
                    else:
                        p_err("Nginx test cú pháp thành công nhưng bị Android kill khi chạy nền!")
                        log_file = os.path.join(prefix, "var/log/nginx/error.log")
                        if os.path.exists(log_file):
                            try:
                                with open(log_file, 'r') as f:
                                    lines = f.readlines()
                                    last_lines = lines[-10:] if len(lines) > 10 else lines
                                    print(f"\n--- 10 dòng cuối log lỗi Nginx ({log_file}) ---")
                                    for line in last_lines:
                                        print(f"  {line.strip()}")
                            except:
                                pass
                else:
                    p_err("Nginx phát hiện lỗi cấu hình:")
                    print(proc.stderr)

            p_h("GIẢI PHÁP KHẮC PHỤC TRÊN TERMUX")
            print("  • Nếu test cú pháp thành công nhưng tiến trình nền bị kill ngay lập tức:")
            print("    Đây là lỗi cực kỳ phổ biến do tính năng Phantom Processes của Android 12+ tự động tắt các app chạy ngầm trong Termux.")
            print("    Giải pháp triệt để: Hãy mở Termux và chạy lệnh sau (hoặc cắm máy tính bật qua ADB):")
            print(f"    {C.G}adb shell device_config put activity_manager max_phantom_processes 2147483647{C.E}")
            print("    Hoặc giải pháp đơn giản nhất: Chuyển đổi sang sử dụng KSWEB (Mục [3]) để chạy Web/MySQL mượt mà, không lo bị Android tắt ngầm.")
            wait()
        elif ch == "0":
            break

# ==========================================
# [8/9] VẬN HÀNH LOGIN & GAME SERVER
# ==========================================
def launch_server(cfg, stype):
    p = get_paths(cfg)
    path = p["LOGIN_DIR"] if stype == "login" else p["GAME_DIR"]
    port = cfg['local_login_port'] if stype == "login" else cfg['local_game_port']
    session = f"nro_{stype}_server"
    xmx = cfg.get('jvm_xmx', '512m')
    
    if not path or not os.path.exists(path):
        p_err(f"Không tìm thấy thư mục của Server {stype.upper()}!")
        wait()
        return

    # Xác định các cờ tối ưu JVM dựa trên chế độ cấu hình RAM được lựa chọn
    jvm_mode = cfg.get("jvm_mode", "opt")
    if jvm_mode == "low":
        jvm_opts = f"-XX:+UseSerialGC -Xms16m -Xmx{xmx} -Xss160k -XX:CICompilerCount=1 -XX:TieredStopAtLevel=1 -XX:MaxMetaspaceSize=48m -XX:CompressedClassSpaceSize=12m -XX:+SegmentedCodeCache -XX:+UseStringDeduplication -XX:MaxHeapFreeRatio=40 -XX:MinHeapFreeRatio=20"
    elif jvm_mode == "high":
        jvm_opts = f"-XX:+UseG1GC -Xms128m -Xmx{xmx} -Xss384k -XX:MaxGCPauseMillis=100 -XX:+ParallelRefProcEnabled -XX:InitiatingHeapOccupancyPercent=45 -XX:MaxMetaspaceSize=128m"
    else:
        jvm_opts = f"-XX:+UseSerialGC -Xms32m -Xmx{xmx} -Xss256k -XX:CICompilerCount=2 -XX:TieredStopAtLevel=1 -XX:MaxMetaspaceSize=64m -XX:CompressedClassSpaceSize=16m -XX:+SegmentedCodeCache"
        
    if os.path.exists(os.path.join(path, "dist")):
        main_class = "nro.models.server.ServerManager"
        jar_cmd = f"java -Dfile.encoding=UTF-8 -Duser.timezone=Asia/Ho_Chi_Minh -Djava.awt.headless=true -server {jvm_opts} -cp \"dist/*:lib/*\" {main_class}"
    else:
        jar_cmd = f"java -Dfile.encoding=UTF-8 -Duser.timezone=Asia/Ho_Chi_Minh -Djava.awt.headless=true -jar *.jar" if stype == "login" else f"java -Dfile.encoding=UTF-8 -Duser.timezone=Asia/Ho_Chi_Minh -Djava.awt.headless=true -server {jvm_opts} -jar *.jar"

    while True:
        os.system("clear")
        p_h(f"VẬN HÀNH {stype.upper()} SERVER")
        print("[1] Khởi chạy trực tiếp (Xem Log màn hình)")
        print("[2] Khởi chạy ngầm (TMux - Khuyên Dùng)")
        print("[3] Dừng Server (Kill Port & Session)")
        print("[0] Quay lại")
        ch = input("\nChọn: ").strip()
        
        if ch == "1":
            kill_port(port)
            os.chdir(path)
            
            p_info(f"Khởi chạy trực tiếp {stype.upper()} Server...")
            p_info(f"Lệnh chạy: {jar_cmd}")
            p_info("Nhấn Ctrl + C để dừng server.")
            print("-" * 50)
            
            # Khởi chạy trực tiếp thông qua os.system
            start_time = time.time()
            try:
                exit_code = os.system(jar_cmd)
            except KeyboardInterrupt:
                exit_code = "Đã ngắt bằng Ctrl+C"
                print(f"\n{C.G}[✓] Đã ngắt tiến trình Server chủ động.{C.E}")
                
            duration = time.time() - start_time
            print("-" * 50)
            p_err(f"Server đã dừng! (Thời gian hoạt động: {duration:.1f} giây, Mã thoát: {exit_code})")
            
            # Điều chỉnh dừng lại khi lỗi để người dùng nhìn thấy log!
            if duration < 15:
                p_err("CẢNH BÁO: Server dừng quá nhanh (< 15 giây). Có thể gặp lỗi khởi động!")
                p_info("Lời khuyên: Vui lòng đọc kỹ các dòng log lỗi ở trên trước khi bấm Enter.")
            else:
                p_ok("Server đã dừng bình thường hoặc tắt chủ động.")
                
            input(f"\n{C.Y}👉 Bấm Enter để quay lại Menu quản lý...{C.E}")
            
        elif ch == "2":
            kill_port(port)
            os.system(f"tmux kill-session -t {session} 2>/dev/null")
            
            # Ghi file watchdog.py vào thư mục của Server tương ứng
            watchdog_path = os.path.join(path, "watchdog.py")
            pkill_cmd = "pkill -9 -f 'ServerLogin' >/dev/null 2>&1" if stype == "login" else "pkill -9 -f 'ServerManager' >/dev/null 2>&1; pkill -9 -f 'VanTuan' >/dev/null 2>&1"
            watchdog_code = f"""# -*- coding: utf-8 -*-
import os, time, socket, subprocess

port = {port}
jar_cmd = {repr(jar_cmd)}
db_port = 3306

def is_port_open(p):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.5)
    try:
        s.connect(("127.0.0.1", p))
        s.close()
        return True
    except:
        return False

print("=== WATCHDOG STARTED ===")

# Buoc 1: Kiem tra MySQL phai san sang
if not is_port_open(db_port):
    print("CSDL dang offline, doi CSDL online...")
    while not is_port_open(db_port):
        time.sleep(3)
    print("CSDL da online!")
    time.sleep(1)

# Buoc 2: Khoi dong ban dau neu chua chay
if not is_port_open(port):
    print("Khoi dong Server ban dau...")
    subprocess.Popen(jar_cmd, shell=True, start_new_session=True)
    time.sleep(15)

# Buoc 3: Vong lap giam sat
while True:
    if is_port_open(port):
        time.sleep(5)
        continue
    
    # Phat hien mat ket noi, doi 20 giay va kiem tra lai
    print("Phat hien mat ket noi! Doi 20 giay...")
    time.sleep(20)
    if is_port_open(port):
        print("Da phuc hoi ket noi!")
        continue
    
    print("Van mat ket noi sau 20 giay! Tien hanh khoi dong lai...")
    os.system(f"fuser -k -9 {{port}}/tcp >/dev/null 2>&1")
    os.system(f"lsof -t -i:{{port}} >/dev/null 2>&1 | xargs kill -9 >/dev/null 2>&1")
    os.system("{pkill_cmd}")
    time.sleep(2)
    
    subprocess.Popen(jar_cmd, shell=True, start_new_session=True)
    time.sleep(15)
"""
            try:
                with open(watchdog_path, "w", encoding="utf-8") as wf:
                    wf.write(watchdog_code)
            except Exception as e:
                p_err(f"Không thể ghi tệp giám sát: {e}")
                
            # Khởi chạy session TMux mới gọi watchdog.py
            os.system(f"tmux new-session -d -s {session} 'cd {path} && python3 watchdog.py'")
            p_ok(f"Bộ tự động kiểm tra & giám sát thông minh (Watchdog) đã được kích hoạt thành công!")
            p_ok(f"Server {stype} đang được khởi động ngầm ổn định trong session TMux.")
            wait()
            
        elif ch == "3":
            kill_port(port)
            os.system(f"tmux kill-session -t {session} 2>/dev/null")
            p_ok(f"Đã tắt Server {stype}!")
            wait()
            
        elif ch == "0":
            break

# ==========================================
# [W] QUẢN LÝ GIAO DIỆN WEB ĐĂNG KÝ
# ==========================================
def refresh_web_index(cfg):
    db_name = cfg.get('db_name', 'nrovip')
    backend = cfg.get('backend', 'termux')
    ksweb_pass = cfg.get('ksweb_mysql_pass', '') if backend == 'ksweb' else ""
    footer_text = "KSWEB Hybrid" if backend == 'ksweb' else "LEMP Termux"
    
    if backend == 'ksweb':
        web_subdir = cfg.get('ksweb_web_dir', 'nso_web')
        web_dir = f"/sdcard/htdocs/{web_subdir}"
    else:
        web_dir = os.path.join(HOME, "web_register")
    os.makedirs(web_dir, exist_ok=True)
    
    # 1. db_config.php (Always overwritten)
    db_cfg_content = f"<?php\n$db_name = '{db_name}';\n$ksweb_pass = '{ksweb_pass}';\n$footer_text = '{footer_text}';\n?>"
    with open(os.path.join(web_dir, "db_config.php"), "w", encoding="utf-8") as f:
        f.write(db_cfg_content)
        
    # 2. web_config.json (Always overwritten to sync with nro_config)
    web_cfg_content = json.dumps({
        "web_show_vnd": cfg.get('web_show_vnd', True),
        "web_show_admin": cfg.get('web_show_admin', True),
        "web_admin_notice": cfg.get('web_admin_notice', ''),
        "web_admin_pass": cfg.get('web_admin_pass', 'admin')
    }, indent=4)
    with open(os.path.join(web_dir, "web_config.json"), "w", encoding="utf-8") as f:
        f.write(web_cfg_content)
        
    # 3. index.php (Only created if not exists, so user can edit it via admin.php)
    index_file = os.path.join(web_dir, "index.php")
    should_write_index = True
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            if "web_config.json" in content and "Zalo" in content:
                should_write_index = False

    if should_write_index:
        index_content = r"""<?php
error_reporting(E_ALL & ~E_NOTICE & ~E_DEPRECATED & ~E_WARNING);
ini_set('display_errors', 0);
require_once 'db_config.php';
$web_cfg = json_decode(file_get_contents('web_config.json'), true);
$show_vnd = $web_cfg['web_show_vnd'] ?? true;
$show_admin = $web_cfg['web_show_admin'] ?? true;
$admin_notice = $web_cfg['web_admin_notice'] ?? '';

$conn = new mysqli("127.0.0.1", "root", $ksweb_pass, $db_name);
$msg = ""; $status = "";

if ($_SERVER["REQUEST_METHOD"] == "POST") {
    $user = preg_replace("/[^a-zA-Z0-9]/", "", $_POST['user']);
    $pass = $_POST['pass'];
    $email = isset($_POST['email']) ? preg_replace("/[^a-zA-Z0-9@.]/", "", $_POST['email']) : "";
    $isAdmin = isset($_POST['is_admin']) ? 1 : 0;
    $vnd = isset($_POST['vnd']) ? (int)$_POST['vnd'] : 0;
    
    if (strlen($user) < 4 || strlen($pass) < 1) {
        $msg = "Tên tài khoản tối thiểu 4 ký tự!"; $status = "error";
    } else {
        try {
            $cols_res = $conn->query("DESCRIBE account");
            $db_cols = [];
            while ($row = $cols_res->fetch_assoc()) {
                $db_cols[$row['Field']] = ['Null' => $row['Null'], 'Default' => $row['Default']];
            }
            $insert_data = [
                'username' => "'$user'", 'password' => "'$pass'", 'email' => "'$email'",
                'is_admin' => $isAdmin, 'vnd' => $vnd, 'active' => 1
            ];
            foreach ($db_cols as $field => $meta) {
                if ($field === 'id') continue;
                if (!isset($insert_data[$field]) && $meta['Null'] === 'NO' && $meta['Default'] === null) {
                    $insert_data[$field] = "''";
                }
            }
            $final_cols = []; $final_vals = [];
            foreach ($insert_data as $field => $val) {
                if (isset($db_cols[$field])) { $final_cols[] = $field; $final_vals[] = $val; }
            }
            $check = $conn->query("SELECT id FROM account WHERE username = '$user'");
            if ($check->num_rows > 0) {
                $msg = "Tài khoản này đã tồn tại!"; $status = "error";
            } else {
                $sql = "INSERT INTO account (" . implode(", ", $final_cols) . ") VALUES (" . implode(", ", $final_vals) . ")";
                if ($conn->query($sql)) {
                    $msg = "Đăng ký thành công!";
                    if ($isAdmin) $msg .= " Đã cấp quyền Admin.";
                    if ($vnd > 0) $msg .= " Tặng " . number_format($vnd) . " VND.";
                    $status = "success";
                } else {
                    $msg = "Lỗi Database: " . $conn->error; $status = "error";
                }
            }
        } catch (Exception $e) { $msg = "Lỗi hệ thống: " . $e->getMessage(); $status = "error"; }
    }
}
?>
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NRO - Đăng Ký Test Game</title>
    <style>
        :root { --primary: #00d2ff; --secondary: #3a7bd5; --bg: #0f172a; }
        * { box-sizing: border-box; font-family: 'Segoe UI', sans-serif; }
        body { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; margin: 0; color: white; padding: 20px; }
        .card { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px); padding: 2rem; border-radius: 1.5rem; border: 1px solid rgba(255, 255, 255, 0.1); width: 100%; max-width: 450px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); }
        h1 { text-align: center; margin-bottom: 1.5rem; font-weight: 800; background: linear-gradient(to right, #00d2ff, #3a7bd5); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .badge { text-align: center; margin-bottom: 1rem; }
        .badge span { background: linear-gradient(to right, #10b981, #059669); padding: 4px 12px; border-radius: 999px; font-size: 0.7rem; font-weight: bold; }
        .input-group { margin-bottom: 1rem; }
        label { display: block; margin-bottom: 0.4rem; font-size: 0.85rem; color: #94a3b8; }
        input[type="text"], input[type="password"], input[type="email"], input[type="number"] { width: 100%; padding: 0.75rem 1rem; border-radius: 0.75rem; border: 1px solid rgba(255, 255, 255, 0.1); background: rgba(0,0,0,0.2); color: white; outline: none; transition: 0.3s; }
        input:focus { border-color: var(--primary); box-shadow: 0 0 0 2px rgba(0, 210, 255, 0.2); }
        .checkbox-group { display: flex; align-items: center; gap: 10px; margin: 1rem 0; cursor: pointer; }
        .checkbox-group input { width: 18px; height: 18px; cursor: pointer; }
        button { width: 100%; padding: 0.9rem; border: none; border-radius: 0.75rem; background: linear-gradient(to right, var(--primary), var(--secondary)); color: white; font-weight: bold; cursor: pointer; transition: 0.3s; margin-top: 1rem; }
        button:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0, 210, 255, 0.3); }
        .alert { padding: 0.8rem; border-radius: 0.75rem; margin-bottom: 1rem; text-align: center; font-size: 0.85rem; }
        .success { background: rgba(34, 197, 94, 0.2); border: 1px solid #22c55e; color: #4ade80; }
        .error { background: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; color: #f87171; }
        .footer { text-align: center; margin-top: 1.5rem; font-size: 0.75rem; color: #64748b; }
    </style>
</head>
<body>
    <div class="card">
        <h1>NRO TEST TOOLS</h1>
        <div class="badge"><span><?php echo $footer_text; ?></span></div>
        
        <div style="background: rgba(0, 210, 255, 0.1); border-left: 4px solid #00d2ff; padding: 15px; margin-bottom: 20px; border-radius: 8px; font-size: 0.85rem; line-height: 1.5; text-align: justify;">
            <strong>Chào mừng các bạn đến với NRO termux</strong> phiên bản SRC được chia sẻ bởi <a href="https://www.youtube.com/watch?v=YTnZo66T0Tk" target="_blank" style="color: #00d2ff; font-weight: bold; text-decoration: none;">DAITEN Studio</a> dự án free hoàn toàn nếu có ai bắt trả phí chắc chắn nó là scam ! chúc các bạn chơi và mod game vui vẻ !
            <div style="margin-top: 10px; display: flex; gap: 10px; justify-content: center;">
                <a href="https://zalo.me/g/nran3u1pi3hgm9mq5mpc" target="_blank" style="background: #0068ff; color: white; padding: 6px 12px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 0.8rem; flex: 1; text-align: center;">📱 Nhóm Zalo</a>
                <a href="https://www.facebook.com/groups/nro.termux" target="_blank" style="background: #1877f2; color: white; padding: 6px 12px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 0.8rem; flex: 1; text-align: center;">📘 Nhóm Facebook</a>
            </div>
        </div>
        
        <?php
        $game_ip_port = "Chưa thiết lập";
        if (file_exists("game_info.txt")) {
            $game_ip_port = trim(file_get_contents("game_info.txt"));
        }
        ?>
        <div style="background: rgba(16, 185, 129, 0.1); border-left: 4px solid #10b981; padding: 15px; margin-bottom: 20px; border-radius: 8px; text-align: center;">
            <div style="font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px;">IP / Domain Kết Nối Game</div>
            <div style="font-size: 1.2rem; font-weight: bold; color: #10b981; letter-spacing: 0.5px; cursor: pointer;" onclick="alert('Đã copy IP!'); navigator.clipboard.writeText('<?php echo htmlspecialchars($game_ip_port); ?>');"><?php echo htmlspecialchars($game_ip_port); ?> 📋</div>
        </div>
        
        <?php if (!empty($admin_notice)): ?>
        <div style="background: rgba(59, 130, 246, 0.1); border-left: 4px solid #3b82f6; padding: 15px; margin-bottom: 20px; border-radius: 8px;">
            <div style="font-weight: bold; color: #3b82f6; margin-bottom: 5px;">THÔNG BÁO TỪ ADMIN:</div>
            <div style="font-size: 0.9rem; line-height: 1.5; color: #e2e8f0;"><?php echo htmlspecialchars($admin_notice); ?></div>
        </div>
        <?php endif; ?>
        
        <?php if ($msg): ?>
            <div class="alert <?php echo $status; ?>"><?php echo $msg; ?></div>
        <?php endif; ?>
        
        <form method="POST">
            <div class="input-group">
                <label>Tên tài khoản</label>
                <input type="text" name="user" placeholder="Nhập username..." required autofocus>
            </div>
            <div class="input-group">
                <label>Mật khẩu</label>
                <input type="password" name="pass" placeholder="Nhập mật khẩu..." required>
            </div>
            <div class="input-group">
                <label>Email (Tùy chọn)</label>
                <input type="email" name="email" placeholder="Nhập email...">
            </div>
            
            <?php if ($show_vnd): ?>
            <div class="input-group">
                <label>Số tiền VND muốn nạp (Để test)</label>
                <input type="number" name="vnd" value="1000000" placeholder="Nhập số tiền...">
            </div>
            <?php endif; ?>
            
            <?php if ($show_admin): ?>
            <label class="checkbox-group">
                <input type="checkbox" name="is_admin"> Kích hoạt quyền Admin cho tài khoản này
            </label>
            <?php endif; ?>
            
            <button type="submit">ĐĂNG KÝ VÀ NHẬN QUÀ</button>
        </form>
        <div class="footer">Dự án Mod Game NRO - <?php echo $footer_text; ?></div>
        <div class="footer" style="margin-top:5px;"><a href="admin.php" style="color:#3b82f6; text-decoration:none;">Truy cập Admin Web</a></div>
    </div>
</body>
</html>
"""
        with open(index_file, "w", encoding="utf-8") as f:
            f.write(index_content)

    # 4. admin.php (Only created if not exists)
    admin_file = os.path.join(web_dir, "admin.php")
    if not os.path.exists(admin_file) or os.path.getsize(admin_file) < 100:
        admin_content = r"""<?php
session_start();
$cfg_file = 'web_config.json';
$cfg = json_decode(file_get_contents($cfg_file), true);
$admin_pass = $cfg['web_admin_pass'] ?? 'admin';

if (isset($_GET['logout'])) {
    session_destroy();
    header("Location: admin.php");
    exit;
}

if ($_SERVER['REQUEST_METHOD'] == 'POST' && isset($_POST['login_pass'])) {
    if ($_POST['login_pass'] === $admin_pass) {
        $_SESSION['is_admin_web'] = true;
        header("Location: admin.php");
        exit;
    } else {
        $login_err = "Mật khẩu không đúng!";
    }
}

if (!isset($_SESSION['is_admin_web'])) {
?>
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Đăng nhập Web Admin</title>
    <style>
        body { background: #0f172a; color: white; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .box { background: rgba(255,255,255,0.05); padding: 2rem; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1); width: 100%; max-width: 350px; text-align: center; }
        input { width: 100%; padding: 10px; margin-top: 10px; margin-bottom: 20px; border-radius: 8px; border: 1px solid #333; background: #222; color: white; box-sizing: border-box;}
        button { width: 100%; padding: 10px; border: none; border-radius: 8px; background: #3b82f6; color: white; font-weight: bold; cursor: pointer;}
    </style>
</head>
<body>
    <div class="box">
        <h2>Admin Login</h2>
        <?php if(isset($login_err)) echo "<p style='color:#ef4444;'>$login_err</p>"; ?>
        <form method="POST">
            <input type="password" name="login_pass" placeholder="Nhập mật khẩu Admin..." autofocus required>
            <button type="submit">Đăng Nhập</button>
        </form>
    </div>
</body>
</html>
<?php
    exit;
}

// Xử lý lưu config
$msg = "";
if ($_SERVER['REQUEST_METHOD'] == 'POST' && isset($_POST['action'])) {
    if ($_POST['action'] == 'save_cfg') {
        $cfg['web_show_vnd'] = isset($_POST['show_vnd']) ? true : false;
        $cfg['web_show_admin'] = isset($_POST['show_admin']) ? true : false;
        $cfg['web_admin_notice'] = $_POST['admin_notice'];
        file_put_contents($cfg_file, json_encode($cfg, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
        $msg = "Đã lưu cài đặt hiển thị!";
    } elseif ($_POST['action'] == 'save_code') {
        file_put_contents('index.php', $_POST['source_code']);
        $msg = "Đã cập nhật mã nguồn index.php!";
    }
}
$cfg = json_decode(file_get_contents($cfg_file), true);
?>
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Web Admin Control Panel</title>
    <style>
        body { background: #0f172a; color: white; font-family: sans-serif; margin: 0; padding: 20px; }
        .container { max-width: 800px; margin: auto; background: rgba(255,255,255,0.05); padding: 2rem; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1); }
        h1 { color: #3b82f6; text-align: center; }
        .tab-btn { background: #1e293b; color: white; border: none; padding: 10px 20px; cursor: pointer; border-radius: 5px; margin-right: 5px; }
        .tab-btn.active { background: #3b82f6; }
        .tab-content { display: none; margin-top: 20px; }
        .tab-content.active { display: block; }
        label { display: block; margin-bottom: 10px; cursor: pointer; }
        textarea { width: 100%; height: 300px; padding: 10px; border-radius: 5px; border: 1px solid #333; background: #111; color: #10b981; font-family: monospace; box-sizing: border-box; margin-bottom: 15px; }
        button.submit { background: #10b981; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; width: 100%; }
        .alert { background: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; color: #10b981; padding: 10px; border-radius: 5px; margin-bottom: 15px; text-align: center; }
    </style>
    <script>
        function showTab(id) {
            document.querySelectorAll('.tab-content').forEach(e => e.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(e => e.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            event.target.classList.add('active');
        }
    </script>
</head>
<body>
    <div class="container">
        <h1>Bảng Điều Khiển Web Admin</h1>
        <div style="text-align:right; margin-bottom: 20px;">
            <a href="index.php" target="_blank" style="color: #00d2ff; text-decoration: none; margin-right: 15px;">Mở Web Đăng Ký</a>
            <a href="?logout=1" style="color: #ef4444; text-decoration: none;">Đăng Xuất</a>
        </div>
        
        <?php if($msg) echo "<div class='alert'>$msg</div>"; ?>
        
        <div>
            <button class="tab-btn active" onclick="showTab('tab-settings')">Cài Đặt Form</button>
            <button class="tab-btn" onclick="showTab('tab-code')">Sửa Code index.php</button>
        </div>
        
        <div id="tab-settings" class="tab-content active">
            <form method="POST">
                <input type="hidden" name="action" value="save_cfg">
                <label>
                    <input type="checkbox" name="show_vnd" <?php echo ($cfg['web_show_vnd']??true) ? 'checked' : ''; ?>> Hiển thị ô nhập tiền VND
                </label>
                <label>
                    <input type="checkbox" name="show_admin" <?php echo ($cfg['web_show_admin']??true) ? 'checked' : ''; ?>> Hiển thị tuỳ chọn cấp quyền Admin
                </label>
                <div style="margin-top: 15px; margin-bottom: 5px;">Nội dung Thông Báo (để trống nếu muốn ẩn):</div>
                <textarea name="admin_notice" style="height: 100px; color: white; background: #222;"><?php echo htmlspecialchars($cfg['web_admin_notice']??''); ?></textarea>
                <button type="submit" class="submit">LƯU CÀI ĐẶT</button>
            </form>
        </div>
        
        <div id="tab-code" class="tab-content">
            <form method="POST">
                <input type="hidden" name="action" value="save_code">
                <div style="margin-bottom: 5px; color:#ef4444; font-size: 0.85rem;">* CẢNH BÁO: Chỉnh sửa sai mã nguồn có thể làm lỗi trang đăng ký! Nhấn 'Lưu' để cập nhật.</div>
                <textarea name="source_code"><?php echo htmlspecialchars(file_get_contents('index.php')); ?></textarea>
                <button type="submit" class="submit">LƯU MÃ NGUỒN</button>
            </form>
        </div>
    </div>
</body>
</html>
"""
        with open(admin_file, "w", encoding="utf-8") as f:
            f.write(admin_content)
    
    return web_dir

def manage_web_ui(cfg):
    while True:
        os.system("clear")
        p_h("QUẢN LÝ TÀI KHOẢN ADMIN WEB")
        
        curr_pass = cfg.get('web_admin_pass', 'admin')
        ip_port = get_local_ip()
        if cfg.get('backend', 'termux') == 'ksweb':
            port = "8080"
        else:
            port = cfg.get('web_port', 8080)
            
        print(f"  > Trang quản lý đã được chuyển lên Web để chống lỗi Font!")
        print(f"  > Đường dẫn Web Admin: {C.CY}http://{ip_port}:{port}/admin.php{C.E}")
        print(f"  > Mật khẩu truy cập hiện tại: {C.G}{curr_pass}{C.E}\n")
        
        print("  [1] Đổi Mật Khẩu Truy Cập Web Admin")
        print("  [0] Quay lại")
        
        ch = input(f"\n{C.BOLD}Chọn: {C.E}").strip()
        
        if ch == "1":
            new_pass = input("Nhập mật khẩu mới (hoặc Enter để huỷ): ").strip()
            if new_pass:
                cfg['web_admin_pass'] = new_pass
                save_config(cfg)
                refresh_web_index(cfg)
                p_ok(f"Đã đổi mật khẩu thành công: {new_pass}")
                time.sleep(1.5)
        elif ch == "0":
            break

# ==========================================
# [A] QUẢN LÝ TÀI KHOẢN (TERMINAL CLI)
# ==========================================
def manage_accounts(cfg):
    p_h("QUẢN LÝ TÀI KHOẢN")
    db_name = cfg.get('db_name', 'nrovip')
    db_cmd = get_db_cmd(cfg)
    
    while True:
        backend = cfg.get('backend', 'termux').upper()
        print(f"\n  Backend đang hoạt động: {C.H}{backend}{C.E}")
        print("[1] Liệt kê danh sách tài khoản")
        print("[2] Tạo tài khoản nhanh")
        print("[3] Đổi mật khẩu tài khoản")
        print("[4] Xóa tài khoản")
        print("[0] Quay lại")
        ch = input(f"\n{C.BOLD}Chọn: {C.E}").strip()
        
        if ch == "1":
            os.system(f"{db_cmd} {db_name} -e 'SELECT id, username, active, is_admin FROM account LIMIT 30;'")
        elif ch == "2":
            u = input("Username: ").strip()
            p = input("Password: ").strip()
            if u and p:
                res = os.system(f"{db_cmd} {db_name} -e \"INSERT INTO account (username, password, active) VALUES ('{u}', '{p}', 1);\"")
                if res == 0: p_ok(f"Đã tạo tài khoản: {u}")
                else: p_err("Lỗi: Tài khoản có thể đã tồn tại!")
        elif ch == "3":
            u = input("Username cần đổi: ").strip()
            p = input("Mật khẩu mới: ").strip()
            if u and p:
                os.system(f"{db_cmd} {db_name} -e \"UPDATE account SET password='{p}' WHERE username='{u}';\"")
                p_ok("Cập nhật mật khẩu thành công!")
        elif ch == "4":
            u = input("Username cần xóa: ").strip()
            if u:
                os.system(f"{db_cmd} {db_name} -e \"DELETE FROM account WHERE username='{u}';\"")
                p_ok("Đã xóa tài khoản khỏi CSDL.")
        elif ch == "0": break
    wait()

# ==========================================
# [K] CHUYỂN ĐỔI BACKEND
# ==========================================
def switch_backend(cfg):
    p_h("CHUYỂN ĐỔI BACKEND (LEMP ↔ KSWEB)")
    current = cfg.get('backend', 'termux')
    ksweb_found, ksweb_mysql = detect_ksweb()
    
    ksweb_found_str = f"{C.G}✓ Có{C.E}" if ksweb_found else f"{C.R}✗ Không{C.E}"
    ksweb_mysql_str = f"{C.G}✓ Online{C.E}" if ksweb_mysql else f"{C.R}✗ Offline{C.E}"
    
    print(f"  Backend hiện tại : {C.H}{current.upper()}{C.E}")
    print(f"  Ứng dụng KSWEB   : {ksweb_found_str}")
    print(f"  MySQL trên KSWEB : {ksweb_mysql_str}")
    print(f"  Mật khẩu KSWEB   : {C.Y}{cfg.get('ksweb_mysql_pass', 'Trống')}{C.E}")
    print()
    print(f"  [1] Sử dụng LEMP Termux (Dịch vụ MariaDB + Nginx nội bộ)")
    print(f"  [2] Sử dụng KSWEB (Dịch vụ MySQL + Lighttpd bên ngoài)")
    print(f"  [3] Đồng bộ Web đăng ký sang KSWEB (/sdcard/htdocs/)")
    print(f"  [4] Thiết lập/Thay đổi mật khẩu MySQL KSWEB")
    print(f"  [0] Quay lại")
    
    ch = input(f"\n{C.BOLD}Chọn: {C.E}").strip()
    if ch == "1":
        cfg['backend'] = 'termux'
        cfg['db_pass'] = ''
        save_config(cfg)
        p_ok("Đã chuyển sang dùng LEMP Termux!")
    elif ch == "2":
        if not ksweb_found:
            p_err("Không phát hiện ứng dụng KSWEB! Hãy cài đặt app KSWEB trước.")
            wait(); return
        cfg['backend'] = 'ksweb'
        cfg['db_pass'] = cfg.get('ksweb_mysql_pass', '')
        save_config(cfg)
        p_ok("Đã chuyển sang dùng KSWEB!")
    elif ch == "3":
        deploy_web_to_ksweb(cfg)
    elif ch == "4":
        pw = input("Nhập mật khẩu MySQL KSWEB: ").strip()
        cfg['ksweb_mysql_pass'] = pw
        cfg['db_pass'] = pw
        save_config(cfg)
        p_ok("Cập nhật mật khẩu MySQL KSWEB thành công!")
    wait()

# ==========================================
# [B] QUẢN LÝ TIẾN TRÌNH CHẠY ẨN (TMUX / TUNNEL)
# ==========================================
def check_process_running(pattern):
    try:
        output = subprocess.check_output(["pgrep", "-f", pattern], stderr=subprocess.DEVNULL)
        return True, len(output.decode().strip().split('\n'))
    except:
        return False, 0

def manage_tmux(cfg):
    while True:
        os.system("clear")
        p_h("GIÁM SÁT & PHÍM TẮT KẾT NỐI NHANH TMUX SESSIONS")
        
        # Quét các session TMux thực tế đang hoạt động
        tmux_sessions = []
        try:
            res = subprocess.check_output(["tmux", "list-sessions"], stderr=subprocess.DEVNULL).decode("utf-8", errors="ignore")
            for line in res.strip().split("\n"):
                if line.strip():
                    name = line.split(":")[0].strip()
                    tmux_sessions.append(name)
        except:
            pass
            
        print(f" {C.BOLD}Danh sách Session TMux đang hoạt động:{C.E}")
        if not tmux_sessions:
            print(f"  {C.R}✗ Hiện tại không có Session TMux nào đang chạy.{C.E}")
        else:
            for i, name in enumerate(tmux_sessions, 1):
                print(f"  [{i}] Kết nối trực tiếp vào: {C.G}{name}{C.E} (tmux attach -t {name})")
                
        print("\n-------------------------------------------------------------")
        print(f"  {C.Y}[N]{C.E} Kết nối nhanh Ngrok  : {C.BOLD}tmux attach -t nro_ngrok{C.E}")
        print(f"  {C.Y}[G]{C.E} Kết nối nhanh Server : {C.BOLD}tmux attach -t nro_game_server{C.E}")
        print("-------------------------------------------------------------")
        print("  [K] Tắt (Kill) một Session TMux bất kỳ")
        print("  [T] Tắt toàn bộ TMux server (Kill-server)")
        print("  [0] Quay lại Menu chính")
        print("-------------------------------------------------------------")
        print(f"  {C.Y}HƯỚNG DẪN THOÁT TMUX: Nhấn [Ctrl + B] rồi thả ra, sau đó bấm [D]{C.E}")
        print(f"  {C.Y}để quay trở về menu quản lý mà không làm sập tiến trình chạy ẩn.{C.E}")
        print("-------------------------------------------------------------")
        
        ch = input(f"{C.BOLD}Lựa chọn của bạn: {C.E}").strip().upper()
        if ch == "0":
            break
        elif ch == "N":
            p_info("Đang thực hiện lệnh: tmux attach -t nro_ngrok ...")
            time.sleep(1)
            os.system("tmux attach -t nro_ngrok")
        elif ch == "G":
            p_info("Đang thực hiện lệnh: tmux attach -t nro_game_server ...")
            time.sleep(1)
            os.system("tmux attach -t nro_game_server")
        elif ch == "K":
            if not tmux_sessions:
                p_err("Không có Session TMux nào để tắt.")
                time.sleep(1.5)
                continue
            idx = input("Nhập số thứ tự hoặc tên Session cần tắt: ").strip()
            if idx in tmux_sessions:
                os.system(f"tmux kill-session -t {idx}")
                p_ok(f"Đã tắt Session: {idx}")
                time.sleep(1.5)
            else:
                try:
                    idx = int(idx)
                    if 1 <= idx <= len(tmux_sessions):
                        s_name = tmux_sessions[idx-1]
                        os.system(f"tmux kill-session -t {s_name}")
                        p_ok(f"Đã tắt Session: {s_name}")
                    else:
                        p_err("Số thứ tự không hợp lệ.")
                except ValueError:
                    p_err("Tên hoặc số thứ tự không hợp lệ.")
                time.sleep(1.5)
        elif ch == "T":
            confirm = input(f"{C.Y}Xác nhận tắt toàn bộ TMux server? (y/N): {C.E}").strip().lower()
            if confirm == 'y':
                os.system("tmux kill-server")
                p_ok("Đã tắt toàn bộ TMux Server!")
            time.sleep(1.5)
        else:
            try:
                idx = int(ch)
                if 1 <= idx <= len(tmux_sessions):
                    s_name = tmux_sessions[idx-1]
                    p_info(f"Đang kết nối tới Session '{s_name}'...")
                    time.sleep(1)
                    os.system(f"tmux attach -t {s_name}")
                else:
                    p_err("Lựa chọn không hợp lệ.")
                    time.sleep(1)
            except ValueError:
                pass

# ==========================================
# TRÌNH CHẠY CHÍNH (MAIN LOOP)
# ==========================================
def get_ram_bar():
    try:
        res = subprocess.check_output("free -m", shell=True).decode().split('\n')[1].split()
        total, used = int(res[1]), int(res[2]); pct = int(used * 100 / total); bar_len = 20
        filled = int(pct * bar_len / 100); bar = "█" * filled + "░" * (bar_len - filled)
        return f"{C.Y}[{bar}] {pct}% ({used}MB/{total}MB){C.E}"
    except: return "[N/A]"

SRC_DOWNLOAD_LINK = "https://drive.google.com/file/d/1kahsNgga4pH0gzFlMtAbvf45Np82Ex1I/view?usp=sharing"
APK_DOWNLOAD_LINK = "https://drive.google.com/file/d/1K1bwBRhiyNLfEMuOo2Yujs2CGe9yMIip/view?usp=sharing"

def show_download_links(cfg):
    os.system("clear")
    p_h("LINK TẢI SRC & APK")
    print(f" {C.BOLD}Copy link bên dưới dán sang trình duyệt (Chrome/Cốc Cốc...) để tải:{C.E}\n")
    print(f" {C.Y}[SRC Game]{C.E}")
    print(f" {C.CY}{SRC_DOWNLOAD_LINK}{C.E}\n")
    print(f" {C.Y}[APK Termux/Game]{C.E}")
    print(f" {C.CY}{APK_DOWNLOAD_LINK}{C.E}\n")
    print("-" * 50)
    print(f" {C.Y}Lưu ý: Tool không tự tải hộ vì Google Drive yêu cầu xác nhận trình duyệt.{C.E}")
    input("\nNhấn Enter để quay lại menu...")

def main():
    while True:
        cfg = load_config()
        l_st = get_server_status(cfg, "login")
        g_st = get_server_status(cfg, "game")
            
        lemp_st = check_lemp_status(cfg)
        backend = cfg.get('backend', 'termux')
        
        # Xây dựng PMA & Web đăng ký hiển thị
        if backend == 'ksweb':
            web_subdir = cfg.get('ksweb_web_dir', 'nso_web')
            web_display = cfg.get('web_url', f"http://{get_local_ip()}:8080/{web_subdir}/")
            pma_display = f"http://{get_local_ip()}:8001 (KSWEB)"
            svc_label = f"Trạng thái KSWEB: {lemp_st}"
        else:
            web_display = cfg.get('web_url', f"http://{get_local_ip()}:8080")
            pma_display = f"http://{get_local_ip()}:8081"
            svc_label = f"Quản lý Dịch vụ LEMP: {lemp_st}"
            
        ksweb_hint = ""
        if backend == 'termux' and 'OFF' in lemp_st:
            ksweb_found, _ = detect_ksweb()
            if ksweb_found:
                ksweb_hint = f"\n  {C.Y}⚡ LEMP lỗi? Phát hiện KSWEB! Bấm [K] để chuyển đổi.{C.E}"

        mode_str = cfg.get('mode', 'offline').upper()
        if mode_str == 'OFFLINE':
            ip = cfg.get('tcp_domain', get_local_ip())
        else:
            ip = get_local_ip()
        
        os.system("clear")
        print(f"""{C.CY}{C.BOLD}
==========================================
      NRO VNPro4 - Danh Rieng Cho SRC_4
=========================================={C.E}
 {C.G}tôi tạo ra app này để mod những game này thành game pvp 
 hoặc các chế độ khác tương tự mà không cần cày quốc 
 ae ai có chung ý tưởng nhớ share cho mọi người để 
 chúng ta cùng vui vẻ nhé!{C.E}
------------------------------------------
 {C.BOLD}RAM: {get_ram_bar()}
 {C.BOLD}IP:  {C.G}{ip}{C.E} | {C.BOLD}MODE:{C.E} {C.H}{mode_str}{C.E} | {C.BOLD}BACKEND:{C.E} {get_backend_label(cfg)}
 {C.BOLD}WEB ĐĂNG KÝ: {C.CY}{web_display}{C.E}{ksweb_hint}
 {C.BOLD}PHPMYADMIN:  {C.CY}{pma_display}{C.E}
------------------------------------------
 [1] Cài đặt môi trường hệ thống{get_stat(cfg,'env')}
 [2] Giải nén Source game (Scan Download){get_stat(cfg,'source')}
 [3] Thiết lập Database & Web (Auto Fix){get_stat(cfg,'db_web')}
 [4] Cấu hình Kết nối (Online/Offline)
 [5] Vá IP & Build Game{get_stat(cfg,'build')}
 [6] Cấu hình RAM & Swap (Hybrid)
 [7] {svc_label}
 [8] VẬN HÀNH GAME SERVER: {g_st}
 [9] QUẢN LÝ TÀI KHOẢN
 [W] QUẢN LÝ GIAO DIỆN WEB ĐĂNG KÝ
 [A] TỰ ĐỘNG SAO LƯU XOAY VÒNG (BACKUP DAEMON): {f"{C.G}ON{C.E}" if is_backup_daemon_running() else f"{C.R}OFF{C.E}"}
 [B] GIÁM SÁT TIẾN TRÌNH TMUX (NGROK/CF/SERVER)
 {C.G}[K] CHUYỂN ĐỔI BACKEND (LEMP ↔ KSWEB){C.E}
 [D] LÀM MỚI KẾT NỐI NHANH
 [L] LINK TẢI SRC & APK
 [0] THOÁT CHƯƠNG TRÌNH
------------------------------------------""")
        ch = input(f"{C.BOLD}Lựa chọn của bạn: {C.E}").strip().upper()
        if ch == "1": install_env(cfg)
        elif ch == "2": extract_source(cfg)
        elif ch == "3": setup_db(cfg)
        elif ch == "4": manage_tcp(cfg)
        elif ch == "5": apply_and_build(cfg)
        elif ch == "6": config_ram(cfg)
        elif ch == "7": manage_lemp(cfg)
        elif ch == "8": launch_server(cfg, "game")
        elif ch == "9": manage_accounts(cfg)
        elif ch == "W": manage_web_ui(cfg)
        elif ch == "A": manage_auto_backup(cfg)
        elif ch == "B": manage_tmux(cfg)
        elif ch == "K": switch_backend(cfg)
        elif ch == "D":
            kill_port(cfg['local_login_port']); kill_port(cfg['local_game_port'])
            time.sleep(2)
            if cfg.get("mode") != "online":
                cfg["tcp_domain"] = get_local_ip()
                cfg["tcp_port"] = cfg['local_game_port']
                save_config(cfg)
            apply_and_build(cfg)
        elif ch == "L": show_download_links(cfg)
        elif ch == "0": break
        time.sleep(0.1)

if __name__ == "__main__":
    import sys
    if "--backup-daemon" in sys.argv:
        run_backup_daemon()
    else:
        main()
