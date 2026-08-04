import os, json, socket, subprocess, time, re, sys, shutil, datetime

# ==========================================
# MÀU SẮC & GIAO DIỆN
# ==========================================
class C:
    H = '\033[95m'; B = '\033[94m'; CY = '\033[96m'; G = '\033[92m'
    Y = '\033[93m'; R = '\033[91m'; E = '\033[0m'; BOLD = '\033[1m'

def p_h(t): print(f"\n{C.H}{C.BOLD}=== {t} ==={C.E}")
def p_ok(t): print(f"{C.G}[✓] {t}{C.E}")
def p_err(t): print(f"{C.R}[✗] {t}{C.E}")
def p_info(t): print(f"{C.CY}[i] {t}{C.E}")

# ==========================================
# CẤU HÌNH
# ==========================================
HOME = os.path.expanduser("~")
CONFIG_FILE = os.path.join(HOME, "nro_config.json")

def load_config():
    defaults = {
        "base_dir": os.path.join(HOME, "NroNew"),
        "db_user": "root", "db_pass": "", "db_name": "ngocrong",
        "tcp_domain": "127.0.0.1", "tcp_port": 14445,
        "local_login_port": 8888, "local_game_port": 14445,
        "mode": "offline", "pma_port": 8081, "jvm_xmx": "512m",
        "backend": "termux", "ksweb_mysql_pass": "",
        "backup_daemon": {
            "interval_hours": 1, "max_backups": 24,
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
            cfg['local_login_port'] = int(cfg.get('local_login_port', 8888))
            cfg['local_game_port'] = int(cfg.get('local_game_port', 14445))
            return cfg
        except: pass
    return dict(defaults)

def save_config(cfg):
    with open(CONFIG_FILE, 'w') as f: json.dump(cfg, f, indent=4)

def get_paths(cfg):
    b = cfg["base_dir"]
    return {
        "BASE": b,
        "LOGIN_DIR": os.path.join(b, "Login"),
        "GAME_DIR": os.path.join(b, "Server"),
        "LOGIN_INI": os.path.join(b, "Login/server.ini"),
        "GAME_PROPS": os.path.join(b, "Server/resources/config/server.properties"),
        "DB_SERVICE": os.path.join(b, "Server/src/main/java/nro/jdbc/DBService.java"),
        "DATA_GAME": os.path.join(b, "Server/src/main/java/nro/data/DataGame.java"),
        "SQL_FILE": os.path.join(b, "ngocrong.sql"),
    }

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close(); return ip
    except:
        try:
            res = subprocess.check_output(
                "ip -4 addr | grep -oP '(?<=inet\\s)\\d+(\\.\\d+){3}' | grep -v '127.0.0.1'",
                shell=True).decode().strip()
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

def get_st(pattern):
    try:
        subprocess.check_output(["pgrep", "-f", pattern], stderr=subprocess.DEVNULL)
        return f"{C.G}ON{C.E}"
    except: return f"{C.R}OFF{C.E}"

def check_status():
    login = get_st("Login")
    game = f"{C.R}OFF{C.E}"
    for p in ["nro.server.ServerManager"]:
        if "ON" in get_st(p): game = f"{C.G}ON{C.E}"; break
    db = get_st("mariadbd")
    return login, game, db

def get_stat(cfg, key):
    return f" {C.G}(OK){C.E}" if cfg.get("status", {}).get(key) else ""

def get_server_status(cfg, stype):
    running = "ON" in get_st("Login" if stype == "login" else "nro.server.ServerManager")
    if running: return f"{C.G}ON{C.E}"
    session = "nro_login" if stype == "login" else "nro_game"
    try:
        res = subprocess.run(["tmux", "has-session", "-t", session],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0: return f"{C.Y}AUTO-START{C.E}"
    except: pass
    return f"{C.R}OFF{C.E}"

# ==========================================
# KSWEB HYBRID - HÀM TIỆN ÍCH (từ nro4, thêm mới)
# ==========================================
def detect_ksweb():
    ksweb_found = os.path.exists("/sdcard/htdocs")
    mysql_ok = False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2); s.connect(("127.0.0.1", 3306)); s.close()
        mysql_ok = True
    except: pass
    return ksweb_found, mysql_ok

def get_db_cmd(cfg):
    if cfg.get('backend') == 'ksweb':
        ksweb_pass = cfg.get('ksweb_mysql_pass', '')
        if ksweb_pass: return f"mariadb -h 127.0.0.1 -u root -p'{ksweb_pass}'"
        return "mariadb -h 127.0.0.1 -u root"
    return "mariadb -u root"

def get_backend_label(cfg):
    return f"{C.G}KSWEB{C.E}" if cfg.get('backend') == 'ksweb' else f"{C.B}TERMUX (LEMP){C.E}"

def switch_backend(cfg):
    p_h("CHUYỂN ĐỔI BACKEND (LEMP ↔ KSWEB)")
    cur = cfg.get('backend', 'termux')
    print(f"Backend hiện tại: {get_backend_label(cfg)}")
    ksweb_found, mysql_ok = detect_ksweb()
    print(f"Phát hiện KSWEB (thư mục /sdcard/htdocs): {'CÓ' if ksweb_found else 'KHÔNG'}")
    print(f"MariaDB/MySQL đang lắng nghe cổng 3306: {'CÓ' if mysql_ok else 'KHÔNG'}")
    print("\n[1] Dùng LEMP Termux (mariadb/nginx/php gốc)")
    print("[2] Dùng KSWEB (app KSWEB quản lý MySQL/Web riêng)")
    print("[0] Hủy")
    ch = input(f"\n{C.BOLD}Chọn: {C.E}").strip()
    if ch == "1":
        cfg['backend'] = 'termux'; cfg['db_pass'] = ''
        save_config(cfg); p_ok("Đã chuyển sang LEMP Termux!")
    elif ch == "2":
        if not ksweb_found:
            p_err("Không tìm thấy /sdcard/htdocs - hãy cài và mở app KSWEB trước!")
        pw = input("Nhập mật khẩu MySQL root của KSWEB (Enter nếu không có): ").strip()
        cfg['backend'] = 'ksweb'; cfg['ksweb_mysql_pass'] = pw; cfg['db_pass'] = pw
        save_config(cfg); p_ok("Đã chuyển sang KSWEB!")
    input("\nEnter...")

# ==========================================
# [1] CÀI ĐẶT MÔI TRƯỜNG
# ==========================================
def install_env(cfg):
    p_h("CÀI ĐẶT MÔI TRƯỜNG")
    print(f"{C.H}Chọn kiến trúc Database & Web:{C.E}")
    print("[1] Mặc định (LEMP Termux - MariaDB/Nginx/PHP) - giữ nguyên như trước")
    print("[2] Dùng KSWEB (nếu máy bị lỗi CSDL Termux, cần cài app KSWEB riêng)")
    b_ch = input(f"\n{C.BOLD}Lựa chọn (Enter = 1): {C.E}").strip()
    if b_ch == "2":
        cfg['backend'] = 'ksweb'; save_config(cfg)
        pkgs = ["openjdk-17", "maven", "wget", "unzip", "unrar", "tar", "git", "tmux", "psmisc", "lsof"]
    else:
        cfg['backend'] = 'termux'; save_config(cfg)
        pkgs = ["openjdk-17", "mariadb", "nginx", "php", "php-fpm", "maven",
                "wget", "unzip", "unrar", "tar", "git", "tmux", "psmisc", "lsof"]
    p_info("Đang cập nhật hệ thống (Cực kỳ tự động)...")
    env = os.environ.copy()
    env["DEBIAN_FRONTEND"] = "noninteractive"
    subprocess.run(["pkg", "update", "-y"], env=env)
    # Dùng apt upgrade với option force-confold để tự động chọn giữ file cấu hình cũ, không hỏi người dùng
    subprocess.run(["apt", "upgrade", "-y", "-o", "Dpkg::Options::=--force-confold"], env=env)
    for pkg in pkgs:
        p_info(f"Đang cài {pkg}...")
        subprocess.run(["pkg", "install", pkg, "-y"])
    p_ok("Cài đặt và cập nhật hoàn tất!")
    cfg["status"]["env"] = True; save_config(cfg)

# ==========================================
# [2] GIẢI NÉN SOURCE
# ==========================================
def extract_source(cfg):
    p_h("GIẢI NÉN SOURCE")
    scan_paths = [HOME, "/sdcard/Download"]
    all_files = []
    for path in scan_paths:
        if os.path.exists(path):
            try:
                files = [(f, path) for f in os.listdir(path) if any(f.endswith(e) for e in [".zip", ".rar", ".tar.gz"])]
                all_files.extend(files)
            except: continue

    if not all_files:
        p_err("Không tìm thấy file nén trong ~/ hoặc /sdcard/Download")
        p_info("Mẹo: Hãy đảm bảo bạn đã chạy 'termux-setup-storage' để script có quyền truy cập bộ nhớ.")
        return
    
    for i, (f, p) in enumerate(all_files):
        loc = "Download" if "Download" in p else "Home"
        print(f"[{i+1}] {f} ({loc})")
        
    c = input("\nChọn file để giải nén (0=hủy): ")
    if not c or c == "0": return
    
    sel_file, sel_path = all_files[int(c)-1]
    full_path = os.path.join(sel_path, sel_file)
    
    target = os.path.join(HOME, "NroNew")
    os.makedirs(target, exist_ok=True)
    
    p_info(f"Đang giải nén: {sel_file}...")
    if sel_file.endswith(".zip"):
        subprocess.run(["unzip", "-o", full_path, "-d", target])
    elif sel_file.endswith(".rar"):
        subprocess.run(["unrar", "x", "-o+", full_path, target + "/"])
    elif sel_file.endswith(".tar.gz"):
        subprocess.run(["tar", "-xf", full_path, "-C", target])

    inner = os.path.join(target, "SRC NRO NEW 01")
    if os.path.isdir(inner):
        p_info("Sửa lỗi thư mục lồng nhau...")
        os.system(f"mv '{inner}'/* {target}/ 2>/dev/null; rm -rf '{inner}'")
        
    os.system(f"chmod -R 777 {target}")
    p_ok("Giải nén & Phân quyền thành công!")
    cfg["base_dir"] = target; cfg["status"]["source"] = True; save_config(cfg)
    input("\nNhấn Enter để tiếp tục...")

# [3] THIẾT LẬP DATABASE & WEB (LEMP)
# ==========================================
def setup_db_ksweb(cfg):
    p_h("THIẾT LẬP DATABASE (KSWEB)")
    ksweb_found, mysql_ok = detect_ksweb()
    if not mysql_ok:
        p_err("Không kết nối được MySQL trên 127.0.0.1:3306 - hãy mở app KSWEB và bật MySQL trước!")
        input("\nEnter..."); return
    db_cmd = get_db_cmd(cfg)
    paths = get_paths(cfg)
    db_name = cfg.get('db_name', 'ngocrong')
    os.system(f"{db_cmd} -e 'CREATE DATABASE IF NOT EXISTS {db_name};'")
    if os.path.exists(paths['SQL_FILE']):
        p_info(f"Đang import database: {os.path.basename(paths['SQL_FILE'])}...")
        os.system(f"{db_cmd} {db_name} < '{paths['SQL_FILE']}'")
        p_ok(f"Import {db_name} thành công!")
    else:
        p_info("Không tìm thấy file .sql - hãy đảm bảo file nằm trong thư mục dự án.")
    p_ok("Database KSWEB đã sẵn sàng! (Web/PMA quản lý qua app KSWEB)")
    cfg["status"]["db_web"] = True; save_config(cfg)
    input("\nEnter...")

def setup_db(cfg):
    if cfg.get('backend') == 'ksweb':
        setup_db_ksweb(cfg); return
    p_h("THIẾT LẬP DATABASE & WEB (LEMP)")
    p_info("Đang đảm bảo các gói hệ thống...")
    os.system("pkg install nginx mariadb php php-fpm wget tar -y")

    p_info("Đang cấu hình MariaDB...")
    if not os.path.exists(os.path.join(os.environ['PREFIX'], "var/lib/mysql")):
        os.system("mysql_install_db")
    
    os.system("mariadbd-safe > /dev/null 2>&1 &")
    time.sleep(4)

    sql_cmds = [
        "ALTER USER 'root'@'localhost' IDENTIFIED BY '';",
        "GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost' WITH GRANT OPTION;",
        "FLUSH PRIVILEGES;"
    ]
    for cmd in sql_cmds:
        os.system(f"mariadb -u root -e \"{cmd}\"")
    p_ok("Đã cấu hình MariaDB (User: root / No Pass)")

    paths = get_paths(cfg)
    db_name = cfg.get('db_name', 'ngocrong')
    if os.path.exists(paths['SQL_FILE']):
        p_info(f"Đang import database: {os.path.basename(paths['SQL_FILE'])}...")
        os.system(f"mariadb -u root -e 'CREATE DATABASE IF NOT EXISTS {db_name};'")
        os.system(f"mariadb -u root {db_name} < '{paths['SQL_FILE']}'")
        p_ok(f"Import {db_name} thành công!")

    web_dir = os.path.join(HOME, "phpmyadmin")
    if not os.path.exists(os.path.join(web_dir, "index.php")):
        p_info("Đang tải và giải nén phpMyAdmin mới nhất...")
        pma_url = "https://www.phpmyadmin.net/downloads/phpMyAdmin-latest-all-languages.tar.gz"
        pma_tar = os.path.join(HOME, "pma.tar.gz")
        os.system(f"wget {pma_url} -O {pma_tar}")
        os.system(f"tar -xf {pma_tar} -C {HOME}")
        extracted = [d for d in os.listdir(HOME) if d.startswith("phpMyAdmin-") and os.path.isdir(os.path.join(HOME, d))]
        if extracted:
            os.system(f"rm -rf {web_dir}")
            os.system(f"mv {os.path.join(HOME, extracted[0])} {web_dir}")
        os.system(f"rm -f {pma_tar}")
    
    pma_config = os.path.join(web_dir, "config.inc.php")
    pma_sample = os.path.join(web_dir, "config.sample.inc.php")
    if not os.path.exists(pma_config) and os.path.exists(pma_sample):
        os.system(f"cp {pma_sample} {pma_config}")
    
    if os.path.exists(pma_config):
        with open(pma_config, 'r') as f: content = f.read()
        content = content.replace("'localhost'", "'127.0.0.1'")
        content = content.replace("AllowNoPassword'] = false", "AllowNoPassword'] = true")
        if "$cfg['blowfish_secret'] = '';" in content:
            content = content.replace("$cfg['blowfish_secret'] = '';", "$cfg['blowfish_secret'] = 'vantuannro2026_super_secret_key';")
        with open(pma_config, 'w') as f: f.write(content)
        p_ok("Đã cấu hình config.inc.php (127.0.0.1)")

    nginx_conf = os.path.join(os.environ['PREFIX'], "etc/nginx/nginx.conf")
    nginx_template = f"""
worker_processes  1;
events {{
    worker_connections  1024;
}}
http {{
    include       mime.types;
    default_type  application/octet-stream;
    sendfile        on;
    keepalive_timeout  65;

    server {{
        listen       8081;
        server_name  localhost;
        root         {web_dir};
        index        index.php index.html index.htm;

        location / {{
            try_files $uri $uri/ =404;
        }}

        location ~ \.php$ {{
            try_files $uri =404;
            fastcgi_pass   127.0.0.1:9000;
            fastcgi_index  index.php;
            fastcgi_param  SCRIPT_FILENAME  $document_root$fastcgi_script_name;
            include        fastcgi_params;
        }}
    }}
}}
"""
    with open(nginx_conf, 'w') as f: f.write(nginx_template)
    
    fpm_conf = os.path.join(os.environ['PREFIX'], "etc/php-fpm.d/www.conf")
    if os.path.exists(fpm_conf):
        with open(fpm_conf, 'r') as f: c = f.read()
        c = re.sub(r'^listen\s*=.*', 'listen = 127.0.0.1:9000', c, flags=re.M)
        with open(fpm_conf, 'w') as f: f.write(c)

    pma_idx = os.path.join(web_dir, "index.php")
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
                if has_declare:
                    if "declare(strict_types=1)" in line:
                        new_lines.append(fix_code)
                        inserted = True
                elif "<?php" in line:
                    new_lines.append(fix_code)
                    inserted = True
        with open(pma_idx, 'w') as f: f.writelines(new_lines)
        p_ok("Đã vá lỗi tương thích PHP 8.4 (Vị trí an toàn)")

    p_info("Đang khởi động lại dịch vụ...")
    os.system("pkill -9 nginx; pkill -9 php-fpm")
    time.sleep(1)
    os.system("php-fpm")
    os.system("nginx")
    
    cfg["status"]["db_web"] = True; save_config(cfg)
    p_ok(f"Hệ thống Database & Web đã SẴN SÀNG!")
    p_info(f"Truy cập: http://{get_local_ip()}:8081")
    p_info("User: root | Pass: (Trống)")
    input("\nEnter...")

# ==========================================
# [4] CẤU HÌNH KẾT NỐI (Online/Offline)
# ==========================================
def manage_tcp(cfg):
    if "LD_PRELOAD" in os.environ: del os.environ["LD_PRELOAD"]
    p_h("CẤU HÌNH KẾT NỐI (ONLINE/OFFLINE)")
    print(f"Chế độ kết nối hiện tại: {C.H}{cfg.get('mode','offline').upper()}{C.E}")
    print(f"IP/Domain kết nối: {C.Y}{cfg['tcp_domain']}:{cfg['tcp_port']}{C.E}\n")

    print("[1] Cài đặt Ngrok (Tối ưu cho Termux ARM64)")
    print("[2] Khởi chạy & Quản lý Ngrok (TCP)")
    print("[3] Cấu hình Online: Tự động lấy link Ngrok đang mở (Port 4040)")
    print("[4] Cấu hình Online: Nhập liên kết thủ công (Ngrok/Playit/Bore)")
    print("[5] Cấu hình Offline: Chạy mạng LAN/WiFi (Sử dụng IP máy)")
    print("[6] Cấu hình Offline: Chạy trên máy ảo (Localhost 127.0.0.1)")
    print("[0] Quay lại")
    ch = input(f"\n{C.BOLD}Chọn: {C.E}").strip().upper()

    if ch == "1":
        p_info("Đang cài đặt môi trường giả lập (proot) để vá lỗi DNS Ngrok...")
        subprocess.run(["pkg", "install", "proot", "dnsutils", "-y"])
        p_info("Đang tải Ngrok ARM64 chính chủ cho Termux...")
        os.system("wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.tgz -O ngrok.tgz")
        os.system("tar -xvzf ngrok.tgz")
        os.system(f"mv ngrok {os.environ.get('PREFIX','/data/data/com.termux/files/usr')}/bin/")
        os.system(f"chmod +x {os.environ.get('PREFIX','/data/data/com.termux/files/usr')}/bin/ngrok")
        os.system("rm -f ngrok.tgz")
        p_ok("Đã cài đặt Ngrok thành công!")
        tk = input(f"{C.CY}Nhập AuthToken (Bỏ trống nếu đã nhập trước đó): {C.E}")
        if tk.strip():
            os.system(f"ngrok config add-authtoken {tk.strip()}")
            p_ok("Đã lưu AuthToken!")

    elif ch == "2":
        print("\n[1] Chạy trực tiếp (Xem Log - Bấm Ctrl+C để thoát)")
        print("[2] Chạy ngầm Ngrok (Tmux - Không lo tắt nhầm)")
        print("[0] Tắt dịch vụ Ngrok đang chạy")
        sc = input(f"\n{C.BOLD}Chọn: {C.E}").strip()
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
        elif sc == "0":
            subprocess.run(["pkill", "-9", "ngrok"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            subprocess.run(["tmux", "kill-session", "-t", "nro_ngrok"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            p_ok("Đã tắt dịch vụ Ngrok!")

    elif ch == "3":
        try:
            import urllib.request
            with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels") as r:
                tunnels = json.loads(r.read().decode()).get('tunnels', [])
                if not tunnels: p_err("Không thấy tunnel nào đang mở!")
                else:
                    t = tunnels[0]
                    u = t['public_url'].replace('tcp://', '')
                    d, p = u.rsplit(':', 1)
                    cfg['mode'] = 'online'; cfg['tcp_domain'] = d; cfg['tcp_port'] = int(p)
                    save_config(cfg)
                    p_ok(f"Lưu cấu hình ONLINE thành công: {d}:{p}")
                    p_info("Lưu ý: Hãy chạy mục [5] để áp dụng IP mới vào source.")
        except Exception as e:
            p_err(f"Lỗi: Hãy chắc chắn bạn đã kích hoạt Ngrok trước! ({e})")

    elif ch == "4":
        p_info("VD: bore.pub:6489 | 0.tcp.ap.ngrok.io:12345 | abc.at.playit.gg:30000")
        link = input("Nhập địa chỉ: ").strip().replace("tcp://", "")
        if ':' in link:
            d, p = link.rsplit(':', 1)
            cfg['mode'] = 'online'; cfg['tcp_domain'] = d; cfg['tcp_port'] = int(p)
            save_config(cfg); p_ok(f"Lưu cấu hình ONLINE thành công: {d}:{p}")
            p_info("Lưu ý: Hãy chạy mục [5] để áp dụng IP mới vào source.")
        else: p_err("Sai format! Cần Domain:Port")

    elif ch == "5":
        local_ip = get_local_ip()
        cfg['mode'] = 'offline'; cfg['tcp_domain'] = local_ip; cfg['tcp_port'] = cfg['local_game_port']
        save_config(cfg)
        p_ok(f"Lưu cấu hình OFFLINE (LAN/WiFi): {local_ip}:{cfg['tcp_port']}")
        p_info("Lưu ý: Hãy chạy mục [5] Vá IP & Build Game để áp dụng.")

    elif ch == "6":
        cfg['mode'] = 'offline'; cfg['tcp_domain'] = "127.0.0.1"; cfg['tcp_port'] = cfg['local_game_port']
        save_config(cfg)
        p_ok("Lưu cấu hình OFFLINE (Localhost 127.0.0.1) thành công!")
        p_info("Lưu ý: Hãy chạy mục [5] Vá IP & Build Game để áp dụng.")
    input("\nEnter...")

def get_ram_bar():
    try:
        res = subprocess.check_output("free -m", shell=True).decode()
        lines = res.split('\n')
        mem = lines[1].split()
        total, used = int(mem[1]), int(mem[2])
        percent = int(used * 100 / total)
        bar_len = 20
        filled = int(percent * bar_len / 100)
        bar = "█" * filled + "░" * (bar_len - filled)
        color = C.G if percent < 70 else (C.Y if percent < 90 else C.R)
        return f"{color}[{bar}] {percent}% ({used}MB/{total}MB){C.E}"
    except: return "[N/A]"

def check_lemp_status(cfg=None):
    if cfg and cfg.get('backend') == 'ksweb':
        return f"{C.G}KSWEB OK{C.E}" if detect_ksweb()[1] else f"{C.R}KSWEB OFF{C.E}"
    nginx = subprocess.run(["pgrep", "nginx"], stdout=subprocess.DEVNULL).returncode == 0
    mysql = subprocess.run(["pgrep", "mariadbd"], stdout=subprocess.DEVNULL).returncode == 0
    php = subprocess.run(["pgrep", "php-fpm"], stdout=subprocess.DEVNULL).returncode == 0
    if nginx and mysql and php: return f"{C.G}OK{C.E}"
    if not nginx and not mysql and not php: return f"{C.R}OFF{C.E}"
    return f"{C.Y}PARTIAL{C.E}"

def manage_lemp(cfg):
    if cfg.get('backend') == 'ksweb':
        p_h("QUẢN LÝ DỊCH VỤ (KSWEB)")
        print(f"Trạng thái KSWEB: {check_lemp_status(cfg)}")
        p_info("Backend đang là KSWEB - hãy bật/tắt MySQL/Web trực tiếp trong app KSWEB.")
        p_info("Dùng menu [K] để chuyển lại LEMP Termux nếu cần.")
        input("\nEnter..."); return
    p_h("QUẢN LÝ DỊCH VỤ LEMP")
    print(f"Trạng thái hiện tại: LEMP: {check_lemp_status(cfg)}")
    print("-" * 30)
    print("[1] Bật dịch vụ (Start)")
    print("[2] Tắt dịch vụ (Stop)")
    print("[3] Xóa sạch môi trường (Wipe/Reset)")
    print("[0] Quay lại")
    c = input(f"\n{C.BOLD}Lựa chọn: {C.E}").upper()
    if c == "1":
        os.system("php-fpm > /dev/null 2>&1; nginx > /dev/null 2>&1; mariadbd-safe > /dev/null 2>&1 &")
        p_ok("Đã khởi động!")
    elif c == "2":
        os.system("pkill -9 nginx; pkill -9 php-fpm; pkill -9 mariadbd")
        p_ok("Đã tắt!")
    elif c == "3":
        confirm = input(f"{C.R}Xóa sạch Database & Config (Y/N)? {C.E}").upper()
        if confirm == "Y":
            os.system("pkill -9 nginx; pkill -9 php-fpm; pkill -9 mariadbd; pkill -9 mysqld")
            os.system(f"rm -rf {os.environ['PREFIX']}/var/lib/mysql")
            os.system(f"rm -rf {os.environ['PREFIX']}/etc/nginx/nginx.conf")
            os.system(f"rm -rf {HOME}/phpmyadmin")
            p_ok("Đã dọn dẹp sạch sẽ!")
    time.sleep(1)

# ==========================================
# [6] VÁ IP & BUILD
# ==========================================
def apply_and_build(cfg):
    p_h("VÁ MÃ NGUỒN & BUILD")
    paths = get_paths(cfg)
    if cfg.get('mode') == 'online':
        ip = resolve_ip(cfg['tcp_domain']); port = cfg['tcp_port']
    else:
        ip = get_local_ip(); port = cfg['local_game_port']
    l_port = cfg['local_login_port']; g_port = cfg['local_game_port']
    db_u = cfg['db_user']; db_p = cfg['db_pass']; db_name = cfg['db_name']
    sv1 = f"KhanhDTK:{ip}:{port}:0,0,0"

    p_info(f"Mode: {cfg.get('mode','offline').upper()} | Online: {ip}:{port}")
    p_info(f"Local: Login={l_port}, Game={g_port}")

    # 1. server.ini
    if os.path.exists(paths["LOGIN_INI"]):
        with open(paths["LOGIN_INI"], 'w') as f:
            f.write(f"# Config\nserver.port={l_port}\ndb.port=3306\ndb.host=127.0.0.1\n")
            f.write(f"db.user={db_u}\ndb.password={db_p}\ndb.name={db_name}\n")
            f.write("db.driver=com.mysql.cj.jdbc.Driver\nadmin.mode=0\n")
        p_ok(f"server.ini → port={l_port}")

    # 2. server.properties
    props_dir = os.path.dirname(paths["GAME_PROPS"])
    if os.path.exists(props_dir):
        with open(paths["GAME_PROPS"], 'w') as f:
            f.write(f"""##config db
server.db.ip=localhost
server.db.port=3306
server.db.name={db_name}
server.db.us={db_u}
server.db.pw={db_p}
server.db.maxactive=99999

##config login
login.host=127.0.0.1
login.port={l_port}

##config server
server.sv=1
server.sv1={sv1}
server.port={g_port}

server.debug=false

server.waitlogin=5
server.maxperip=50
server.maxplayer=1500
server.expserver=3
server.name=KhanhDTK
server.domain=KhanhDTK

server.key=ahskjbdkajsndakjnsdjaksbn324873
server.key2=askjlndfakjsldnaslkjdnakjsn636
server.activeKey=true

api.port=8181
api.key=abcdef

#hikariCP
server.hikari.minIdle=5
server.hikari.poolSize=200
server.hikari.cachePre=true
server.hikari.cacheSize=250
server.hikari.cacheSqlLimit=2048

execute.command=java -Djava.awt.headless=true -jar target/*dependencies.jar

server.event=3
""")
        p_ok(f"server.properties → sv1={sv1}")

    # 3. DBService.java
    if os.path.exists(paths["DB_SERVICE"]):
        with open(paths["DB_SERVICE"], 'r', encoding='utf-8') as f: content = f.read()
        content = re.sub(r'DB_HOST\s*=\s*".*?"', 'DB_HOST = "127.0.0.1"', content)
        content = re.sub(r'DB_NAME\s*=\s*".*?"', f'DB_NAME = "{db_name}"', content)
        content = re.sub(r'DB_USER\s*=\s*".*?"', f'DB_USER = "{db_u}"', content)
        content = re.sub(r'DB_PASSWORD\s*=\s*".*?"', f'DB_PASSWORD = "{db_p}"', content)
        with open(paths["DB_SERVICE"], 'w', encoding='utf-8') as f: f.write(content)
        p_ok("DBService.java → DB config")

    # 4. DataGame.java
    if os.path.exists(paths["DATA_GAME"]):
        with open(paths["DATA_GAME"], 'r', encoding='utf-8') as f: content = f.read()
        content = re.sub(r'LINK_IP_PORT\s*=\s*".*?"', f'LINK_IP_PORT = "{sv1}"', content)
        with open(paths["DATA_GAME"], 'w', encoding='utf-8') as f: f.write(content)
        p_ok(f"DataGame.java → LINK_IP_PORT")

    # Xoá BOM (UTF-8 with BOM) gây lỗi compiler
    def remove_bom(src_dir):
        count = 0
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

    # 5. Build
    p_info("Đang kiểm tra và sửa lỗi BOM (.java)...")
    c1 = remove_bom(paths["GAME_DIR"]); c2 = remove_bom(paths["LOGIN_DIR"])
    if c1+c2 > 0: p_ok(f"Đã xóa BOM (UTF-8) cho {c1+c2} file lỗi!")

    # 5.1 Fix Lombok (java.lang.NoSuchFieldError JCTree)
    for p_xml in [os.path.join(paths["GAME_DIR"], "pom.xml"), os.path.join(paths["LOGIN_DIR"], "pom.xml")]:
        if os.path.exists(p_xml):
            try:
                with open(p_xml, 'r', encoding='utf-8') as f: content = f.read()
                if "<artifactId>lombok</artifactId>" in content:
                    new_content = re.sub(r'(<artifactId>lombok</artifactId>\s*<version>)[^<]+(</version>)', r'\g<1>1.18.32\g<2>', content)
                    if new_content != content:
                        with open(p_xml, 'w', encoding='utf-8') as f: f.write(new_content)
                        p_ok(f"Đã vá lỗi JCTree (Nâng cấp Lombok) trong {os.path.basename(os.path.dirname(p_xml))}/pom.xml")
            except: pass

    # Fix Case-Sensitive trên Linux: Thư mục KhanhDTK -> khanhdtk
    kh_upper = os.path.join(paths["GAME_DIR"], "resources", "KhanhDTK")
    kh_lower = os.path.join(paths["GAME_DIR"], "resources", "khanhdtk")
    if os.path.exists(kh_upper) and not os.path.exists(kh_lower):
        os.rename(kh_upper, kh_lower)
        p_ok("Đã chuẩn hóa tên thư mục KhanhDTK -> khanhdtk (Fix lỗi NullPointerException)")

    p_info("Đang build Maven (1-3 phút)...")
    game_dir = paths["GAME_DIR"]
    target_dir = os.path.join(game_dir, "target")
    if os.path.exists(target_dir): os.system(f"rm -rf '{target_dir}'")
    res = subprocess.run(["mvn", "clean", "package", "-DskipTests"], cwd=game_dir)
    
    # Check login build as well
    login_dir = paths["LOGIN_DIR"]
    login_target = os.path.join(login_dir, "target")
    if os.path.exists(login_target): os.system(f"rm -rf '{login_target}'")
    subprocess.run(["mvn", "clean", "package", "-DskipTests"], cwd=login_dir)

    if res.returncode == 0:
        p_ok("BUILD THÀNH CÔNG!"); cfg["status"]["build"] = True
    else: p_err("BUILD THẤT BẠI!")
    save_config(cfg); input("\nEnter...")

# ==========================================
# [6] CẤU HÌNH RAM & SWAP (HYBRID)
# ==========================================
def config_ram(cfg):
    p_h("CẤU HÌNH RAM & SWAP")
    try:
        mem = subprocess.check_output(["cat", "/proc/meminfo"]).decode()
        total = int(re.search(r"MemTotal:\s+(\d+)", mem).group(1)) // 1024
        avail = int(re.search(r"MemAvailable:\s+(\d+)", mem).group(1)) // 1024
        swap_total = int(re.search(r"SwapTotal:\s+(\d+)", mem).group(1)) // 1024
        swap_free = int(re.search(r"SwapFree:\s+(\d+)", mem).group(1)) // 1024
        
        used = total - avail; pct = int(used * 20 / total)
        print(f"  RAM Thật: [{'█' * pct}{'░' * (20-pct)}] {used}MB / {total}MB")
        print(f"  RAM Ảo (Swap): {swap_total - swap_free}MB / {swap_total}MB")
        
        if swap_total > 0:
            suggest = max(total - 150, 512)
            p_info(f"Phát hiện Swap: Gợi ý chế độ Hybrid {suggest}MB (Chạy gần full RAM thật)")
        else:
            suggest = max(min(avail - 200, 1024), 256)
            p_info(f"Gợi ý an toàn: {suggest}MB")
    except: suggest = 512

    print(f"\n[1] Cấu hình RAM cho Server (Hiện: {cfg.get('jvm_xmx','512m')})")
    print(f"[2] Tạo/Cập nhật RAM ảo - Swap (Yêu cầu ROOT)")
    print(f"[0] Quay lại")
    
    ch = input(f"\n{C.BOLD}Chọn: {C.E}")
    
    if ch == "1":
        val = input(f"Nhập RAM (VD: 512m, 1g) [{suggest}m]: ").strip()
        if not val: val = f"{suggest}m"
        if not val.endswith(('m','g')): val += 'm'
        cfg['jvm_xmx'] = val
        save_config(cfg); p_ok(f"Đã thiết lập JVM RAM = {val}")
        
    elif ch == "2":
        if subprocess.run(["which", "su"], stdout=subprocess.DEVNULL).returncode != 0:
            p_err("Máy bạn chưa ROOT hoặc chưa cài 'su'!"); return
        
        size_gb = input("Nhập dung lượng Swap muốn tạo (GB) [2]: ").strip()
        if not size_gb: size_gb = "2"
        
        swap_file = os.path.join(HOME, "swapfile")
        p_info(f"Đang tạo {size_gb}GB Swap tại {swap_file}...")
        
        cmds = [
            f"su -c 'swapoff {swap_file}'",
            f"su -c 'dd if=/dev/zero of={swap_file} bs=1M count={int(size_gb)*1024}'",
            f"su -c 'chmod 600 {swap_file}'",
            f"su -c 'mkswap {swap_file}'",
            f"su -c 'swapon {swap_file}'"
        ]
        
        for cmd in cmds:
            p_info(f"Đang chạy: {cmd}")
            os.system(cmd)
            
        p_ok("Đã kích hoạt RAM ảo Hybrid thành công!")
    
    input("\nEnter...")

# ==========================================
# [A] TỰ ĐỘNG SAO LƯU XOAY VÒNG (BACKUP DAEMON) - mới từ nro4
# ==========================================
def is_backup_daemon_running():
    try:
        res = subprocess.run(["tmux", "has-session", "-t", "nro_backup_daemon"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except Exception:
        return False

def check_and_create_dir(path):
    try:
        os.makedirs(path, exist_ok=True)
        test_file = os.path.join(path, ".write_test")
        with open(test_file, "w") as f: f.write("test")
        os.remove(test_file)
        return True, ""
    except Exception as e:
        return False, str(e)

def start_backup_daemon_tmux():
    try:
        cfg = load_config()
        bcfg = cfg.get("backup_daemon", {})
        backup_dir = bcfg.get("backup_dir", os.path.join(HOME, "nro_backups"))
        os.makedirs(backup_dir, exist_ok=True)
        boot_log = os.path.join(backup_dir, "backup_daemon_boot.log")
        if os.path.exists(boot_log):
            try: os.remove(boot_log)
            except Exception: pass

        script_path = os.path.abspath(__file__) if '__file__' in globals() else os.path.abspath(sys.argv[0])
        script_dir = os.path.dirname(script_path)
        script_name = os.path.basename(script_path)

        os.system("tmux kill-session -t nro_backup_daemon 2>/dev/null")
        time.sleep(0.3)
        res = os.system("tmux new-session -d -s nro_backup_daemon")
        if res != 0: return False
        time.sleep(0.5)

        cmd = f"cd \"{script_dir}\" && {sys.executable} \"{script_name}\" --backup-daemon > \"{boot_log}\" 2>&1"
        os.system(f"tmux send-keys -t nro_backup_daemon '{cmd}' C-m")
        return True
    except Exception as e:
        p_err(f"Lỗi khi chạy lệnh tmux: {str(e)}")
        return False

def run_backup_daemon():
    cfg = load_config()
    bcfg = cfg.get("backup_daemon", {})
    interval_hours = int(bcfg.get("interval_hours", 1))
    max_backups = int(bcfg.get("max_backups", 24))
    backup_dir = bcfg.get("backup_dir", os.path.join(HOME, "nro_backups"))
    db_name = cfg.get('db_name', 'ngocrong')

    try:
        os.makedirs(backup_dir, exist_ok=True)
    except Exception:
        backup_dir = os.path.join(HOME, "nro_backups")
        os.makedirs(backup_dir, exist_ok=True)

    log_file = os.path.join(backup_dir, "backup_daemon.log")

    def log_msg(msg):
        t_str = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{t_str}] {msg}\n"
        print(line, end=""); sys.stdout.flush()
        try:
            with open(log_file, "a") as f: f.write(line)
        except Exception: pass

    log_msg("=== KHỞI ĐỘNG TIẾN TRÌNH SAO LƯU TỰ ĐỘNG ===")
    log_msg(f"Cấu hình: Chu kỳ = {interval_hours} giờ, Giới hạn tối đa = {max_backups} file.")
    log_msg(f"Thư mục lưu trữ: {backup_dir}")

    first_run = True
    while True:
        try:
            if not first_run:
                now = datetime.datetime.now()
                dt = now.replace(minute=0, second=0, microsecond=0)
                while True:
                    dt += datetime.timedelta(hours=1)
                    if dt > now and (dt.hour % interval_hours) == 0: break
                seconds_to_sleep = (dt - now).total_seconds()
                log_msg(f"Đang chờ đến mốc giờ sao lưu tiếp theo: {dt.strftime('%d-%m-%Y %H:%M:%S')} (Còn {seconds_to_sleep:.1f} giây)...")
                target_time = now + datetime.timedelta(seconds=seconds_to_sleep)
                while datetime.datetime.now() < target_time:
                    time.sleep(10)
            else:
                first_run = False
                log_msg("Thực hiện sao lưu bản đầu tiên ngay sau khi khởi chạy...")

            t_struct = time.localtime()
            timestamp_str = time.strftime("Ngay_%d-%m-%Y_Luc_%Hh%Mp", t_struct)
            out_file = os.path.join(backup_dir, f"backup_{db_name}_{timestamp_str}.sql")

            if cfg.get('backend') == 'ksweb':
                ksweb_pass = cfg.get('ksweb_mysql_pass', '')
                dump_cmd = f"mariadb-dump -h 127.0.0.1 -u root -p'{ksweb_pass}'" if ksweb_pass else "mariadb-dump -h 127.0.0.1 -u root"
            else:
                dump_cmd = "mariadb-dump -u root"

            res = os.system(f"{dump_cmd} {db_name} > \"{out_file}\"")
            if res == 0:
                log_msg(f"Sao lưu thành công: {os.path.basename(out_file)}")
                try:
                    all_files = []
                    for f_name in os.listdir(backup_dir):
                        if f_name.startswith(f"backup_{db_name}_") and f_name.endswith(".sql"):
                            full_p = os.path.join(backup_dir, f_name)
                            all_files.append((full_p, os.path.getmtime(full_p)))
                    all_files.sort(key=lambda x: x[1])
                    if len(all_files) > max_backups:
                        for f_p, _ in all_files[:len(all_files) - max_backups]:
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
        status_str = f"{C.G}ĐANG CHẠY{C.E}" if is_running else f"{C.R}ĐANG TẮT{C.E}"
        bcfg = cfg.get("backup_daemon", {"interval_hours": 1, "max_backups": 24,
                                          "backup_dir": os.path.join(HOME, "nro_backups")})
        interval = bcfg.get("interval_hours", 1)
        max_backups = bcfg.get("max_backups", 24)
        backup_dir = bcfg.get("backup_dir", os.path.join(HOME, "nro_backups"))

        print(f"  • Trạng thái Daemon  : {status_str}")
        print(f"  • Chu kỳ sao lưu     : {C.Y}{interval} giờ / lần{C.E}")
        print(f"  • Giới hạn lưu trữ   : {C.Y}Tối đa {max_backups} file gần nhất{C.E}")
        print(f"  • Thư mục lưu trữ    : {C.CY}{backup_dir}{C.E}")
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
                p_ok("Tiến trình đang hoạt động rồi!"); time.sleep(1.5); continue
            ok, err_msg = check_and_create_dir(backup_dir)
            if not ok:
                p_err(f"Không thể ghi vào thư mục: {backup_dir} ({err_msg})")
                input("\nEnter..."); continue
            if not shutil.which("tmux"):
                p_err("Chưa cài 'tmux'! Chạy: pkg install tmux -y")
                input("\nEnter..."); continue
            start_backup_daemon_tmux(); time.sleep(1.5)
            if is_backup_daemon_running(): p_ok("Đã kích hoạt Backup Daemon!")
            else: p_err("Khởi chạy thất bại! Xem mục [6] để biết chi tiết.")
            time.sleep(2)
        elif ch == "2":
            os.system("tmux kill-session -t nro_backup_daemon 2>/dev/null")
            p_ok("Đã dừng Backup Daemon!"); time.sleep(1.5)
        elif ch == "3":
            new_val = input(f"Chu kỳ sao lưu mới (số giờ) [{interval}]: ").strip()
            if new_val:
                try:
                    v = int(new_val)
                    if v <= 0: raise ValueError()
                    bcfg["interval_hours"] = v; cfg["backup_daemon"] = bcfg; save_config(cfg)
                    p_ok(f"Đã lưu chu kỳ mới: {v} giờ.")
                    if is_running: start_backup_daemon_tmux()
                except ValueError: p_err("Giá trị không hợp lệ!")
                time.sleep(1.5)
        elif ch == "4":
            new_val = input(f"Số bản lưu tối đa để xoay vòng [{max_backups}]: ").strip()
            if new_val:
                try:
                    v = int(new_val)
                    if v <= 0: raise ValueError()
                    bcfg["max_backups"] = v; cfg["backup_daemon"] = bcfg; save_config(cfg)
                    p_ok(f"Đã lưu giới hạn mới: {v} file.")
                    if is_running: start_backup_daemon_tmux()
                except ValueError: p_err("Giá trị không hợp lệ!")
                time.sleep(1.5)
        elif ch == "5":
            new_path = input("Nhập đường dẫn tuyệt đối mới cho thư mục backup: ").strip()
            if new_path:
                ok, err_msg = check_and_create_dir(new_path)
                if not ok:
                    p_err(f"Không thể ghi vào thư mục này! ({err_msg})")
                else:
                    bcfg["backup_dir"] = new_path; cfg["backup_daemon"] = bcfg; save_config(cfg)
                    p_ok(f"Đã cập nhật thư mục lưu trữ: {new_path}")
                    if is_running: start_backup_daemon_tmux()
                time.sleep(2)
        elif ch == "6":
            log_file = os.path.join(backup_dir, "backup_daemon.log")
            boot_log = os.path.join(backup_dir, "backup_daemon_boot.log")
            p_h("LOG TIẾN TRÌNH SAO LƯU")
            has_logs = False
            if os.path.exists(boot_log) and os.path.getsize(boot_log) > 0:
                print(f"{C.Y}--- LOG KHỞI ĐỘNG ---{C.E}"); os.system(f"cat \"{boot_log}\"")
                has_logs = True
            if os.path.exists(log_file) and os.path.getsize(log_file) > 0:
                print(f"{C.G}--- LOG VẬN HÀNH ---{C.E}"); os.system(f"tail -n 30 \"{log_file}\"")
                has_logs = True
            if not has_logs: p_err("Chưa có log nào được tạo.")
            input("\nEnter...")
        elif ch == "0": break

# ==========================================
# [B] GIÁM SÁT TIẾN TRÌNH TMUX - mới từ nro4
# ==========================================
def manage_tmux(cfg):
    while True:
        os.system("clear")
        p_h("GIÁM SÁT TIẾN TRÌNH TMUX")
        tmux_sessions = []
        try:
            res = subprocess.check_output(["tmux", "list-sessions"], stderr=subprocess.DEVNULL).decode("utf-8", errors="ignore")
            for line in res.strip().split("\n"):
                if line.strip(): tmux_sessions.append(line.split(":")[0].strip())
        except: pass

        print(f" {C.BOLD}Danh sách Session TMux đang hoạt động:{C.E}")
        if not tmux_sessions:
            print(f"  {C.R}Hiện không có Session TMux nào đang chạy.{C.E}")
        else:
            for i, name in enumerate(tmux_sessions, 1):
                print(f"  [{i}] {C.G}{name}{C.E} (tmux attach -t {name})")
        print("-" * 50)
        print("  [K] Tắt (Kill) một Session TMux bất kỳ")
        print("  [T] Tắt toàn bộ TMux server (Kill-server)")
        print("  [0] Quay lại Menu chính")
        print("-" * 50)
        print(f"  {C.Y}THOÁT TMUX: Ctrl+B rồi thả ra, sau đó bấm D (không làm sập tiến trình).{C.E}")

        ch = input(f"{C.BOLD}Lựa chọn của bạn: {C.E}").strip().upper()
        if ch == "0": break
        elif ch == "K":
            if not tmux_sessions:
                p_err("Không có Session nào để tắt."); time.sleep(1.5); continue
            idx = input("Nhập số thứ tự hoặc tên Session cần tắt: ").strip()
            if idx in tmux_sessions:
                os.system(f"tmux kill-session -t {idx}"); p_ok(f"Đã tắt: {idx}")
            else:
                try:
                    i = int(idx)
                    if 1 <= i <= len(tmux_sessions):
                        s_name = tmux_sessions[i-1]
                        os.system(f"tmux kill-session -t {s_name}"); p_ok(f"Đã tắt: {s_name}")
                    else: p_err("Số thứ tự không hợp lệ.")
                except ValueError: p_err("Không hợp lệ.")
            time.sleep(1.5)
        elif ch == "T":
            confirm = input(f"{C.Y}Xác nhận tắt toàn bộ TMux server? (y/N): {C.E}").strip().lower()
            if confirm == 'y':
                os.system("tmux kill-server"); p_ok("Đã tắt toàn bộ TMux Server!")
            time.sleep(1.5)
        else:
            try:
                i = int(ch)
                if 1 <= i <= len(tmux_sessions):
                    s_name = tmux_sessions[i-1]
                    p_info(f"Đang kết nối tới '{s_name}'..."); time.sleep(1)
                    os.system(f"tmux attach -t {s_name}")
                else: p_err("Lựa chọn không hợp lệ."); time.sleep(1)
            except ValueError: pass

# ==========================================
# [C] QUẢN LÝ TÀI KHOẢN - mới từ nro4
# ==========================================
def manage_accounts(cfg):
    p_h("QUẢN LÝ TÀI KHOẢN")
    db_name = cfg.get('db_name', 'ngocrong')
    db_cmd = get_db_cmd(cfg)
    while True:
        print(f"\n  Backend đang hoạt động: {C.H}{cfg.get('backend','termux').upper()}{C.E}")
        print("[1] Liệt kê danh sách tài khoản")
        print("[2] Tạo tài khoản nhanh")
        print("[3] Đổi mật khẩu tài khoản")
        print("[4] Xóa tài khoản")
        print("[0] Quay lại")
        ch = input(f"\n{C.BOLD}Chọn: {C.E}").strip()
        if ch == "1":
            os.system(f"{db_cmd} {db_name} -e 'SELECT id, username, active FROM account LIMIT 30;'")
        elif ch == "2":
            u = input("Username: ").strip(); p = input("Password: ").strip()
            if u and p:
                res = os.system(f"{db_cmd} {db_name} -e \"INSERT INTO account (username, password, active) VALUES ('{u}', '{p}', 1);\"")
                if res == 0: p_ok(f"Đã tạo tài khoản: {u}")
                else: p_err("Lỗi: Tài khoản có thể đã tồn tại hoặc sai tên bảng!")
        elif ch == "3":
            u = input("Username cần đổi: ").strip(); p = input("Mật khẩu mới: ").strip()
            if u and p:
                os.system(f"{db_cmd} {db_name} -e \"UPDATE account SET password='{p}' WHERE username='{u}';\"")
                p_ok("Cập nhật mật khẩu thành công!")
        elif ch == "4":
            u = input("Username cần xóa: ").strip()
            if u:
                os.system(f"{db_cmd} {db_name} -e \"DELETE FROM account WHERE username='{u}';\"")
                p_ok("Đã xóa tài khoản khỏi CSDL.")
        elif ch == "0": break
    input("\nEnter...")

# ==========================================
# [9/10] QUẢN LÝ SERVER
# ==========================================
def launch_server(cfg, stype):
    paths = get_paths(cfg)
    xmx = cfg.get('jvm_xmx', '512m')
    if stype == "login":
        path = paths["LOGIN_DIR"]; port = cfg['local_login_port']
        jar_cmd = f"java -Djava.awt.headless=true -jar target/*dependencies.jar"
        session = "nro_login"
    else:
        path = paths["GAME_DIR"]; port = cfg['local_game_port']
        jar_cmd = f"java -Djava.awt.headless=true -server -Xms{xmx} -Xmx{xmx} -jar target/*dependencies.jar"
        session = "nro_game"

    p_h(f"VẬN HÀNH {stype.upper()} (port {port})")
    print(f"[1] Chạy trực tiếp (thấy log)")
    print(f"[2] Chạy ngầm (tmux)")
    print(f"[0] TẮT server (kill port {port})")
    ch = input(f"\n{C.BOLD}Chọn: {C.E}")
    if ch == "1":
        kill_port(port); time.sleep(1)
        os.chdir(path)
        p_info(f"Đang chạy lệnh: {jar_cmd}")
        os.system(jar_cmd)
        input(f"\n{C.Y}Server đã dừng! Nhấn Enter để quay lại menu...{C.E}")
    elif ch == "2":
        kill_port(port); time.sleep(1)
        os.system(f"tmux kill-session -t {session} 2>/dev/null")
        script_path = os.path.join(HOME, f".nro_run_{session}.sh")
        script_content = (
            f"#!/data/data/com.termux/files/usr/bin/bash\n"
            f"cd \"{path}\"\n"
            f"{jar_cmd}\n"
            f"echo -e '\\n\\033[91m[SERVER STOPPED/CRASHED]\\033[0m'\n"
            f"read -p 'Press Enter...'\n"
        )
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)
        res = os.system(f"tmux new-session -d -s {session} \"bash '{script_path}'\"")
        time.sleep(1)
        alive = subprocess.run(["tmux", "has-session", "-t", session],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        if res == 0 and alive:
            p_ok(f"{stype} đang chạy ngầm trong tmux ({session})")
            p_info(f"Xem log: tmux attach -t {session}")
        else:
            p_err(f"Khởi chạy tmux thất bại! Kiểm tra: tmux attach -t {session} hoặc dùng menu [M].")
        input(f"\nNhấn Enter để tiếp tục...")
    elif ch == "0":
        kill_port(port)
        os.system(f"tmux kill-session -t {session} 2>/dev/null")
        p_ok(f"Đã tắt {stype} (port {port})")

def main():
    cfg = load_config()
    while True:
        lemp_st = check_lemp_status(cfg)
        ram_bar = get_ram_bar()
        backend = cfg.get('backend', 'termux')
        mode_str = cfg.get('mode', 'offline').upper()
        ip = cfg.get('tcp_domain', get_local_ip()) if mode_str == 'OFFLINE' else get_local_ip()

        if backend == 'ksweb':
            pma_display = f"http://{get_local_ip()}:8081 (KSWEB)"
            svc_label = f"Trạng thái KSWEB: {lemp_st}"
        else:
            pma_display = f"http://{get_local_ip()}:{cfg.get('pma_port', 8081)}"
            svc_label = f"Quản lý Dịch vụ LEMP: {lemp_st}"

        ksweb_hint = ""
        if backend == 'termux' and 'OFF' in lemp_st:
            ksweb_found, _ = detect_ksweb()
            if ksweb_found:
                ksweb_hint = f"\n  {C.Y}⚡ LEMP lỗi? Phát hiện KSWEB! Bấm [K] để chuyển đổi.{C.E}"

        l_st = get_server_status(cfg, "login")
        g_st = get_server_status(cfg, "game")

        os.system("clear")
        print(f"""{C.CY}{C.BOLD}
==========================================
        NRO2 danh rieng cho SRC2
    
=========================================={C.E}
 {C.G}Công cụ setup & vận hành server NRO tự động,
 giúp bạn dựng game riêng để chơi/mod game 
 đơn giản, nhanh gọn!{C.E}
------------------------------------------
 {C.BOLD}RAM: {ram_bar}
 {C.BOLD}IP:  {C.G}{ip}{C.E} | {C.BOLD}MODE:{C.E} {C.H}{mode_str}{C.E} | {C.BOLD}BACKEND:{C.E} {get_backend_label(cfg)}
 {C.BOLD}PHPMYADMIN:  {C.CY}{pma_display}{C.E}{ksweb_hint}
------------------------------------------
 [1] Cài đặt môi trường hệ thống{get_stat(cfg,'env')}
 [2] Giải nén Source game (Scan Download){get_stat(cfg,'source')}
 [3] Thiết lập Database & Web (Auto Fix){get_stat(cfg,'db_web')}
 [4] Cấu hình Kết nối (Online/Offline)
 [5] Vá IP & Build Game{get_stat(cfg,'build')}
 [6] Cấu hình RAM & Swap (Hybrid)
 [7] {svc_label}
 [8] VẬN HÀNH LOGIN SERVER: {l_st}
 [9] VẬN HÀNH GAME SERVER: {g_st}
 [A] QUẢN LÝ TÀI KHOẢN
 [T] TỰ ĐỘNG SAO LƯU XOAY VÒNG (BACKUP DAEMON): {f"{C.G}ON{C.E}" if is_backup_daemon_running() else f"{C.R}OFF{C.E}"}
 [M] GIÁM SÁT TIẾN TRÌNH TMUX (NGROK/SERVER)
 [K] CHUYỂN ĐỔI BACKEND (LEMP ↔ KSWEB)
 [L] LINK TẢI SRC & APK
 [D] LÀM MỚI KẾT NỐI NHANH
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
        elif ch == "8": launch_server(cfg, "login")
        elif ch == "9": launch_server(cfg, "game")
        elif ch == "A": manage_accounts(cfg)
        elif ch == "T": manage_auto_backup(cfg)
        elif ch == "M": manage_tmux(cfg)
        elif ch == "K": switch_backend(cfg)
        elif ch == "L":
            p_h("LINK TẢI SRC & APK")
            print(f"  {C.Y}SRC: {C.CY}https://drive.google.com/file/d/1wJzyRhii-rw25482R9gOS20ItqXEs9gQ/view?usp=sharing{C.E}")
            print(f"  {C.Y}APK: {C.CY}https://drive.google.com/file/d/1K1bwBRhiyNLfEMuOo2Yujs2CGe9yMIip/view?usp=sharing{C.E}")
            print(f"\n  {C.G}Bạn có thể copy link và dán vào trình duyệt để tải.{C.E}")
            input("\nEnter để quay lại...")
        elif ch == "D":
            kill_port(cfg['local_login_port'])
            kill_port(cfg['local_game_port'])
            time.sleep(2)
            if cfg.get("mode") != "online":
                cfg["tcp_domain"] = get_local_ip()
                cfg["tcp_port"] = cfg['local_game_port']
                save_config(cfg)
            apply_and_build(cfg)
        elif ch == "0": break
        time.sleep(0.3)

if __name__ == "__main__":
    if "--backup-daemon" in sys.argv:
        run_backup_daemon()
    else:
        main()
