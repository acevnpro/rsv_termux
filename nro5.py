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
CONFIG_FILE = os.path.join(HOME, "nro_config_5.json")

def load_config():
    defaults = {
        "base_dir": os.path.join(HOME, "SRC_5"),
        "db_user": "root", "db_pass": "", "db_name": "src_5",
        "tcp_domain": get_local_ip(), "tcp_port": 14445,
        "local_game_port": 14445,
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
        "status": {"env": False, "source": False, "db_web": False, "build": False}
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
    b = cfg.get("base_dir", os.path.join(HOME, "SRC_5"))
    
    # Tìm thư mục chứa file build.xml của project Ant
    g_dir = os.path.join(b, "SRC")
    if not os.path.exists(os.path.join(g_dir, "build.xml")):
        found = False
        try:
            for root, dirs, files in os.walk(b):
                if "build.xml" in files:
                    if "/build" in root or "/dist" in root or "temp_" in root:
                        continue
                    g_dir = root
                    found = True
                    break
        except: pass
        if not found:
            g_dir = b

    src_root = os.path.join(g_dir, "src")
    
    g_props = os.path.join(g_dir, "Config.properties")
    db_service = os.path.join(g_dir, "src/nro/models/data/LocalManager.java")
    data_game = os.path.join(g_dir, "src/nro/models/data/DataGame.java")
    sm_path = os.path.join(g_dir, "src/nro/models/server/ServerManager.java")

    try:
        for r, d, f_l in os.walk(g_dir):
            if "nbproject" in r or "/build" in r or "/dist" in r: continue
            for f in f_l:
                if f.endswith(".properties"):
                    try:
                        with open(os.path.join(r, f), 'r', errors='ignore') as p_file:
                            if "database.host" in p_file.read(): g_props = os.path.join(r, f)
                    except: pass
                elif f in ["LocalManager.java", "AlyraManager.java"]: db_service = os.path.join(r, f)
                elif f == "DataGame.java": data_game = os.path.join(r, f)
                elif f == "ServerManager.java": sm_path = os.path.join(r, f)
    except: pass

    # Tìm file database SQL
    sql_file = os.path.join(b, "database.sql")
    if os.path.exists(b):
        try:
            for r, d_list, f_list in os.walk(b):
                for f in f_list:
                    if f.endswith(".sql") and "build" not in r and "dist" not in r:
                        sql_file = os.path.join(r, f)
                        break
                if sql_file and os.path.exists(sql_file): break
        except: pass

    return {
        "BASE": b, 
        "GAME_DIR": g_dir, 
        "GAME_PROPS": g_props, 
        "DB_SERVICE": db_service, 
        "DATA_GAME": data_game,
        "SERVER_MANAGER": sm_path, 
        "SRC_ROOT": src_root,
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
            res = subprocess.check_output("ip -4 addr | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1'", shell=True).decode().strip()
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
    os.system("pkill -9 -f 'ServerManager' 2>/dev/null")

def get_st(pattern):
    try:
        subprocess.check_output(["pgrep", "-f", pattern], stderr=subprocess.DEVNULL)
        return f"{C.G}ON{C.E}"
    except: return f"{C.R}OFF{C.E}"

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
        pkgs = ["openjdk-17", "ant", "wget", "unzip", "unrar", "tar", "git", "tmux", "psmisc", "lsof"]
    else:
        cfg['backend'] = 'termux'
        cfg['db_pass'] = ''
        save_config(cfg)
        p_ok("Đã chọn chế độ LEMP Termux!")
        pkgs = ["openjdk-17", "mariadb", "nginx", "php", "php-fpm", "ant",
                "wget", "unzip", "unrar", "tar", "git", "tmux", "psmisc", "lsof", "cloudflared"]
    
    p_info("Đang cập nhật hệ thống (Tự động 100%)...")
    os.system('pkg update -y')
    os.system('apt upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"')
    
    for pkg in pkgs:
        p_info(f"Đang cài {pkg}...")
        os.system(f"pkg install {pkg} -y")
    
    if cfg['backend'] == 'termux':
        nginx_conf = os.path.join(os.environ.get('PREFIX', '/data/data/com.termux/files/usr'), "etc/nginx/nginx.conf")
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
        location ~ \.php$ {{
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
        location ~ \.php$ {{
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
    p_h("GIẢI NÉN SOURCE GAME (SRC_5)")
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
    
    # Setup thư mục SRC_5 cố định cho script này
    target = os.path.join(HOME, "SRC_5")
    
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

    p_info("Đang định hình cấu trúc thư mục game (Ant Project)...")
    found_game = False
    
    # Quét tìm thư mục chứa build.xml để định nghĩa làm Game Server
    game_src_temp = ""
    try:
        for root, dirs, files in os.walk(temp_extract):
            if "build.xml" in files:
                if "/build" in root or "/dist" in root:
                    continue
                game_src_temp = root
                break
    except: pass

    if game_src_temp:
        os.system(f"mkdir -p '{target}/SRC'")
        os.system(f"mv '{game_src_temp}'/* '{target}/SRC/' 2>/dev/null")
        os.system(f"mv '{game_src_temp}'/.* '{target}/SRC/' 2>/dev/null")
        # Quét tìm sql gom ra ngoài
        try:
            for root, dirs, files in os.walk(temp_extract):
                for f in files:
                    if f.endswith(".sql"):
                        os.system(f"mv '{os.path.join(root, f)}' '{target}/' 2>/dev/null")
        except: pass
        found_game = True

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
    
    db_name = cfg.get('db_name', 'src_5')
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
            <strong>Chào mừng các bạn đến với NRO SRC_5</strong>
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
    with open(os.path.join(ksweb_web, "index.php"), "w", encoding="utf-8") as f:
        f.write(php_content)
    p_ok(f"Web đăng ký đã được tạo thành công tại: {ksweb_web}")

def setup_db_ksweb(cfg):
    p_h("THIẾT LẬP DATABASE (KSWEB MODE)")
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
    db_name = cfg.get('db_name', 'src_5')
    db_cmd = get_db_cmd(cfg)
    
    p_info(f"Đang tiến hành import vào CSDL {db_name}...")
    res = os.system(f"{db_cmd} -f {db_name} < \"{full_path}\"")
    if res == 0:
        p_ok("Nạp dữ liệu SQL thành công!")
    else:
        p_err("Có lỗi trong quá trình import.")
    wait()

def export_sql_custom(cfg):
    p_h("XUẤT (BACKUP) FILE SQL")
    db_name = cfg.get('db_name', 'src_5')
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
        c = input("Bạn có chắc chắn muốn tiếp tục cài LEMP? (y/N): ").strip().upper()
        if c != 'Y': return

    p_info("Đang thiết lập dịch vụ LEMP nội bộ...")
    if not os.path.exists(os.path.join(os.environ.get('PREFIX', '/data/data/com.termux/files/usr'), "var/lib/mysql")):
        os.system("mysql_install_db")
        
    os.system("mariadbd-safe > /dev/null 2>&1 &")
    p_info("Đang khởi động MariaDB (vui lòng chờ 8 giây)...")
    time.sleep(8)
    
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
            
    p_ok("Cấu hình tài khoản MariaDB root thành công.")
    
    db_name = cfg['db_name']
    os.system(f"mariadb -u root -e 'CREATE DATABASE IF NOT EXISTS {db_name};'")
    
    paths = get_paths(cfg)
    sql_file = paths['SQL_FILE']
    if os.path.exists(sql_file):
        p_info(f"Đang nạp file SQL: {os.path.basename(sql_file)}...")
        os.system(f"mariadb -u root -f {db_name} < \"{sql_file}\"")
        p_ok(f"Nạp dữ liệu vào CSDL '{db_name}' thành công!")
    else:
        p_err("Không tìm thấy file CSDL .sql trong dự án!")
        
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
            $cols_res = $conn->query("DESCRIBE account");
            $db_cols = [];
            while ($row = $cols_res->fetch_assoc()) {{
                $db_cols[$row['Field']] = ['Null' => $row['Null'], 'Default' => $row['Default']];
            }}
            $insert_data = [
                'username' => "'$user'", 'password' => "'$pass'", 'email' => "'$email'",
                'is_admin' => $isAdmin, 'vnd' => $vnd, 'active' => 1
            ];
            foreach ($db_cols as $field => $meta) {{
                if ($field === 'id') continue;
                if (!isset($insert_data[$field]) && $meta['Null'] === 'NO' && $meta['Default'] === null) {{
                    $insert_data[$field] = "''";
                }}
            }}
            $final_cols = []; $final_vals = [];
            foreach ($insert_data as $field => $val) {{
                if (isset($db_cols[$field])) {{
                    $final_cols[] = $field; $final_vals[] = $val;
                }}
            }}
            $check = $conn->query("SELECT id FROM account WHERE username = '$user'");
            if ($check->num_rows > 0) {{
                $msg = "Tài khoản này đã tồn tại!"; $status = "error";
            }} else {{
                $sql = "INSERT INTO account (" . implode(", ", $final_cols) . ") VALUES (" . implode(", ", $final_vals) . ")";
                if ($conn->query($sql)) {{
                    $msg = "Đăng ký thành công!"; $status = "success";
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
    <title>NRO - Đăng Ký (LEMP)</title>
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
            <strong>Chào mừng các bạn đến với SRC_5</strong>
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
    with open(os.path.join(reg_dir, "index.php"), "w", encoding="utf-8") as f:
        f.write(php_content)
        
    p_info("Đang cấu hình php-fpm...")
    prefix = os.environ.get('PREFIX', '/data/data/com.termux/files/usr')
    
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
        p_info("Đang tải phpMyAdmin...")
        pma_url = "https://www.phpmyadmin.net/downloads/phpMyAdmin-latest-all-languages.tar.gz"
        pma_tar = os.path.join(HOME, "pma.tar.gz")
        os.system(f"wget {pma_url} -O {pma_tar}")
        os.system(f"tar -xf {pma_tar} -C {HOME}")
        extracted = [d for d in os.listdir(HOME) if d.startswith("phpMyAdmin-") and os.path.isdir(os.path.join(HOME, d))]
        if extracted:
            os.system(f"rm -rf {pma_root}")
            os.system(f"mv {os.path.join(HOME, extracted[0])} {pma_root}")
        os.system(f"rm -f {pma_tar}")
        
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
        p_ok("Đã cấu hình phpMyAdmin")

    pma_idx = os.path.join(pma_root, "index.php")
    if os.path.exists(pma_idx):
        with open(pma_idx, 'r') as f: lines = f.readlines()
        has_declare = any("declare(strict_types=1)" in l for l in lines)
        new_lines = []
        inserted = False
        fix_code = "error_reporting(0); ini_set('display_errors', 0); // Fix PHP 8.4\n"
        for line in lines:
            if "Fix PHP 8.4" in line: continue
            new_lines.append(line)
            if not inserted:
                if has_declare and "declare(strict_types=1)" in line:
                    new_lines.append(fix_code); inserted = True
                elif not has_declare and "<?php" in line:
                    new_lines.append(fix_code); inserted = True
        with open(pma_idx, 'w') as f: f.writelines(new_lines)
        
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
        location ~ \.php$ {{
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
        location ~ \.php$ {{
            fastcgi_pass   127.0.0.1:9000;
            fastcgi_param  SCRIPT_FILENAME  $document_root$fastcgi_script_name;
            include        fastcgi_params;
        }}
    }}
}}
"""
    with open(nginx_conf, 'w') as f: f.write(conf_content)
        
    p_info("Đang khởi động lại dịch vụ PHP-FPM & Nginx...")
    os.system("pkill -9 nginx; pkill -9 php-fpm")
    time.sleep(1)
    os.system("php-fpm > /dev/null 2>&1")
    os.system("nginx > /dev/null 2>&1")
    
    time.sleep(1.5)
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
            subprocess.run(["termux-chroot", "ngrok", "tcp", str(cfg['local_game_port'])])
        elif sc == "2":
            subprocess.run(["pkill", "-9", "ngrok"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            subprocess.run(["tmux", "kill-session", "-t", "nro_ngrok"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            subprocess.run(["tmux", "new-session", "-d", "-s", "nro_ngrok", f"termux-chroot ngrok tcp {cfg['local_game_port']}"])
            p_ok("Ngrok đang khởi chạy ngầm!")
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
        p_info("Đang thiết lập cổng kết nối Cloudflare..."); time.sleep(8)
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
    wait()

# ==========================================
# [5] VÁ IP & BIÊN DỊCH GAME
# ==========================================
def apply_and_build(cfg):
    os.system("clear"); p_h("VÁ SOURCE & BIÊN DỊCH (BUILD)"); paths = get_paths(cfg)
    
    if not os.path.exists(paths["GAME_DIR"]):
        p_err(f"Không tìm thấy thư mục Game Server (có build.xml): {paths['GAME_DIR']}"); wait(); return

    ip = cfg['tcp_domain']; port = cfg['tcp_port']
    g_port = cfg['local_game_port']
    db_u = cfg['db_user']
    db_pass = cfg.get('ksweb_mysql_pass', '') if cfg.get('backend') == 'ksweb' else cfg['db_pass']
    db_name = cfg['db_name']
    
    sv1 = f"SRC_5:{ip}:{port}"
    p_info(f"Đang vá cấu hình IP & Database: {ip}:{port}")
    
    # 1. Vá Config.properties cho cấu trúc linh hoạt
    if os.path.exists(paths["GAME_PROPS"]):
        try:
            with open(paths["GAME_PROPS"], 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            new_lines = []
            for line in lines:
                if line.startswith("database.host="): line = "database.host=127.0.0.1\n"
                elif line.startswith("database.port="): line = "database.port=3306\n"
                elif line.startswith("database.name="): line = f"database.name={db_name}\n"
                elif line.startswith("database.user="): line = f"database.user={db_u}\n"
                elif line.startswith("database.pass="): line = f"database.pass={db_pass}\n"
                elif line.startswith("server.port="): line = f"server.port={g_port}\n"
                elif line.startswith("server.ip="): line = "server.ip=127.0.0.1\n"
                elif line.startswith("server.sv1="): line = f"server.sv1={sv1}\n"
                new_lines.append(line)
            with open(paths["GAME_PROPS"], 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            p_ok(f"{os.path.basename(paths['GAME_PROPS'])} → Cập nhật thành công")
        except: pass

    # 2. Vá LocalManager.java (DB credentials & Collation MariaDB 11)
    if os.path.exists(paths["DB_SERVICE"]):
        with open(paths["DB_SERVICE"], 'r', encoding='utf-8') as f: content = f.read()
        
        # Sửa JDBC url trong LocalManager
        if 'jdbc:mysql' in content.lower():
            if 'detectCustomCollations' not in content:
                p_info("   [+] Áp dụng JDBC URL Collation Patch (MariaDB 11)...")
                params = "&useSSL=false&connectionCollation=utf8_general_ci&characterEncoding=UTF-8&useUnicode=yes&serverTimezone=Asia/Ho_Chi_Minh&useLegacyDatetimeCode=false&detectCustomCollations=false"
                content = re.sub(r'(\?useUnicode=[^"]+)', r'?useUnicode=yes', content)
                content = re.sub(r'(jdbc:mysql://[^"]+)', r'\1' + params, content, flags=re.IGNORECASE)
        
        with open(paths["DB_SERVICE"], 'w', encoding='utf-8') as f: f.write(content)
        p_ok(f"{os.path.basename(paths['DB_SERVICE'])} → Cập nhật thành công")

    # 3. Vá DataGame.java
    if os.path.exists(paths["DATA_GAME"]):
        with open(paths["DATA_GAME"], 'r', encoding='utf-8') as f: content = f.read()
        content = re.sub(r'LINK_IP_PORT\s*=\s*".*?"', f'LINK_IP_PORT = "SRC_5:{ip}:{port}:0"', content)
        with open(paths["DATA_GAME"], 'w', encoding='utf-8') as f: f.write(content)
        p_ok("DataGame.java → LINK_IP_PORT")

    # 4. GUI Bypass cho ServerManager.java (Headless mode)
    if os.path.exists(paths["SERVER_MANAGER"]):
        fp = paths["SERVER_MANAGER"]
        p_info("Đang tự động vá lỗi GUI và vá lỗi tương thích Termux...")
        os.system(f"sed -i '/JFrame\\|JPanel\\|setVisible\\|setBounds\\|JOptionPane/s/^/\\/\\//' '{fp}'")
        os.system(f"sed -i '/frame\\./s/^/\\/\\//' '{fp}'")
        os.system(f"sed -i '/cmd \\/c/s/^/\\/\\//' '{fp}'")
        os.system(f"sed -i '/ProcessBuilder(\"cmd\"/s/^/\\/\\//' '{fp}'")
        os.system(f"sed -i '/processBuilder\\./s/^/\\/\\//' '{fp}'")
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

    # 5. Sửa lỗi ký tự BOM ẩn trong file Java
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

    # 6. Nâng cấp MySQL Driver cho project (Fix lỗi MariaDB 11)
    lib_dir = os.path.join(paths["GAME_DIR"], "lib")
    if os.path.exists(lib_dir):
        p_info("Đang đồng bộ Driver MySQL (Fix MariaDB 11)...")
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

    # 7. Tự động vá lỗi hiển thị CPU âm (-100%) và RAM ảo (90%) trên Termux/Linux
    p_info("Đang quét và tối ưu hóa logic hiển thị CPU/RAM...")
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
                        if "getSystemCpuLoad()" in java_content:
                            java_content = re.sub(
                                r'(\w+)\.getSystemCpuLoad\(\)',
                                r'(\1.getSystemCpuLoad() >= 0 && !Double.isNaN(\1.getSystemCpuLoad()) ? \1.getSystemCpuLoad() : (0.05 + (double)(Thread.activeCount() % 15) / 100.0))',
                                java_content
                            )
                            modified = True
                            
                        if "getProcessCpuLoad()" in java_content:
                            java_content = re.sub(
                                r'(\w+)\.getProcessCpuLoad\(\)',
                                r'(\1.getProcessCpuLoad() >= 0 && !Double.isNaN(\1.getProcessCpuLoad()) ? \1.getProcessCpuLoad() : (0.05 + (double)(Thread.activeCount() % 15) / 100.0))',
                                java_content
                            )
                            modified = True
                            
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
                    except: pass
        if patched_count > 0: p_ok(f"Sửa lỗi hiển thị CPU/RAM trên {patched_count} tệp Java!")

    # 8. Biên dịch Source Code bằng Ant
    p_info("Đang chuẩn bị dọn dẹp và biên dịch bằng Ant...")
    os.system(f"rm -rf '{os.path.join(paths['GAME_DIR'], 'build')}'")
    os.system(f"rm -rf '{os.path.join(paths['GAME_DIR'], 'dist')}'")

    env = os.environ.copy()
    java_exe = shutil.which("java")
    if java_exe:
        env["JAVA_HOME"] = os.path.dirname(os.path.dirname(os.path.realpath(java_exe)))
    else:
        p_err("Chưa cài đặt JAVA!"); wait(); return

    res = subprocess.run(["ant", "jar"], cwd=paths["GAME_DIR"], env=env)

    if res.returncode == 0: 
        p_ok("Biên dịch game thành công!")
        cfg["status"]["build"] = True; save_config(cfg)
    else: 
        p_err("Biên dịch thất bại!")
    wait()

# ==========================================
# [6] CẤU HÌNH RAM & SWAP
# ==========================================
def config_ram(cfg):
    p_h("CẤU HÌNH RAM & SWAP TỐI ƯU")
    total, avail, swap_total, swap_free = 4096, 2048, 0, 0
    
    try:
        mem = subprocess.check_output(["cat", "/proc/meminfo"]).decode()
        total = int(re.search(r"MemTotal:\s+(\d+)", mem).group(1)) // 1024
        avail = int(re.search(r"MemAvailable:\s+(\d+)", mem).group(1)) // 1024
        swap_total = int(re.search(r"SwapTotal:\s+(\d+)", mem).group(1)) // 1024
        swap_free = int(re.search(r"SwapFree:\s+(\d+)", mem).group(1)) // 1024
    except: pass

    used = total - avail
    pct = max(0, min(20, int(used * 20 / total))) if total > 0 else 10
    print(f"  {C.BOLD}HỆ THỐNG PHÁT HIỆN:{C.E}")
    print(f"  • RAM Thật      : [{'█' * pct}{'░' * (20-pct)}] {used}MB / {total}MB")
    print(f"  • RAM Ảo (Swap) : {swap_total - swap_free}MB / {swap_total}MB")

    if total <= 1024: suggest_opt, suggest_high, suggest_low = 256, 384, 192
    elif total <= 2048: suggest_opt, suggest_high, suggest_low = 512, 768, 256
    elif total <= 4096: suggest_opt, suggest_high, suggest_low = 1024, 1536, 384
    elif total <= 6144: suggest_opt, suggest_high, suggest_low = 2048, 3072, 512
    else:
        suggest_opt = (total // 2 // 128) * 128
        suggest_high = (int(total * 0.7) // 128) * 128
        suggest_low = 512

    print(f"\n  {C.BOLD}CẤU HÌNH GỢI Ý CHO MÁY BẠN:{C.E}")
    print(f"  • {C.G}Chế độ 1 (Tối ưu/Cân bằng){C.E} : {C.Y}{suggest_opt}m{C.E}")
    print(f"  • {C.B}Chế độ 2 (Hiệu năng cao){C.E}     : {C.Y}{suggest_high}m{C.E}")
    print(f"  • {C.CY}Chế độ 3 (Tiết kiệm tối đa){C.E}  : {C.Y}{suggest_low}m{C.E}")

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
            mode_name, mode_code, suggest = "Tối ưu nhất", "opt", f"{suggest_opt}m"
        elif ch == "2":
            mode_name, mode_code, suggest = "Hiệu năng cao", "high", f"{suggest_high}m"
        else:
            mode_name, mode_code, suggest = "Tiết kiệm cực hạn", "low", f"{suggest_low}m"

        p_info(f"Đang thiết lập chế độ: {mode_name}")
        val = input(f"Nhập mức RAM bạn muốn cấp (VD: 512m, 1g) [Mặc định: {suggest}]: ").strip()
        if not val: val = suggest
        if not val.endswith(('m','g','M','G')): val += 'm'
        val = val.lower()
        
        cfg['jvm_xmx'] = val
        cfg['jvm_mode'] = mode_code
        save_config(cfg)
        p_ok(f"Đã đặt JVM RAM = {val} và chế độ {mode_name}.")
        
    elif ch == "4":
        p_info("Đang kiểm tra quyền ROOT trên thiết bị...")
        is_root = False
        try:
            res = subprocess.run(["su", "-c", "id"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
            if res.returncode == 0 and b"uid=0(root)" in res.stdout: is_root = True
        except: pass

        if not is_root:
            p_err("Thiết bị của bạn CHƯA ĐƯỢC ROOT hoặc chưa cấp quyền ROOT!")
            wait()
        else:
            p_ok("Đã xác nhận quyền ROOT thành công!")
            print("  1. Bật Swap (Khuyên dùng: 2048MB)")
            print("  2. Tắt Swap hiện có")
            sw_ch = input(f"\n{C.BOLD}Chọn: {C.E}").strip()
            if sw_ch == "1":
                size_mb = input("Nhập dung lượng Swap mong muốn (MB) [Mặc định: 2048]: ").strip() or "2048"
                try:
                    size_mb = int(size_mb)
                    cmds = [
                        f"su -c 'dd if=/dev/zero of=/data/swapfile bs=1M count={size_mb}'",
                        "su -c 'chmod 600 /data/swapfile'",
                        "su -c 'mkswap /data/swapfile'",
                        "su -c 'swapon /data/swapfile'"
                    ]
                    success = True
                    for cmd in cmds:
                        ret = os.system(cmd)
                        if ret != 0 and "swapon" not in cmd: success = False
                    if success: p_ok("Kích hoạt RAM ảo (Swap) thành công!")
                    else: p_err("Có lỗi xảy ra trong quá trình thiết lập Swap!")
                except ValueError:
                    p_err("Dung lượng nhập vào không hợp lệ!")
                wait()
            elif sw_ch == "2":
                ret = os.system("su -c 'swapoff /data/swapfile && rm -f /data/swapfile'")
                if ret == 0: p_ok("Đã tắt Swap thành công!")
                wait()

# ==========================================
# BACKUP DAEMON
# ==========================================
def is_backup_daemon_running():
    try:
        res = subprocess.run(["tmux", "has-session", "-t", "nro_backup_daemon"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except: return False

def start_backup_daemon_tmux():
    try:
        cfg = load_config()
        bcfg = cfg.get("backup_daemon", {})
        backup_dir = bcfg.get("backup_dir", os.path.join(HOME, "nro_backups"))
        os.makedirs(backup_dir, exist_ok=True)
        boot_log = os.path.join(backup_dir, "backup_daemon_boot.log")
        
        if os.path.exists(boot_log):
            try: os.remove(boot_log)
            except: pass

        script_path = os.path.abspath(__file__) if '__file__' in globals() else os.path.abspath(sys.argv[0])
        script_dir = os.path.dirname(script_path)
        script_name = os.path.basename(script_path)
        
        os.system("tmux kill-session -t nro_backup_daemon 2>/dev/null")
        time.sleep(0.3)
        if os.system("tmux new-session -d -s nro_backup_daemon") != 0: return False
        time.sleep(0.5)
        
        cmd = f"cd \"{script_dir}\" && {sys.executable} \"{script_name}\" --backup-daemon > \"{boot_log}\" 2>&1"
        os.system(f"tmux send-keys -t nro_backup_daemon '{cmd}' C-m")
        return True
    except: return False

def run_backup_daemon():
    cfg = load_config()
    bcfg = cfg.get("backup_daemon", {})
    interval = int(bcfg.get("interval_hours", 1)) * 3600
    max_backups = int(bcfg.get("max_backups", 24))
    backup_dir = bcfg.get("backup_dir", os.path.join(HOME, "nro_backups"))
    db_name = cfg.get('db_name', 'src_5')
    
    try: os.makedirs(backup_dir, exist_ok=True)
    except:
        backup_dir = os.path.join(HOME, "nro_backups")
        os.makedirs(backup_dir, exist_ok=True)
        
    log_file = os.path.join(backup_dir, "backup_daemon.log")
    
    def log_msg(msg):
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n"
        print(line, end=""); sys.stdout.flush()
        try:
            with open(log_file, "a") as f: f.write(line)
        except: pass

    log_msg("=== KHỞI ĐỘNG TIẾN TRÌNH SAO LƯU TỰ ĐỘNG ===")
    
    while True:
        try:
            timestamp_str = time.strftime("%Y%m%d_%H%M%S")
            out_file = os.path.join(backup_dir, f"backup_{db_name}_{timestamp_str}.sql")
            
            if cfg.get('backend') == 'ksweb':
                ksweb_pass = cfg.get('ksweb_mysql_pass', '')
                dump_cmd = f"mariadb-dump -h 127.0.0.1 -u root -p'{ksweb_pass}'" if ksweb_pass else "mariadb-dump -h 127.0.0.1 -u root"
            else: dump_cmd = "mariadb-dump -u root"
                
            cmd = f"{dump_cmd} {db_name} > \"{out_file}\""
            res = os.system(cmd)
            
            if res == 0:
                log_msg(f"Sao lưu thành công: {os.path.basename(out_file)}")
                try:
                    all_files = []
                    for f_name in os.listdir(backup_dir):
                        if f_name.startswith(f"backup_{db_name}_") and f_name.endswith(".sql"):
                            fp = os.path.join(backup_dir, f_name)
                            all_files.append((fp, os.path.getmtime(fp)))
                    all_files.sort(key=lambda x: x[1])
                    if len(all_files) > max_backups:
                        for f_p, _ in all_files[:len(all_files) - max_backups]:
                            os.remove(f_p)
                            log_msg(f"Đã xóa file cũ: {os.path.basename(f_p)}")
                except: pass
        except Exception as e: log_msg(f"Lỗi hệ thống: {str(e)}")
        time.sleep(interval)

def manage_auto_backup(cfg):
    while True:
        os.system("clear")
        p_h("TỰ ĐỘNG SAO LƯU XOAY VÒNG (BACKUP DAEMON)")
        is_running = is_backup_daemon_running()
        print(f"  • Trạng thái Daemon: {'ONLINE' if is_running else 'OFFLINE'}")
        print("[1] Bật tiến trình sao lưu tự động (Chạy ngầm tmux)")
        print("[2] Tắt tiến trình sao lưu tự động")
        print("[0] Quay lại")
        ch = input(f"\n{C.BOLD}Chọn: {C.E}").strip()
        if ch == "1" and not is_running: start_backup_daemon_tmux()
        elif ch == "2" and is_running: os.system("tmux kill-session -t nro_backup_daemon 2>/dev/null")
        elif ch == "0": break

# ==========================================
# [7] QUẢN LÝ DỊCH VỤ LEMP
# ==========================================
def manage_lemp(cfg):
    if cfg.get('backend') == 'ksweb':
        p_h("TRẠNG THÁI & HƯỚNG DẪN BẬT KSWEB")
        ks_found, mysql_ok = detect_ksweb()
        print(f"  KSWEB phát hiện: {'✓ Có' if ks_found else '✗ Không'}")
        print(f"  KSWEB MySQL    : {'✓ Online' if mysql_ok else '✗ Offline'}")
        wait(); return

    while True:
        os.system("clear")
        p_h("QUẢN LÝ DỊCH VỤ LEMP")
        print("[1] Khởi chạy toàn bộ dịch vụ (LEMP ON)")
        print("[2] Tắt toàn bộ dịch vụ (LEMP OFF)")
        print("[0] Quay lại")
        ch = input("\nChọn: ")
        
        if ch == "1":
            os.system("pkill -9 nginx; pkill -9 php-fpm")
            time.sleep(1)
            os.system("mariadbd-safe > /dev/null 2>&1 &")
            os.system("php-fpm > /dev/null 2>&1")
            os.system("nginx > /dev/null 2>&1")
            p_ok("Đã khởi chạy Nginx, MariaDB & PHP-FPM!")
            wait()
        elif ch == "2":
            os.system("pkill -9 nginx; pkill -9 php-fpm; pkill -9 mariadbd")
            p_ok("Đã tắt toàn bộ các dịch vụ!")
            wait()
        elif ch == "0": break

# ==========================================
# [8] VẬN HÀNH GAME SERVER
# ==========================================
def launch_server(cfg):
    paths = get_paths(cfg); xmx = cfg['jvm_xmx']
    path = paths["GAME_DIR"]
    
    if not path or not os.path.exists(path):
        p_err(f"Không tìm thấy thư mục của Game Server!"); wait(); return
        
    port = cfg['local_game_port']
    session = f"nro_game_server"
    
    jvm_mode = cfg.get("jvm_mode", "opt")
    if jvm_mode == "low":
        jvm_opts = f"-XX:+UseSerialGC -Xms16m -Xmx{xmx} -Xss160k -XX:CICompilerCount=1 -XX:TieredStopAtLevel=1 -XX:MaxMetaspaceSize=48m -XX:CompressedClassSpaceSize=12m -XX:+UseStringDeduplication"
    elif jvm_mode == "high":
        jvm_opts = f"-XX:+UseG1GC -Xms128m -Xmx{xmx} -Xss384k -XX:MaxGCPauseMillis=100 -XX:+ParallelRefProcEnabled -XX:InitiatingHeapOccupancyPercent=45 -XX:MaxMetaspaceSize=128m"
    else:
        jvm_opts = f"-XX:+UseSerialGC -Xms32m -Xmx{xmx} -Xss256k -XX:CICompilerCount=2 -XX:TieredStopAtLevel=1 -XX:MaxMetaspaceSize=64m -XX:CompressedClassSpaceSize=16m"
        
    main_class = "nro.models.server.ServerManager"
    proj_props = os.path.join(path, "nbproject/project.properties")
    if os.path.exists(proj_props):
        try:
            with open(proj_props, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if line.startswith("main.class="):
                        main_class = line.split("=", 1)[1].strip()
                        break
        except: pass

    jar_cmd = f"java -Duser.timezone=Asia/Ho_Chi_Minh -Djava.awt.headless=true -server {jvm_opts} -cp \"dist/*:lib/*:build/classes\" {main_class}"
    
    p_h(f"VẬN HÀNH GAME SERVER")
    print("[1] Khởi chạy trực tiếp (Xem Log màn hình)")
    print("[2] Khởi chạy ngầm (TMux - Khuyên Dùng)")
    print("[3] Dừng Server (Kill Port & Session)")
    print("[0] Quay lại")
    ch = input("\nChọn: ")
    
    if ch == "1":
        kill_port(port)
        os.chdir(path)
        res = os.system(jar_cmd)
        if res != 0:
            print(f"\n{C.R}[LỖI] Tiến trình đã dừng với mã lỗi {res}. Hãy xem log phía trên!{C.E}")
        wait()
    elif ch == "2":
        kill_port(port)
        os.system(f"tmux kill-session -t {session} 2>/dev/null")
        os.system(f"tmux new-session -d -s {session} 'cd {path} && while true; do {jar_cmd}; echo \"[AUTO-RESTART] Server dang khoi dong lai sau 20 giay...\"; sleep 20; done'")
        p_ok(f"Server Game đã được khởi chạy ngầm trong tmux thành công!")
        wait()
    elif ch == "3":
        kill_port(port)
        os.system(f"tmux kill-session -t {session} 2>/dev/null")
        p_ok(f"Đã tắt Server Game!")
        wait()

# ==========================================
# [A] QUẢN LÝ TÀI KHOẢN (TERMINAL CLI)
# ==========================================
def manage_accounts(cfg):
    p_h("QUẢN LÝ TÀI KHOẢN")
    db_name = cfg.get('db_name', 'src_5')
    db_cmd = get_db_cmd(cfg)
    
    while True:
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

# ==========================================
# [K] CHUYỂN ĐỔI BACKEND
# ==========================================
def switch_backend(cfg):
    p_h("CHUYỂN ĐỔI BACKEND (LEMP ↔ KSWEB)")
    current = cfg.get('backend', 'termux')
    print(f"  [1] Sử dụng LEMP Termux")
    print(f"  [2] Sử dụng KSWEB")
    ch = input(f"\n{C.BOLD}Chọn: {C.E}").strip()
    if ch == "1":
        cfg['backend'] = 'termux'; cfg['db_pass'] = ''; save_config(cfg)
        p_ok("Đã chuyển sang dùng LEMP Termux!")
    elif ch == "2":
        cfg['backend'] = 'ksweb'; cfg['db_pass'] = cfg.get('ksweb_mysql_pass', ''); save_config(cfg)
        p_ok("Đã chuyển sang dùng KSWEB!")
    wait()

# ==========================================
# TRÌNH CHẠY CHÍNH (MAIN LOOP)
# ==========================================
SRC_DOWNLOAD_LINK = "https://drive.google.com/file/d/1u8RRcE-zI1LBd4QcudtjyuYUTxpD5qfP/view?usp=sharing"
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
        g_st = f"{C.G}ON{C.E}" if "ON" in get_st("ServerManager") else f"{C.R}OFF{C.E}"
            
        lemp_st = check_lemp_status(cfg)
        backend = cfg.get('backend', 'termux')
        
        if backend == 'ksweb':
            web_display = cfg.get('web_url', f"http://{get_local_ip()}:8080/{cfg.get('ksweb_web_dir', 'nso_web')}/")
            svc_label = f"Trạng thái KSWEB: {lemp_st}"
        else:
            web_display = cfg.get('web_url', f"http://{get_local_ip()}:8080")
            svc_label = f"Quản lý Dịch vụ LEMP: {lemp_st}"

        mode_str = cfg.get('mode', 'offline').upper()
        ip = cfg.get('tcp_domain', get_local_ip()) if mode_str == 'OFFLINE' else get_local_ip()
        
        os.system("clear")
        print(f"""{C.CY}{C.BOLD}
==========================================
      NRO VNPro5 - DÀNH RIÊNG CHO SRC_5
=========================================={C.E}
 ------------------------------------------
 {C.BOLD}IP:  {C.G}{ip}{C.E} | {C.BOLD}MODE:{C.E} {C.H}{mode_str}{C.E} | {C.BOLD}BACKEND:{C.E} {get_backend_label(cfg)}
 {C.BOLD}WEB ĐĂNG KÝ: {C.CY}{web_display}{C.E}
 ------------------------------------------
 [1] Cài đặt môi trường hệ thống{get_stat(cfg,'env')}
 [2] Giải nén Source game (Scan Download){get_stat(cfg,'source')}
 [3] Thiết lập Database & Web (Auto Fix){get_stat(cfg,'db_web')}
 [4] Cấu hình Kết nối (Online/Offline)
 [5] Vá IP & Build Game{get_stat(cfg,'build')}
 [6] Cấu hình RAM & Swap (Hybrid)
 [7] {svc_label}
 [8] VẬN HÀNH GAME SERVER: {g_st}
 [A] QUẢN LÝ TÀI KHOẢN
 [B] TỰ ĐỘNG SAO LƯU XOAY VÒNG
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
        elif ch == "8": launch_server(cfg)
        elif ch == "A": manage_accounts(cfg)
        elif ch == "B": manage_auto_backup(cfg)
        elif ch == "K": switch_backend(cfg)
        elif ch == "D":
            kill_port(cfg['local_game_port'])
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
    try:
        if "--backup-daemon" in sys.argv:
            run_backup_daemon()
        else:
            main()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        import traceback
        traceback.print_exc()
        input("\n>>> Chương trình gặp lỗi hệ thống! Bấm Enter để thoát...")
