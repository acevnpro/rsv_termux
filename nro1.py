import os, json, socket, subprocess, time, re, sys, shutil, datetime, urllib.request

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
        "base_dir": os.path.join(HOME, "nro_termux"),
        "db_user": "root", "db_pass": "", "db_name": "nrovip",
        "tcp_domain": get_local_ip(), "tcp_port": 14445,
        "local_login_port": 8888, "local_game_port": 14445,
        "mode": "offline", "pma_port": 8081, "jvm_xmx": "512m",
        "backend": "termux",
        "ksweb_mysql_pass": "",
        "ksweb_web_dir": "nso_web",
        "web_port": 8080,
        "backup_daemon": {
            "interval_hours": 1, "max_backups": 24,
            "backup_dir": os.path.join(HOME, "nro_backups")
        },
        "web_show_vnd": True,
        "web_show_admin": True,
        "web_admin_notice": "",
        "web_admin_pass": "admin",
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

def update_web_game_info(cfg):
    """Ghi IP:PORT hiện tại ra file game_info.txt để trang web hiển thị (không lỗi nếu web chưa tồn tại)"""
    try:
        info = f"{cfg.get('tcp_domain', get_local_ip())}:{cfg.get('tcp_port', 14445)}"
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
    b = cfg["base_dir"]
    return {
        "BASE": b,
        "LOGIN_DIR": os.path.join(b, "ServerLogin"),
        "GAME_DIR": os.path.join(b, "SrcVIP"),
        "LOGIN_INI": os.path.join(b, "ServerLogin/server.ini"),
        "GAME_PROPS": os.path.join(b, "SrcVIP/config/server.properties"),
        "DB_SERVICE": os.path.join(b, "SrcVIP/src/main/java/nro/jdbc/DBService.java"),
        "DATA_GAME": os.path.join(b, "SrcVIP/src/main/java/nro/data/DataGame.java"),
        "SQL_FILE": os.path.join(b, "NroVIP.sql"),
    }

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
    if str(port) == "8888":
        os.system("pkill -9 -f 'ServerLogin' 2>/dev/null")
    elif str(port) == "14445":
        os.system("pkill -9 -f 'VanTuan' 2>/dev/null")

def get_st(pattern):
    try:
        subprocess.check_output(["pgrep", "-f", pattern], stderr=subprocess.DEVNULL)
        return f"{C.G}ON{C.E}"
    except: return f"{C.R}OFF{C.E}"

def check_status():
    login = get_st("ServerLogin")
    game = f"{C.R}OFF{C.E}"
    for p in ["0337766460_VanTuan", "nro.server.ServerManager"]:
        if "ON" in get_st(p): game = f"{C.G}ON{C.E}"; break
    db = get_st("mariadbd")
    return login, game, db

def get_stat(cfg, key):
    return f" {C.G}(OK){C.E}" if cfg.get("status", {}).get(key) else ""

def get_server_status(cfg, stype):
    """Trạng thái chi tiết: ON (đang chạy) / AUTO-START (đang trong tmux, có thể đang tự khởi động lại) / OFF"""
    if stype == "login":
        running = "ON" in get_st("ServerLogin")
        session = "nro_login"
    else:
        running = False
        for p in ["0337766460_VanTuan", "nro.server.ServerManager"]:
            if "ON" in get_st(p): running = True; break
        session = "nro_game"
    if running: return f"{C.G}ON{C.E}"
    try:
        res = subprocess.run(["tmux", "has-session", "-t", session],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0: return f"{C.Y}AUTO-START{C.E}"
    except: pass
    return f"{C.R}OFF{C.E}"

# ==========================================
# KSWEB HYBRID - HÀM TIỆN ÍCH
# ==========================================
def detect_ksweb():
    """Kiểm tra xem KSWEB có đang chạy trên thiết bị không"""
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
    """Trả về lệnh SQL CLI phù hợp với backend đang dùng"""
    if cfg.get('backend') == 'ksweb':
        ksweb_pass = cfg.get('ksweb_mysql_pass', '')
        if ksweb_pass:
            return f"mariadb -h 127.0.0.1 -u root -p'{ksweb_pass}'"
        else:
            return "mariadb -h 127.0.0.1 -u root"
    else:
        return "mariadb -u root"

def get_backend_label(cfg):
    """Trả về nhãn và màu cho backend hiện tại"""
    backend = cfg.get('backend', 'termux')
    if backend == 'ksweb':
        return f"{C.G}KSWEB{C.E}"
    else:
        return f"{C.B}TERMUX{C.E}"

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
        pkgs = ["openjdk-17", "mariadb", "nginx", "php", "php-fpm", "maven",
                "wget", "unzip", "unrar", "tar", "git", "tmux", "psmisc", "lsof"]
    
    p_info("Đang cập nhật hệ thống (Tự động 100%)...")
    # Cấu hình để apt tự động trả lời 'y' và giữ cấu hình cũ nếu bị hỏi
    env = os.environ.copy()
    env["DEBIAN_FRONTEND"] = "noninteractive"
    subprocess.run(["pkg", "update", "-y"], env=env)
    subprocess.run(["apt", "upgrade", "-y", "-o", "Dpkg::Options::=--force-confdef",
                    "-o", "Dpkg::Options::=--force-confold"], env=env)

    for pkg in pkgs:
        p_info(f"Đang cài {pkg}...")
        subprocess.run(["pkg", "install", pkg, "-y"], env=env)

    p_ok("Cài đặt hoàn tất!")
    cfg["status"]["env"] = True; save_config(cfg)

# ==========================================
# [2] GIẢI NÉN SOURCE
# ==========================================
def extract_source(cfg):
    p_h("GIẢI NÉN SOURCE")
    # Các thư mục cần quét file nén
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
    
    target = os.path.join(HOME, "nro_termux")
    if os.path.exists(target):
        print(f"\n{C.Y}[!] Phát hiện thư mục {target} đã tồn tại.{C.E}")
        dl = input(f"Bạn có muốn XÓA SẠCH source cũ trước khi giải nén bản mới không? (Y/n): ").strip().upper()
        if dl != 'N':
            p_info("Đang xóa dữ liệu cũ, vui lòng chờ...")
            os.system(f"rm -rf '{target}'")
            
    os.makedirs(target, exist_ok=True)
    temp_extract = os.path.join(HOME, "temp_nro_extract")
    os.system(f"rm -rf '{temp_extract}'")
    os.makedirs(temp_extract, exist_ok=True)
    
    p_info(f"Đang giải nén: {sel_file}...")
    if sel_file.endswith(".zip"):
        subprocess.run(["unzip", "-q", "-o", full_path, "-d", temp_extract])
    elif sel_file.endswith(".rar"):
        subprocess.run(["unrar", "x", "-y", "-o+", full_path, temp_extract + "/"])
    elif sel_file.endswith(".tar.gz"):
        subprocess.run(["tar", "-xf", full_path, "-C", temp_extract])

    # Sắp xếp lại cấu trúc thư mục chuẩn (Tự động gom ServerLogin, SrcVIP, *.sql)
    p_info("Đang sắp xếp lại cấu trúc thư mục chuẩn...")
    found_login, found_game, found_web = False, False, False
    for root, dirs, files in os.walk(temp_extract):
        for d in list(dirs):
            d_lower = d.lower()
            if not found_login and d_lower == "serverlogin":
                os.system(f"mv '{os.path.join(root, d)}' '{target}/ServerLogin' 2>/dev/null")
                found_login = True
            elif not found_game and d_lower == "srcvip":
                os.system(f"mv '{os.path.join(root, d)}' '{target}/SrcVIP' 2>/dev/null")
                found_game = True
            elif not found_web and d_lower == "web_template":
                os.system(f"mv '{os.path.join(root, d)}' '{target}/web_template' 2>/dev/null")
                found_web = True
        for f in files:
            if f.endswith(".sql"):
                os.system(f"mv '{os.path.join(root, f)}' '{target}/' 2>/dev/null")
                
    # Giữ lại các file/thư mục thừa (có thể là tool mod hoặc tài liệu)
    extras_dir = os.path.join(target, "SanPhamMod_Thua")
    os.makedirs(extras_dir, exist_ok=True)
    os.system(f"mv '{temp_extract}'/* '{extras_dir}/' 2>/dev/null")
    os.system(f"mv '{temp_extract}'/.* '{extras_dir}/' 2>/dev/null")
    os.system(f"rm -rf '{temp_extract}'")
    
    # Xóa thư mục thừa nếu trống để tránh rác
    os.system(f"find '{extras_dir}' -empty -type d -delete 2>/dev/null")
    
    os.system(f"chmod -R 777 '{target}'")
    p_ok("Giải nén & Phân quyền thành công!")
    cfg["base_dir"] = target; cfg["status"]["source"] = True; save_config(cfg)
    input("\nNhấn Enter để tiếp tục...")

# [3] THIẾT LẬP DATABASE & WEB (LEMP / KSWEB)
# ==========================================
def setup_db(cfg):
    # Phân nhánh theo backend
    if cfg.get('backend') == 'ksweb':
        setup_db_ksweb(cfg)
        return
    p_h("THIẾT LẬP DATABASE & WEB (LEMP)")
    
    ksweb_found, ksweb_mysql = detect_ksweb()
    if ksweb_mysql:
        p_err("PHÁT HIỆN PORT 3306 ĐANG BỊ CHIẾM (CÓ THỂ DO KSWEB)!")
        p_info("Nếu bạn đang dùng KSWEB, hãy bấm [K] ngoài Menu chính để chuyển sang backend KSWEB,")
        p_info("hoặc tắt MySQL trên KSWEB nếu bạn muốn dùng LEMP Termux nội bộ.")
        c = input(f"\n{C.Y}Bạn có chắc chắn muốn tiếp tục cài LEMP không? (Y/N): {C.E}").upper()
        if c != 'Y': return
    
    # 1. Cài đặt các gói (Theo nro_cu.py)
    p_info("Đang đảm bảo các gói hệ thống...")
    os.system("pkg install nginx mariadb php php-fpm wget tar -y")

    # 2. Khởi tạo MariaDB (Theo nro_cu.py)
    p_info("Đang cấu hình MariaDB...")
    if not os.path.exists(os.path.join(os.environ['PREFIX'], "var/lib/mysql")):
        # Bản MariaDB mới đổi tên lệnh khởi tạo, dùng lệnh nào có sẵn
        install_cmd = "mariadb-install-db" if shutil.which("mariadb-install-db") else "mysql_install_db"
        p_info(f"Đang khởi tạo dữ liệu MariaDB ({install_cmd})...")
        os.system(f"{install_cmd} > /tmp/nro_mariadb_install.log 2>&1")

    # Khởi động MariaDB an toàn (kill tiến trình cũ lỡ bị treo trước đó)
    os.system("pkill -9 mariadbd 2>/dev/null")
    time.sleep(1)
    os.system("mariadbd-safe --log-error=/tmp/nro_mariadb_err.log > /dev/null 2>&1 &")

    # Dò tích cực tới khi DB thực sự sẵn sàng, thay vì chờ mù 10 giây
    p_info("Đang chờ MariaDB khởi động...")
    db_ready = False
    for _ in range(20):  # tối đa ~20 giây
        time.sleep(1)
        ret = os.system("mariadb -u root -e 'SELECT 1;' > /dev/null 2>&1")
        if ret == 0:
            db_ready = True
            break

    if not db_ready:
        p_err("MariaDB KHÔNG khởi động được sau 20 giây!")
        p_info("Xem log lỗi để biết nguyên nhân:")
        os.system("tail -n 20 /tmp/nro_mariadb_err.log 2>/dev/null")
        p_info(f"Mẹo: thử chạy tay 'mariadbd-safe' (không có &) trong Termux để xem lỗi trực tiếp,")
        p_info("hoặc nếu nghi dữ liệu cũ bị hỏng: menu [7] → [3] Xóa sạch môi trường rồi cài lại.")
        input("\nNhấn Enter để quay lại menu (bỏ qua các bước còn lại)...")
        return

    # Cấu hình quyền truy cập (Dùng tài khoản OS mặc định để cấp quyền cho root)
    whoami = os.popen("whoami").read().strip()
    sql_cmds = [
        "CREATE USER IF NOT EXISTS 'root'@'localhost' IDENTIFIED BY '';",
        "ALTER USER 'root'@'localhost' IDENTIFIED VIA mysql_native_password USING PASSWORD('');",
        "GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost' WITH GRANT OPTION;",
        "FLUSH PRIVILEGES;"
    ]
    all_ok = True
    for cmd in sql_cmds:
        # Thử chạy với root trước (nếu đã config), nếu lỗi thì chạy bằng whoami
        ret = os.system(f"mariadb -u root -e \"{cmd}\" 2>/dev/null")
        if ret != 0:
            ret = os.system(f"mariadb -u {whoami} -e \"{cmd}\" 2>/dev/null")
        if ret != 0:
            all_ok = False
    if all_ok:
        p_ok("Đã cấu hình MariaDB (User: root / No Pass)")
    else:
        p_err("Một vài lệnh cấu hình quyền MariaDB thất bại, có thể phải tự sửa qua menu [7] → [4].")


    # 3. Import SQL
    paths = get_paths(cfg)
    db_name = cfg.get('db_name', 'nro')
    
    scan_paths = [cfg.get("base_dir", ""), HOME, "/sdcard/Download"]
    sql_files = []
    for path in set(scan_paths):
        if path and os.path.exists(path):
            try:
                for f in os.listdir(path):
                    if f.endswith(".sql"): sql_files.append((f, path))
            except: continue
            
    # Add default if not in list
    default_sql = paths['SQL_FILE']
    if os.path.exists(default_sql) and not any(os.path.join(p, f) == default_sql for f, p in sql_files):
        sql_files.insert(0, (os.path.basename(default_sql), os.path.dirname(default_sql)))
        
    if sql_files:
        # Xác định file SQL mặc định nằm sẵn trong source (nro_termux/SrcVIP) vừa giải nén
        default_idx = None
        if os.path.exists(default_sql):
            for i, (f, p) in enumerate(sql_files):
                if os.path.join(p, f) == default_sql:
                    default_idx = i
                    break

        print(f"\n{C.H}[CHỌN FILE SQL ĐỂ IMPORT VÀO DATABASE '{db_name}']{C.E}")
        for i, (f, p) in enumerate(sql_files):
            loc = os.path.basename(p) if p != HOME else "Home"
            tag = f" {C.G}<- Mặc định (Enter){C.E}" if i == default_idx else ""
            print(f"[{i+1}] {f} ({loc}){tag}")
        print(f"[0] Bỏ qua import SQL (Dùng lại data cũ)")

        if default_idx is not None:
            prompt_txt = f"\n{C.BOLD}Chọn file SQL (Enter = dùng file mặc định [{default_idx+1}] {sql_files[default_idx][0]}): {C.E}"
        else:
            prompt_txt = f"\n{C.BOLD}Chọn file SQL: {C.E}"

        c = input(prompt_txt).strip()
        if not c and default_idx is not None:
            c = str(default_idx + 1)

        if c and c != "0" and c.isdigit() and int(c) <= len(sql_files):
            sel_f, sel_p = sql_files[int(c)-1]
            sql_path = os.path.join(sel_p, sel_f)
            p_info(f"Đang import database từ: {sel_f}...")
            c1 = os.system(f"mariadb -u root -e 'CREATE DATABASE IF NOT EXISTS {db_name};' 2>/dev/null")
            if c1 != 0:
                whoami = os.popen("whoami").read().strip()
                c1 = os.system(f"mariadb -u {whoami} -e 'CREATE DATABASE IF NOT EXISTS {db_name};'")
                c2 = os.system(f"mariadb -u {whoami} -f {db_name} < \"{sql_path}\"")
            else:
                c2 = os.system(f"mariadb -u root -f {db_name} < \"{sql_path}\"")
            if c1 == 0 and c2 == 0:
                p_ok(f"Import {db_name} thành công!")
            else:
                p_err(f"Import {db_name} thất bại! Vui lòng kiểm tra lại phía trên.")
                input(f"\n{C.CY}Nhấn Enter để bỏ qua và tiếp tục...{C.E}")
    else:
        p_err("Không tìm thấy file .sql nào trong thư mục game, Home hoặc Download.")
        input(f"\n{C.CY}Nhấn Enter để bỏ qua và tiếp tục...{C.E}")

    # 4. Thiết lập phpMyAdmin (Theo nro_cu.py)
    web_dir = os.path.join(HOME, "phpmyadmin")
    if not os.path.exists(os.path.join(web_dir, "index.php")):
        p_info("Đang tải và giải nén phpMyAdmin mới nhất...")
        pma_url = "https://www.phpmyadmin.net/downloads/phpMyAdmin-latest-all-languages.tar.gz"
        pma_tar = os.path.join(HOME, "pma.tar.gz")
        os.system(f"wget {pma_url} -O {pma_tar}")
        os.system(f"tar -xf {pma_tar} -C {HOME}")
        # Tìm thư mục vừa giải nén
        extracted = [d for d in os.listdir(HOME) if d.startswith("phpMyAdmin-") and os.path.isdir(os.path.join(HOME, d))]
        if extracted:
            os.system(f"rm -rf {web_dir}")
            os.system(f"mv {os.path.join(HOME, extracted[0])} {web_dir}")
        os.system(f"rm -f {pma_tar}")
    
    # Cấu hình config.inc.php (Kết nối qua 127.0.0.1 để ổn định)
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

    # 5. Cấu hình Nginx & PHP-FPM
    nginx_conf = os.path.join(os.environ['PREFIX'], "etc/nginx/nginx.conf")
    reg_web_dir = os.path.join(HOME, "web_register")
    
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

    # WEB ĐĂNG KÝ (PORT 8080)
    server {{
        listen       8080;
        server_name  localhost;
        root         {reg_web_dir};
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
        root         {web_dir};
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
    with open(nginx_conf, 'w') as f: f.write(nginx_template)
    
    # Tạo trang web đăng ký
    refresh_web_index(cfg)
    p_ok("Đã cấu hình Nginx: Port 8080 (Đăng ký) & Port 8081 (PMA)")
    
    # Đảm bảo php-fpm lắng nghe cổng 9000
    fpm_conf = os.path.join(os.environ['PREFIX'], "etc/php-fpm.d/www.conf")
    if os.path.exists(fpm_conf):
        with open(fpm_conf, 'r') as f: c = f.read()
        c = re.sub(r'^listen\s*=.*', 'listen = 127.0.0.1:9000', c, flags=re.M)
        with open(fpm_conf, 'w') as f: f.write(c)

    # Vá lỗi PHP 8.4 cho phpMyAdmin (Vị trí siêu an toàn)
    pma_idx = os.path.join(web_dir, "index.php")
    if os.path.exists(pma_idx):
        with open(pma_idx, 'r') as f: lines = f.readlines()
        
        # Kiểm tra xem file có dùng strict_types không
        has_declare = any("declare(strict_types=1)" in l for l in lines)
        new_lines = []
        inserted = False
        fix_code = "error_reporting(0); ini_set('display_errors', 0); // Fix PHP 8.4 by VanTuan\n"
        
        for line in lines:
            # Xóa các dòng fix cũ nếu có để tránh bị lặp
            if "Fix PHP 8.4 by VanTuan" in line:
                continue
                
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

    # 6. Khởi động lại toàn bộ
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
# KSWEB HYBRID - CÁC HÀM CHÍNH
# ==========================================
def deploy_web_to_ksweb(cfg):
    """Sao chép và cấu hình web đăng ký vào /sdcard/htdocs/ cho KSWEB (dùng chung hệ thống web_template mới)"""
    web_dir = refresh_web_index(cfg)
    p_ok(f"Đã triển khai Web đăng ký lên: {web_dir}")
    web_subdir = cfg.get('ksweb_web_dir', 'nso_web')
    p_info(f"Truy cập: http://{get_local_ip()}:8080/{web_subdir}/")

def setup_db_ksweb(cfg):
    """Thiết lập Database khi dùng KSWEB backend"""
    p_h("THIẾT LẬP DATABASE (KSWEB MODE)")
    ksweb_pass = cfg.get('ksweb_mysql_pass', '')
    db_cmd = get_db_cmd(cfg)
    
    # Kiểm tra kết nối MySQL KSWEB
    p_info("Kiểm tra kết nối MySQL của KSWEB...")
    ret = os.system(f"{db_cmd} -e 'SELECT 1;' 2>/dev/null")
    
    if ret != 0:
        p_err("Không kết nối được MySQL KSWEB!")
        p_info("Hãy kiểm tra: 1) KSWEB đã bật MySQL, 2) Mật khẩu có chính xác không?")
        pass_display = ksweb_pass if ksweb_pass else "(Trống)"
        print(f"\n{C.Y}[GỢI Ý] Mật khẩu KSWEB đang lưu: {pass_display}{C.E}")
        new_pass = input(f"Nhập mật khẩu KSWEB chính xác (Bấm Enter nếu mật khẩu trống): ").strip()
        
        cfg['ksweb_mysql_pass'] = new_pass
        save_config(cfg)
        p_info("Thử lại với mật khẩu mới...")
        db_cmd = get_db_cmd(cfg)
        ret = os.system(f"{db_cmd} -e 'SELECT 1;' 2>/dev/null")
        if ret != 0:
            p_err("Vẫn không kết nối được! Hãy mở app KSWEB để kiểm tra lại pass.")
            input("\nEnter..."); return
        else:
            input("\nEnter..."); return
    
    p_ok("Kết nối MySQL KSWEB thành công!")
    
    # Import SQL (tương tự logic cũ nhưng dùng db_cmd có password)
    paths = get_paths(cfg)
    db_name = cfg.get('db_name', 'nrovip')
    
    scan_paths = [cfg.get("base_dir", ""), HOME, "/sdcard/Download"]
    sql_files = []
    for path in set(scan_paths):
        if path and os.path.exists(path):
            try:
                for f in os.listdir(path):
                    if f.endswith(".sql"): sql_files.append((f, path))
            except: continue
    
    default_sql = paths['SQL_FILE']
    if os.path.exists(default_sql) and not any(os.path.join(p, f) == default_sql for f, p in sql_files):
        sql_files.insert(0, (os.path.basename(default_sql), os.path.dirname(default_sql)))
    
    if sql_files:
        default_idx = None
        if os.path.exists(default_sql):
            for i, (f, p) in enumerate(sql_files):
                if os.path.join(p, f) == default_sql:
                    default_idx = i
                    break

        print(f"\n{C.H}[CHỌN FILE SQL ĐỂ IMPORT VÀO DATABASE '{db_name}' (KSWEB)]{C.E}")
        for i, (f, p) in enumerate(sql_files):
            loc = os.path.basename(p) if p != HOME else "Home"
            tag = f" {C.G}<- Mặc định (Enter){C.E}" if i == default_idx else ""
            print(f"[{i+1}] {f} ({loc}){tag}")
        print(f"[0] Bỏ qua import SQL (Dùng lại data cũ)")

        if default_idx is not None:
            prompt_txt = f"\n{C.BOLD}Chọn file SQL (Enter = dùng file mặc định [{default_idx+1}] {sql_files[default_idx][0]}): {C.E}"
        else:
            prompt_txt = f"\n{C.BOLD}Chọn file SQL: {C.E}"

        c = input(prompt_txt).strip()
        if not c and default_idx is not None:
            c = str(default_idx + 1)

        if c and c != "0" and c.isdigit() and int(c) <= len(sql_files):
            sel_f, sel_p = sql_files[int(c)-1]
            sql_path = os.path.join(sel_p, sel_f)
            p_info(f"Đang import database từ: {sel_f}...")
            c1 = os.system(f"{db_cmd} -e 'CREATE DATABASE IF NOT EXISTS {db_name};'")
            c2 = os.system(f"{db_cmd} -f {db_name} < \"{sql_path}\"")
            if c1 == 0 and c2 == 0:
                p_ok(f"Import {db_name} thành công (KSWEB)!")
            else:
                p_err(f"Import {db_name} thất bại! Vui lòng kiểm tra lại.")
                input(f"\n{C.CY}Nhấn Enter để bỏ qua và tiếp tục...{C.E}")
    else:
        p_err("Không tìm thấy file .sql nào.")
        input(f"\n{C.CY}Nhấn Enter để bỏ qua và tiếp tục...{C.E}")
    
    # Deploy web đăng ký lên KSWEB
    deploy_web_to_ksweb(cfg)
    
    cfg["status"]["db_web"] = True
    save_config(cfg)
    p_ok("Thiết lập KSWEB hoàn tất!")
    p_info(f"phpMyAdmin KSWEB: http://{get_local_ip()}:8001")
    p_info(f"User: root | Pass: {ksweb_pass}")
    input("\nEnter...")

def switch_backend(cfg):
    """Menu chuyển đổi giữa LEMP Termux và KSWEB"""
    p_h("CHUYỂN ĐỔI BACKEND (LEMP ↔ KSWEB)")
    current = cfg.get('backend', 'termux')
    ksweb_found, ksweb_mysql = detect_ksweb()
    
    ksweb_found_str = f"{C.G}✓ Có{C.E}" if ksweb_found else f"{C.R}✗ Không{C.E}"
    ksweb_mysql_str = f"{C.G}✓ Online{C.E}" if ksweb_mysql else f"{C.R}✗ Offline{C.E}"
    
    print(f"  Backend hiện tại : {C.H}{current.upper()}{C.E}")
    print(f"  KSWEB phát hiện : {ksweb_found_str}")
    print(f"  KSWEB MySQL      : {ksweb_mysql_str}")
    ksweb_pass = cfg.get('ksweb_mysql_pass', '')
    pass_display = ksweb_pass if ksweb_pass else "(Trống)"
    print(f"  Mật khẩu KSWEB   : {C.Y}{pass_display}{C.E}")
    print()
    print(f"  [1] Dùng LEMP Termux (MariaDB + Nginx nội bộ)")
    print(f"  [2] Dùng KSWEB (MySQL + Lighttpd bên ngoài)")
    print(f"  [3] Triển khai Web đăng ký lên KSWEB (/sdcard/htdocs/)")
    print(f"  [4] Đổi mật khẩu MySQL KSWEB")
    print(f"  [0] Quay lại")
    
    ch = input(f"\n{C.BOLD}Chọn: {C.E}")
    
    if ch == "1":
        cfg['backend'] = 'termux'
        cfg['db_pass'] = ''  # LEMP Termux mặc định không mật khẩu
        save_config(cfg)
        p_ok("Đã chuyển sang LEMP Termux!")
        p_info("Hãy chạy Mục [3] để thiết lập lại Database & Web.")
        p_info("Sau đó chạy Mục [5] để vá lại IP và Build.")
        
    elif ch == "2":
        if not ksweb_found:
            p_err("Không phát hiện KSWEB! Hãy cài ứng dụng KSWEB và bật MySQL.")
            p_info("Tải KSWEB từ Google Play Store và bật MySQL + Lighttpd.")
            input("\nEnter..."); return
        if not ksweb_mysql:
            p_err("KSWEB đã cài nhưng MySQL chưa bật!")
            p_info("Mở ứng dụng KSWEB → Tab STATUS → Gạt công tắc MySQL sang BẬT.")
            input("\nEnter..."); return
        
        cfg['backend'] = 'ksweb'
        cfg['db_pass'] = cfg.get('ksweb_mysql_pass', '')
        save_config(cfg)
        p_ok("Đã chuyển sang KSWEB!")
        p_info("LƯU Ý: Hãy đảm bảo KSWEB đã bật MySQL (3306) và Lighttpd (8080)")
        p_info("Chạy Mục [3] trong menu chính để thiết lập DB và deploy Web lên KSWEB.")
        p_info("Sau đó chạy Mục [5] để vá lại IP và Build.")
        
    elif ch == "3":
        deploy_web_to_ksweb(cfg)
        
    elif ch == "4":
        new_pass = input(f"Nhập mật khẩu MySQL KSWEB mới (Bấm Enter để đặt mật khẩu trống): ").strip()
        cfg['ksweb_mysql_pass'] = new_pass
        if cfg.get('backend') == 'ksweb':
            cfg['db_pass'] = new_pass
        save_config(cfg)
        p_display = new_pass if new_pass else "(Trống)"
        p_ok(f"Đã lưu mật khẩu KSWEB: {p_display}")
    
    input("\nEnter...")

# ==========================================
# [4] CẤU HÌNH KẾT NỐI (Online/Offline)
# ==========================================
def manage_tcp(cfg):
    p_h("CẤU HÌNH KẾT NỐI & NGROK")
    mode_str = cfg.get('mode', 'offline').upper()
    print(f"Chế độ hiện tại: {C.H}{mode_str}{C.E}")
    print(f"Địa chỉ hiện tại: {C.Y}{cfg['tcp_domain']}:{cfg['tcp_port']}{C.E}")
    
    print(f"\n[1] Cài đặt Ngrok (Tối ưu cho Termux ARM64)")
    print(f"[2] Khởi chạy & Quản lý Ngrok")
    print(f"[3] Online: Tự động lấy từ Ngrok API (127.0.0.1:4040)")
    print(f"[4] Online: Tìm TCP theo Link (Playit/Bore/Ngrok)")
    print(f"[5] Online: Nhập IP/Port thủ công")
    print(f"[6] Offline: Chạy mạng LAN/WiFi (Dùng IP máy)")
    print(f"[7] Online: Mở cổng Web (Ngrok HTTP - Giới hạn 1 tunnel)")
    print(f"[8] Online: Mở cổng Web (Cloudflare - FREE & KHÔNG GIỚI HẠN)")
    print(f"[0] Quay lại")
    ch = input(f"\n{C.BOLD}Chọn: {C.E}")

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
        input("\nEnter...")

    elif ch == "2":
        print("\n[1] Chạy trực tiếp (Xem Log - Bấm Ctrl+C để thoát)")
        print("[2] Chạy ngầm (Tmux - Không lo tắt nhầm)")
        print("[0] Tắt Ngrok đang chạy")
        sc = input(f"\n{C.BOLD}Chọn: {C.E}")
        if sc == "1":
            p_info(f"Đang mở Ngrok cho Port {cfg['local_game_port']}...")
            p_info("LƯU Ý: 'Web Interface http://127.0.0.1:4040' chỉ là trang quản lý của Ngrok, KHÔNG PHẢI lỗi sai port!")
            subprocess.run(["termux-chroot", "ngrok", "tcp", str(cfg['local_game_port'])])
        elif sc == "2":
            os.system("pkill -9 ngrok")
            os.system("tmux kill-session -t nro_ngrok 2>/dev/null")
            p_info(f"Đang mở Ngrok ngầm cho Port {cfg['local_game_port']}...")
            os.system(f"tmux new-session -d -s nro_ngrok 'termux-chroot ngrok tcp {cfg['local_game_port']}'")
            p_ok("Ngrok đang chạy ngầm trong Tmux (Session: nro_ngrok)!")
            p_info("Mẹo: Mở mục [3] để tự động lấy IP và Port nhé.")
            p_info("LƯU Ý: Port 4040 chỉ là trang Web quản lý của Ngrok, Ngrok vẫn đang trỏ đúng vào game!")
            input("\nEnter...")
        elif sc == "0":
            os.system("pkill -9 ngrok")
            os.system("tmux kill-session -t nro_ngrok 2>/dev/null")
            p_ok("Đã tắt Ngrok!")
            input("\nEnter...")

    elif ch == "3":
        try:
            with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels") as r:
                tunnels = json.loads(r.read().decode()).get('tunnels', [])
                if not tunnels: p_err("Không thấy tunnel! Hãy chắc chắn Ngrok đang chạy."); input("\nEnter..."); return
                for i, t in enumerate(tunnels):
                    print(f"[{i+1}] {t.get('name')}: {C.Y}{t.get('public_url')}{C.E}")
                sel = input("\nChọn: ")
                if not sel: return
                url = tunnels[int(sel)-1].get('public_url', '').replace('tcp://', '')
                if ':' in url:
                    d, p = url.rsplit(':', 1)
                    resolved_ip = resolve_ip(d)
                    print(f"IP Số phân giải được: {C.G}{resolved_ip}{C.E}")
                    cfg['mode'] = 'online'
                    cfg['tcp_domain'] = resolved_ip; cfg['tcp_port'] = int(p)
                    save_config(cfg); p_ok(f"Đã lưu ONLINE: {resolved_ip}:{p}")
                    p_info("Lưu ý: Hãy chạy mục [5] để áp dụng IP mới.")
        except Exception as e: p_err(f"Lỗi Ngrok API: {e}"); p_info("Mẹo: Bạn đã chạy Ngrok ở mục [2] chưa?")
        input("\nEnter...")

    elif ch == "4":
        p_info("VD: bore.pub:6489 | 0.tcp.ap.ngrok.io:12345 | abc.at.playit.gg:30000")
        link = input("Nhập địa chỉ: ").strip().replace("tcp://", "")
        if ':' in link:
            d, p = link.rsplit(':', 1)
            resolved_ip = resolve_ip(d)
            print(f"IP Số phân giải được: {C.G}{resolved_ip}{C.E}")
            cfg['mode'] = 'online'
            cfg['tcp_domain'] = resolved_ip; cfg['tcp_port'] = int(p)
            save_config(cfg); p_ok(f"Đã lưu ONLINE: {resolved_ip}:{p}")
            p_info("Lưu ý: Hãy chạy mục [5] để áp dụng IP mới.")
        else: p_err("Sai format! Cần Domain:Port")
        input("\nEnter...")

    elif ch == "5":
        ip = input("Nhập IP số (VD: 54.179.53.232): ").strip()
        port = input("Nhập Port (VD: 13953): ").strip()
        if ip and port.isdigit():
            cfg['mode'] = 'online'
            cfg['tcp_domain'] = ip; cfg['tcp_port'] = int(port)
            save_config(cfg); p_ok(f"Đã lưu ONLINE: {ip}:{port}")
            p_info("Lưu ý: Hãy chạy mục [5] để áp dụng IP mới.")
        else: p_err("Dữ liệu không hợp lệ!")
        input("\nEnter...")

    elif ch == "6":
        auto_ip = get_local_ip()
        print(f"\n{C.H}[CHẾ ĐỘ OFFLINE / MẠNG LAN / WIFI HOTSPOT]{C.E}")
        print(f"[1] IP Localhost: {C.G}127.0.0.1{C.E} (Chơi một mình trên máy)")
        print(f"[2] IP WiFi/LAN : {C.G}{auto_ip}{C.E} (Phát WiFi cho máy khác vào chung)")
        
        sel = input(f"\n{C.BOLD}Chọn loại IP: {C.E}").strip()
        final_ip = auto_ip
        if sel == "1": final_ip = "127.0.0.1"
        elif sel == "2": final_ip = auto_ip
        elif sel != "": return
        
        cfg["mode"] = "offline"
        cfg["tcp_domain"] = final_ip
        cfg["tcp_port"] = cfg['local_game_port']
        save_config(cfg)
        p_ok(f"Đã chuyển sang chế độ OFFLINE (IP: {final_ip})")
        p_info("Lưu ý: Hãy chạy mục [5] để áp dụng IP mới.")
        input("\nEnter...")

    elif ch == "7":
        p_info("Đang khởi động Ngrok HTTP cho Web (Port 8080)...")
        os.system("tmux kill-session -t nro_web 2>/dev/null")
        os.system("tmux new-session -d -s nro_web 'ngrok http 8080'")
        time.sleep(3)
        try:
            with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels") as r:
                data = json.loads(r.read().decode())
                web_url = ""
                for t in data.get('tunnels', []):
                    if t.get('proto') in ['http', 'https']:
                        web_url = t.get('public_url')
                        if web_url.startswith('https'): break # Ưu tiên https
                if web_url:
                    if cfg.get('backend') == 'ksweb':
                        web_subdir = cfg.get('ksweb_web_dir', 'nso_web')
                        web_url = web_url.rstrip('/') + f'/{web_subdir}/'
                    cfg['web_url'] = web_url
                    save_config(cfg)
                    p_ok(f"TRANG ĐĂNG KÝ ONLINE: {C.G}{web_url}{C.E}")
                    p_info("Hãy gửi link này cho người chơi để họ đăng ký tài khoản.")
                else: p_err("Không tìm thấy tunnel HTTP! Hãy kiểm tra lại Ngrok.")
        except: p_err("Lỗi kết nối Ngrok API! (Port 4040 không phản hồi)")
        input("\nEnter...")

    elif ch == "8":
        p_info("Đang kiểm tra Cloudflare Tunnel...")
        if os.system("command -v cloudflared > /dev/null") != 0:
            p_info("Đang cài đặt cloudflared (Dung lượng khoảng 30MB)...")
            os.system("pkg install cloudflared -y")
        
        p_info("Đang khởi động Cloudflare Tunnel cho Web (Port 8080)...")
        os.system("tmux kill-session -t nro_cf 2>/dev/null")
        log_file = os.path.join(HOME, "cf_tunnel.log")
        os.system(f"rm -f {log_file}")
        
        # Chạy tunnel và ghi log ra file để lấy link
        os.system(f"tmux new-session -d -s nro_cf 'cloudflared tunnel --url http://127.0.0.1:8080 2>&1 | tee {log_file}'")
        
        p_info("Đang chờ Cloudflare cấp link (khoảng 8-10 giây)...")
        time.sleep(10)
        
        try:
            with open(log_file, "r") as f:
                log_data = f.read()
                # Tìm link dạng https://...trycloudflare.com
                match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', log_data)
                if match:
                    web_url = match.group(0)
                    # KSWEB: Tự động nối thêm path /nso_web/ để tránh lỗi 403
                    if cfg.get('backend') == 'ksweb':
                        web_subdir = cfg.get('ksweb_web_dir', 'nso_web')
                        web_url = web_url.rstrip('/') + f'/{web_subdir}/'
                    cfg['web_url'] = web_url
                    save_config(cfg)
                    p_ok(f"TRANG ĐĂNG KÝ ONLINE (CLOUDFLARE): {C.G}{web_url}{C.E}")
                    p_info("------------------------------------------")
                    p_info("Ưu điểm: Miễn phí, ổn định, không giới hạn 1 tunnel.")
                    p_info("Hãy gửi link trên cho người chơi để đăng ký tài khoản.")
                    p_info("------------------------------------------")
                else:
                    p_err("Không tìm thấy link Cloudflare trong log!")
                    print(f"{C.Y}Gợi ý: Hãy thử chạy lại Mục [8] hoặc kiểm tra kết nối mạng.{C.E}")
        except Exception as e:
            p_err(f"Lỗi đọc log Cloudflare: {e}")
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
    backend = cfg.get('backend', 'termux') if cfg else 'termux'
    if backend == 'ksweb':
        # Kiểm tra KSWEB MySQL qua socket
        mysql_ok = False
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect(("127.0.0.1", 3306))
            s.close()
            mysql_ok = True
        except: pass
        if mysql_ok: return f"{C.G}KSWEB OK{C.E}"
        return f"{C.R}KSWEB OFF{C.E}"
    else:
        nginx = subprocess.run(["pgrep", "nginx"], stdout=subprocess.DEVNULL).returncode == 0
        mysql = subprocess.run(["pgrep", "mariadbd"], stdout=subprocess.DEVNULL).returncode == 0
        php = subprocess.run(["pgrep", "php-fpm"], stdout=subprocess.DEVNULL).returncode == 0
        if nginx and mysql and php: return f"{C.G}OK{C.E}"
        if not nginx and not mysql and not php: return f"{C.R}OFF{C.E}"
        return f"{C.Y}PARTIAL{C.E}"

def manage_lemp(cfg):
    backend = cfg.get('backend', 'termux')
    if backend == 'ksweb':
        p_h("TRẠNG THÁI KSWEB")
        ksweb_found, ksweb_mysql = detect_ksweb()
        ksweb_found_str = f"{C.G}✓ Có{C.E}" if ksweb_found else f"{C.R}✗ Không{C.E}"
        ksweb_mysql_str = f"{C.G}✓ Online{C.E}" if ksweb_mysql else f"{C.R}✗ Offline{C.E}"
        print(f"  KSWEB phát hiện : {ksweb_found_str}")
        print(f"  KSWEB MySQL      : {ksweb_mysql_str}")
        print(f"\n{C.CY}[HƯỚNG DẪN CÀI ĐẶT PHPMYADMIN TRÊN KSWEB]{C.E}")
        print(f"1. Mở ứng dụng KSWEB trên điện thoại.")
        print(f"2. Kéo sang tab {C.BOLD}TOOLS{C.E}.")
        print(f"3. Chọn {C.BOLD}phpMyAdmin{C.E}, tick chọn {C.BOLD}Lighttpd{C.E} và nhấn cài đặt.")
        print(f"4. Đợi cài xong, bạn có thể truy cập PMA ở port 8001 (hoặc 8000).")
        print(f"\n{C.Y}[i] Bật/tắt MySQL & Web cũng thực hiện trực tiếp trên app KSWEB.{C.E}")
        input("\nEnter...")
        return
    
    p_h("QUẢN LÝ DỊCH VỤ LEMP")
    print(f"Trạng thái hiện tại: LEMP: {check_lemp_status(cfg)}")
    print("-" * 30)
    print("[1] Bật dịch vụ (Start)")
    print("[2] Tắt dịch vụ (Stop)")
    print("[3] Xóa sạch môi trường (Wipe/Reset)")
    print(f"[4] {C.Y}Sửa lỗi 'Access denied for user root' (Game/Web không kết nối được DB){C.E}")
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
    elif c == "4":
        p_info("Đang ép user 'root'@'localhost' dùng mysql_native_password (cho phép đăng nhập qua TCP)...")
        fix_sql = "ALTER USER 'root'@'localhost' IDENTIFIED VIA mysql_native_password USING PASSWORD(''); FLUSH PRIVILEGES;"
        ret = os.system(f'mariadb -u root -e "{fix_sql}" 2>/dev/null')
        if ret != 0:
            whoami = os.popen("whoami").read().strip()
            ret = os.system(f'mariadb -u {whoami} -e "{fix_sql}" 2>/dev/null')
        if ret == 0:
            p_ok("Đã sửa xong! Thử lại Game Server [9] hoặc Web đăng ký ngay bây giờ.")
        else:
            p_err("Không sửa được tự động. Hãy chạy tay: mariadb -u root  (rồi dán lệnh SQL ở trên)")
    time.sleep(1.5 if c == "4" else 1)

# ==========================================
# [6] VÁ IP & BUILD
# ==========================================
def apply_and_build(cfg):
    p_h("VÁ MÃ NGUỒN & BUILD")
    paths = get_paths(cfg)
    if cfg.get('mode') == 'online':
        ip = resolve_ip(cfg['tcp_domain']); port = cfg['tcp_port']
    else:
        ip = cfg.get('tcp_domain', get_local_ip())
        if not ip: ip = get_local_ip()
        port = cfg['local_game_port']
    l_port = cfg['local_login_port']; g_port = cfg['local_game_port']
    db_u = cfg['db_user']
    # Dùng đúng password theo backend
    if cfg.get('backend') == 'ksweb':
        db_p = cfg.get('ksweb_mysql_pass', '123456')
    else:
        db_p = cfg['db_pass']
    db_name = cfg['db_name']
    sv1 = f"Buffalo:{ip}:{port}"

    p_info(f"Mode: {cfg.get('mode','offline').upper()} | Backend: {cfg.get('backend','termux').upper()}")
    p_info(f"Online: {ip}:{port} | Local: Login={l_port}, Game={g_port}")

    # 1. server.ini
    if os.path.exists(paths["LOGIN_INI"]):
        with open(paths["LOGIN_INI"], 'w') as f:
            f.write(f"# Config\nserver.port={l_port}\ndb.port=3306\ndb.host=127.0.0.1\n")
            f.write(f"db.user={db_u}\ndb.password={db_p}\ndb.name={db_name}\n")
            f.write("db.driver=com.mysql.cj.jdbc.Driver\nadmin.mode=0\n")
        p_ok(f"server.ini → port={l_port}")

    # 2. server.properties (GHI ĐẦY ĐỦ)
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

##config server
server.sv=1
server.port={g_port}
server.sv1={sv1}

login.host=127.0.0.1
login.port={l_port}

server.waitlogin=5
server.maxperip=50
server.maxplayer=1500
server.expserver=4
server.debug=false
server.name=buffalo
server.domain=https://nro-buffalo.com/

api.port=8080
api.key=abcdef

#hikariCP
server.hikari.minIdle=5
server.hikari.poolSize=200
server.hikari.cachePre=true
server.hikari.cacheSize=250
server.hikari.cacheSqlLimit=2048

execute.command=java -Djava.awt.headless=true -jar target/0337766460_VanTuan-1.0-RELEASE-jar-with-dependencies.jar

server.event=6
##config server 1 = halloween, 2 = 20/11 nha giao , 3 noel, 4 tet, 5 sk8/3
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
        content = re.sub(r'LINK_IP_PORT\s*=\s*".*?"', f'LINK_IP_PORT = "Buffalo:{ip}:{port}:0"', content)
        with open(paths["DATA_GAME"], 'w', encoding='utf-8') as f: f.write(content)
        p_ok(f"DataGame.java → LINK_IP_PORT")

    game_dir = paths["GAME_DIR"]
    # Tự động vá lỗi GUI cho Termux (Headless Mode)
    sm_path = os.path.join(game_dir, "src/main/java/nro/server/ServerManager.java")
    if os.path.exists(sm_path):
        p_info("Đang tự động vá lỗi GUI cho Termux...")
        os.system(f"sed -i '/JFrame/s/^/\/\//' '{sm_path}'")
        os.system(f"sed -i '/frame\./s/^/\/\//' '{sm_path}'")
        os.system(f"sed -i '/JPanel/s/^/\/\//' '{sm_path}'")
        os.system(f"sed -i '/new panel/s/^/\/\//' '{sm_path}'")
        p_ok("Vá lỗi GUI hoàn tất!")

    # Xoá BOM (UTF-8 with BOM) gây lỗi compiler Maven
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

    p_info("Đang kiểm tra và sửa lỗi BOM (.java)...")
    c1 = remove_bom(paths["GAME_DIR"]); c2 = remove_bom(paths["LOGIN_DIR"])
    if c1 + c2 > 0: p_ok(f"Đã xóa BOM (UTF-8) cho {c1+c2} file lỗi!")

    # Fix Lombok (java.lang.NoSuchFieldError JCTree) - nâng version lombok trong pom.xml nếu có
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

    # 5. Build (Game + Login)
    p_info("Đang build Maven Game Server (1-3 phút)...")
    target_dir = os.path.join(game_dir, "target")
    if os.path.exists(target_dir): os.system(f"rm -rf '{target_dir}'")
    res = subprocess.run(["mvn", "clean", "package", "-DskipTests"], cwd=game_dir)

    login_dir = paths["LOGIN_DIR"]
    login_target = os.path.join(login_dir, "target")
    if os.path.exists(login_dir):
        p_info("Đang build Maven Login Server...")
        if os.path.exists(login_target): os.system(f"rm -rf '{login_target}'")
        subprocess.run(["mvn", "clean", "package", "-DskipTests"], cwd=login_dir)

    if res.returncode == 0:
        p_ok("BUILD THÀNH CÔNG!"); cfg["status"]["build"] = True
    else: p_err("BUILD THẤT BẠI!")
    save_config(cfg); input("\nEnter...")

# ==========================================
# [WEB] TRIỂN KHAI WEB ĐĂNG KÝ (Đọc từ web_template/ trong SRC, có fallback)
# ==========================================
_FALLBACK_INDEX_PHP = r"""<?php
error_reporting(E_ALL & ~E_NOTICE & ~E_DEPRECATED & ~E_WARNING);
ini_set('display_errors', 0);
require_once 'db_config.php';
mysqli_report(MYSQLI_REPORT_OFF);
$conn = @new mysqli("127.0.0.1", "root", $ksweb_pass, $db_name);
$msg = ""; $status = "";
if (!$conn->connect_error && $_SERVER["REQUEST_METHOD"] == "POST") {
    $user = preg_replace("/[^a-zA-Z0-9]/", "", $_POST['user']);
    $pass = $_POST['pass'];
    $email = isset($_POST['email']) ? preg_replace("/[^a-zA-Z0-9@.]/", "", $_POST['email']) : "";
    $isAdmin = isset($_POST['is_admin']) ? 1 : 0;
    $vnd = isset($_POST['vnd']) ? (int)$_POST['vnd'] : 0;
    if (strlen($user) < 4 || strlen($pass) < 1) {
        $msg = "Tên tài khoản tối thiểu 4 ký tự!"; $status = "error";
    } else {
        $check = $conn->query("SELECT id FROM account WHERE username = '$user'");
        if ($check->num_rows > 0) {
            $msg = "Tài khoản này đã tồn tại!"; $status = "error";
        } else {
            $sql = "INSERT INTO account (username, password, email, is_admin, vnd, active) VALUES ('$user', '$pass', '$email', $isAdmin, $vnd, 1)";
            if ($conn->query($sql)) {
                $msg = "Đăng ký thành công! Đã cấp quyền Admin và " . number_format($vnd) . " VND."; $status = "success";
            } else { $msg = "Lỗi Database: " . $conn->error; $status = "error"; }
        }
    }
}
?>
<!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NRO - Đăng Ký Test Game</title>
<style>
body{background:#0f172a;min-height:100vh;display:flex;align-items:center;justify-content:center;margin:0;color:#fff;font-family:sans-serif;padding:20px}
.card{background:rgba(255,255,255,.05);padding:2rem;border-radius:1.5rem;border:1px solid rgba(255,255,255,.1);width:100%;max-width:450px}
h1{text-align:center;color:#00d2ff} label{display:block;margin:.6rem 0 .3rem;font-size:.85rem;color:#94a3b8}
input{width:100%;padding:.7rem;border-radius:.6rem;border:1px solid rgba(255,255,255,.1);background:rgba(0,0,0,.2);color:#fff;box-sizing:border-box}
button{width:100%;padding:.9rem;border:none;border-radius:.75rem;background:#00d2ff;color:#0f172a;font-weight:bold;cursor:pointer;margin-top:1rem}
.alert{padding:.8rem;border-radius:.6rem;margin-top:1rem;text-align:center;font-size:.85rem}
.success{background:rgba(34,197,94,.2);color:#4ade80} .error{background:rgba(239,68,68,.2);color:#f87171}
</style></head><body><div class="card"><h1>NRO TEST TOOLS</h1>
<p style="font-size:.8rem;color:#94a3b8;text-align:center">(Thiếu web_template/ - đang dùng giao diện dự phòng tối giản)</p>
<?php if ($msg): ?><div class="alert <?php echo $status; ?>"><?php echo $msg; ?></div><?php endif; ?>
<form method="POST">
<label>Tên tài khoản</label><input type="text" name="user" required autofocus>
<label>Mật khẩu</label><input type="password" name="pass" required>
<label>Email (tuỳ chọn)</label><input type="email" name="email">
<label>Số VND muốn tặng (test)</label><input type="number" name="vnd" value="1000000">
<label><input type="checkbox" name="is_admin" style="width:auto;display:inline-block"> Cấp quyền Admin</label>
<button type="submit">ĐĂNG KÝ VÀ NHẬN QUÀ</button>
</form></div></body></html>
"""

def get_web_template_dir(cfg):
    """Tìm thư mục web_template: ưu tiên trong SRC vừa giải nén, sau đó cạnh file .py, cuối cùng quét sâu toàn bộ base_dir"""
    candidates = [
        os.path.join(cfg.get("base_dir", ""), "web_template"),
        os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "web_template"),
    ]
    for c in candidates:
        if c and os.path.isdir(c) and os.path.exists(os.path.join(c, "index.php")):
            return c
    # Fallback: quét sâu toàn bộ base_dir (phòng trường hợp web_template bị gom vào SanPhamMod_Thua)
    base_dir = cfg.get("base_dir", "")
    if base_dir and os.path.exists(base_dir):
        try:
            for root, dirs, files in os.walk(base_dir):
                if os.path.basename(root).lower() == "web_template" and "index.php" in files:
                    return root
        except: pass
    return None

def refresh_web_index(cfg):
    """Đồng bộ web đăng ký: luôn cập nhật db_config.php/web_config.json, chỉ ghi index/admin nếu chưa có (để không mất chỉnh sửa tay)"""
    backend = cfg.get('backend', 'termux')
    db_name = cfg.get('db_name', 'nrovip')
    ksweb_pass = cfg.get('ksweb_mysql_pass', '') if backend == 'ksweb' else ''
    footer_text = "KSWEB Hybrid" if backend == 'ksweb' else "LEMP Termux"

    if backend == 'ksweb':
        web_subdir = cfg.get('ksweb_web_dir', 'nso_web')
        web_dir = f"/sdcard/htdocs/{web_subdir}"
    else:
        web_dir = os.path.join(HOME, "web_register")
    os.makedirs(web_dir, exist_ok=True)

    # 1. db_config.php - luôn ghi đè để đồng bộ với cấu hình hiện tại
    db_cfg_content = f"""<?php
$db_name = '{db_name}';
$ksweb_pass = '{ksweb_pass}';
$footer_text = '{footer_text}';
?>"""
    with open(os.path.join(web_dir, "db_config.php"), "w", encoding="utf-8") as f:
        f.write(db_cfg_content)

    # 2. web_config.json - luôn ghi đè để đồng bộ
    web_cfg_content = json.dumps({
        "web_show_vnd": cfg.get('web_show_vnd', True),
        "web_show_admin": cfg.get('web_show_admin', True),
        "web_admin_notice": cfg.get('web_admin_notice', ''),
        "web_admin_pass": cfg.get('web_admin_pass', 'admin')
    }, indent=4)
    with open(os.path.join(web_dir, "web_config.json"), "w", encoding="utf-8") as f:
        f.write(web_cfg_content)

    # 3. index.php + admin.php - lấy từ web_template/ trong SRC nếu có, không thì dùng fallback
    tpl_dir = get_web_template_dir(cfg)
    index_file = os.path.join(web_dir, "index.php")
    admin_file = os.path.join(web_dir, "admin.php")

    should_write_index = not os.path.exists(index_file)
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            if "web_config.json" not in content:
                should_write_index = True  # bản cũ (nro1 gốc) chưa có tính năng mới -> nâng cấp

    if should_write_index:
        if tpl_dir:
            shutil.copyfile(os.path.join(tpl_dir, "index.php"), index_file)
            p_ok(f"Đã lấy giao diện đăng ký từ: {tpl_dir}/index.php")
        else:
            with open(index_file, "w", encoding="utf-8") as f: f.write(_FALLBACK_INDEX_PHP)
            p_info("Không thấy thư mục 'web_template' trong SRC -> dùng giao diện dự phòng tối giản.")
            p_info("Mẹo: thêm thư mục 'web_template' (chứa index.php, admin.php) vào file ZIP nguồn để có giao diện đầy đủ (VND, Admin, Thông báo...).")

    if tpl_dir and (not os.path.exists(admin_file) or os.path.getsize(admin_file) < 100):
        shutil.copyfile(os.path.join(tpl_dir, "admin.php"), admin_file)

    return web_dir

def manage_web_ui(cfg):
    while True:
        os.system("clear")
        p_h("QUẢN LÝ TÀI KHOẢN ADMIN WEB")
        curr_pass = cfg.get('web_admin_pass', 'admin')
        ip_port = get_local_ip()
        port = "8080" if cfg.get('backend', 'termux') == 'ksweb' else cfg.get('web_port', 8080)

        print(f"  > Đường dẫn Web Admin: {C.CY}http://{ip_port}:{port}/admin.php{C.E}")
        print(f"  > Mật khẩu truy cập hiện tại: {C.G}{curr_pass}{C.E}\n")
        print("  [1] Đổi Mật Khẩu Truy Cập Web Admin")
        print("  [2] Đồng bộ lại Web (nếu vừa đổi web_template trong SRC)")
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
        elif ch == "2":
            refresh_web_index(cfg)
            p_ok("Đã đồng bộ lại Web!")
            time.sleep(1.5)
        elif ch == "0":
            break

# ==========================================
# [ACC] QUẢN LÝ TÀI KHOẢN (TERMINAL)
# ==========================================
def manage_accounts(cfg):
    p_h("QUẢN LÝ TÀI KHOẢN")
    db_name = cfg.get('db_name', 'nro')
    db_cmd = get_db_cmd(cfg)
    
    while True:
        backend = cfg.get('backend', 'termux').upper()
        print(f"\n  Backend: {C.H}{backend}{C.E}")
        print(f"[1] Liệt kê tài khoản")
        print(f"[2] Tạo tài khoản nhanh")
        print(f"[3] Đổi mật khẩu")
        print(f"[4] Xóa tài khoản")
        print(f"[0] Quay lại")
        ch = input(f"\n{C.BOLD}Chọn: {C.E}")
        
        if ch == "1":
            os.system(f"{db_cmd} {db_name} -e 'SELECT id, username, active, is_admin FROM account LIMIT 20;'")
        elif ch == "2":
            u = input("Username: ").strip()
            p = input("Password: ").strip()
            if u and p:
                res = os.system(f"{db_cmd} {db_name} -e \"INSERT INTO account (username, password, active) VALUES ('{u}', '{p}', 1);\"")
                if res == 0: p_ok(f"Đã tạo tài khoản: {u}")
                else: p_err("Lỗi tạo tài khoản (Có thể đã tồn tại)")
        elif ch == "3":
            u = input("Username cần đổi pass: ").strip()
            p = input("Mật khẩu mới: ").strip()
            if u and p:
                os.system(f"{db_cmd} {db_name} -e \"UPDATE account SET password='{p}' WHERE username='{u}';\"")
                p_ok("Đã cập nhật mật khẩu.")
        elif ch == "4":
            u = input("Username cần xóa: ").strip()
            if u:
                os.system(f"{db_cmd} {db_name} -e \"DELETE FROM account WHERE username='{u}';\"")
                p_ok("Đã xóa tài khoản.")
        elif ch == "0": break
    input("\nEnter...")

# ==========================================
# [T] TỰ ĐỘNG SAO LƯU XOAY VÒNG (BACKUP DAEMON)
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
    db_name = cfg.get('db_name', 'nrovip')

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
# [M] GIÁM SÁT TIẾN TRÌNH TMUX
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

SRC_DOWNLOAD_LINK = "https://drive.google.com/file/d/17wqWUp3avOhv6xkgbX03joR3zLH6A7i1/view?usp=sharing"
APK_DOWNLOAD_LINK = "https://drive.google.com/file/d/1lRH7I86uUlqf3MBtfv8aWwo88Y-ucQrP/view?usp=sharing"

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
        
        # Các lệnh Root để tạo Swap
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
# [9/10] QUẢN LÝ SERVER
# ==========================================
def launch_server(cfg, stype):
    paths = get_paths(cfg)
    xmx = cfg.get('jvm_xmx', '512m')
    if stype == "login":
        path = paths["LOGIN_DIR"]; port = cfg['local_login_port']
        jar_cmd = f"java -Djava.awt.headless=true -jar ServerLogin.jar"
        session = "nro_login"
    else:
        path = paths["GAME_DIR"]; port = cfg['local_game_port']
        target_dir = os.path.join(path, "target")
        jar_file = ""
        if os.path.exists(target_dir):
            all_jars = [f for f in os.listdir(target_dir) if f.endswith(".jar")]
            # Ưu tiên tìm file có chữ 'dependencies'
            dep_jars = [f for f in all_jars if "dependencies" in f]
            if dep_jars:
                jar_file = os.path.join("target", dep_jars[0])
            elif all_jars:
                # Nếu không thấy bản dependencies, lấy bản jar đầu tiên (thường sẽ lỗi ClassNotFound nhưng vẫn thử)
                jar_file = os.path.join("target", all_jars[0])
        
        if not jar_file:
            p_err("Không tìm thấy file JAR trong thư mục target!")
            p_info("Mẹo: Bạn đã chạy Mục [5] (Vá IP & Build Game) thành công chưa?")
            input("\nNhấn Enter để quay lại...")
            return

        p_info(f"Đang chạy file: {jar_file}")
        jar_cmd = f"java -Djava.awt.headless=true -server -Xms{xmx} -Xmx{xmx} -jar {jar_file}"
        session = "nro_game"

    p_h(f"VẬN HÀNH {stype.upper()} (port {port})")
    print(f"[1] Chạy trực tiếp (thấy log)")
    print(f"[2] Chạy ngầm (tmux)")
    print(f"[0] TẮT server (kill port {port})")
    ch = input(f"\n{C.BOLD}Chọn: {C.E}")
    if ch == "1":
        kill_port(port); time.sleep(1)
        os.chdir(path); os.system(jar_cmd)
        input(f"\n{C.CY}Server đã dừng hoặc gặp lỗi. Nhấn Enter để quay lại menu...{C.E}")
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

def get_stat(cfg, key):
    return f" {C.G}(OK){C.E}" if cfg.get("status", {}).get(key) else ""

def main():
    cfg = load_config()
    while True:
        os.system("clear")
        lemp_st = check_lemp_status(cfg)
        ram_bar = get_ram_bar()
        mode = cfg.get('mode', 'offline').upper()
        backend = cfg.get('backend', 'termux')
        backend_label = get_backend_label(cfg)
        if mode == 'OFFLINE':
            ip = cfg.get('tcp_domain', get_local_ip())
        else:
            ip = get_local_ip()
        
        # Xây dựng link Web đăng ký
        if backend == 'ksweb':
            web_subdir = cfg.get('ksweb_web_dir', 'nso_web')
            default_web = f"http://{get_local_ip()}:8080/{web_subdir}/"
        else:
            default_web = f"http://{get_local_ip()}:8080"
        web_display = cfg.get('web_url', default_web)
        
        # Label cho menu [7]
        if backend == 'ksweb':
            svc_label = f"Trạng thái KSWEB: {lemp_st}"
        else:
            svc_label = f"Quản lý Dịch vụ LEMP: {lemp_st}"
        
        # Gợi ý KSWEB khi LEMP lỗi
        ksweb_hint = ""
        if backend == 'termux' and 'OFF' in lemp_st:
            ksweb_found, _ = detect_ksweb()
            if ksweb_found:
                ksweb_hint = f"\n  {C.Y}⚡ LEMP lỗi? Phát hiện KSWEB! Bấm [K] để chuyển đổi.{C.E}"
        
        # Xây dựng link PMA
        if backend == 'ksweb':
            pma_display = f"http://{get_local_ip()}:8001 (KSWEB)"
        else:
            pma_display = f"http://{get_local_ip()}:8081"

        l_st = get_server_status(cfg, "login")
        g_st = get_server_status(cfg, "game")
        backup_st = f"{C.G}ON{C.E}" if is_backup_daemon_running() else f"{C.R}OFF{C.E}"

        print(f"""{C.CY}{C.BOLD}
==========================================
       NRO VNPro_1 danh rieng cho SRC_1
=========================================={C.E}
 {C.G} Link tải SRC tôi để ở mục L 
 tôi tạo ra app này để mod những game này thành game pvp 
 moba ..vv hoặc các chế độ khác tương tự 
 ae ai có chung ý tưởng hoặc dự án nhớ share cho mọi 
 người để chúng ta cùng vui vẻ nhé!{C.E}
------------------------------------------
 {C.BOLD}RAM: {ram_bar}
 {C.BOLD}IP:  {C.G}{ip}{C.E} | {C.BOLD}MODE:{C.E} {C.H}{mode}{C.E} | {C.BOLD}BACKEND:{C.E} {backend_label}
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
 [8] VẬN HÀNH LOGIN SERVER: {l_st}
 [9] VẬN HÀNH GAME SERVER: {g_st}
 [A] QUẢN LÝ TÀI KHOẢN
 {C.G}[K] CHUYỂN ĐỔI BACKEND (LEMP ↔ KSWEB){C.E}
 [W] QUẢN LÝ WEB ĐĂNG KÝ (Admin, Mật khẩu, Đồng bộ)
 [D] LÀM MỚI KẾT NỐI NHANH
 [T] TỰ ĐỘNG SAO LƯU XOAY VÒNG (BACKUP DAEMON): {backup_st}
 [M] GIÁM SÁT TIẾN TRÌNH TMUX (NGROK/SERVER)
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
        elif ch == "8": launch_server(cfg, "login")
        elif ch == "9": launch_server(cfg, "game")
        elif ch == "A": manage_accounts(cfg)
        elif ch == "K": switch_backend(cfg)
        elif ch == "W": manage_web_ui(cfg)
        elif ch == "D":
            kill_port(cfg['local_login_port'])
            kill_port(cfg['local_game_port'])
            time.sleep(2)
            if cfg.get("mode") != "online":
                cfg["tcp_domain"] = get_local_ip()
                cfg["tcp_port"] = cfg['local_game_port']
                save_config(cfg)
            apply_and_build(cfg)
        elif ch == "T": manage_auto_backup(cfg)
        elif ch == "M": manage_tmux(cfg)
        elif ch == "L": show_download_links(cfg)
        elif ch == "0": break
        time.sleep(0.3)

if __name__ == "__main__":
    if "--backup-daemon" in sys.argv:
        run_backup_daemon()
    else:
        main()
