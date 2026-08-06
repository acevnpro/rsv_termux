import os, sys, json, socket, subprocess, time, re, shutil
import datetime

# Define color class
class C:
    H = '\033[95m'; B = '\033[94m'; CY = '\033[96m'; G = '\033[92m'
    Y = '\033[93m'; R = '\033[91m'; E = '\033[0m'; BOLD = '\033[1m'

def p_h(t): print(f"\n{C.CY}{C.BOLD}=== {t} ==={C.E}")
def p_ok(t): print(f"{C.G}[✓] {t}{C.E}")
def p_err(t): print(f"{C.R}[✗] {t}{C.E}")
def p_info(t): print(f"{C.CY}[i] {t}{C.E}")
def wait(): input(f"\n{C.Y}>>> Bấm Enter để quay lại Menu...{C.E}")

HOME = os.path.expanduser("~")
CONFIG_FILE = os.path.join(HOME, "avt_config.json")

def load_config():
    defaults = {
        "game_dir": os.path.join(HOME, "avatar"),
        "db_port": 3309,
        "db_name": "avt_teamobi",
        "db_user": "debian",
        "db_pass": "password",
        "server_port": 19128,
        "jvm_xmx": "1536m",
        "status": {
            "source": False,
            "packages": False,
            "db_setup": False
        }
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                cfg = json.load(f)
                for k, v in defaults.items():
                    if k not in cfg:
                        cfg[k] = v
                    elif isinstance(v, dict):
                        if k not in cfg or not isinstance(cfg[k], dict):
                            cfg[k] = {}
                        for sk, sv in v.items():
                            if sk not in cfg[k]:
                                cfg[k][sk] = sv
                return cfg
        except:
            pass
    return dict(defaults)

def save_config(cfg):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=4)

def get_stat(cfg, key):
    status = cfg.get("status", {})
    return f" {C.G}[✓]{C.E}" if status.get(key) else ""

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def get_ram_bar():
    try:
        res = subprocess.check_output("free -m", shell=True).decode().split('\n')[1].split()
        total, used = int(res[1]), int(res[2])
        pct = int(used * 100 / total)
        bar_len = 20
        filled = int(pct * bar_len / 100)
        bar = "█" * filled + "░" * (bar_len - filled)
        return f"{C.Y}[{bar}] {pct}% ({used}MB/{total}MB){C.E}"
    except:
        return "[N/A]"

def port_open(port, host="127.0.0.1", timeout=2):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

# Import avatarctl.py dynamically based on game_dir if it exists
def get_avatarctl(cfg):
    game_dir = cfg.get("game_dir", "")
    if game_dir and os.path.exists(os.path.join(game_dir, "avatarctl.py")):
        if game_dir not in sys.path:
            sys.path.insert(0, game_dir)
        import avatarctl
        import importlib
        importlib.reload(avatarctl) # reload in case of changes
        return avatarctl
    return None

def install_env(cfg):
    p_h("CÀI ĐẶT MÔI TRƯỜNG HỆ THỐNG")
    print("Quá trình này sẽ cài đặt các gói cần thiết (Java 17, MariaDB, Python, unrar...).")
    cf = input("Bấm Enter để bắt đầu... (hoặc gõ '0' để hủy): ")
    if cf == '0': return

    p_info("Đang kiểm tra & cài đặt packages...")
    os.system("pkg update -y > /dev/null 2>&1")
    res = os.system("pkg install -y openjdk-17 mariadb unrar unzip python3 php")
    os.system("pip install pymysql > /dev/null 2>&1")
    
    if res == 0:
        cfg["status"]["packages"] = True
        save_config(cfg)
        p_ok("Cài đặt môi trường hoàn tất.")
    else:
        p_err("Có lỗi trong quá trình cài đặt package.")
    wait()

def extract_source(cfg):
    p_h("GIẢI NÉN SOURCE GAME")
    scan_paths = [HOME, "/sdcard/Download"]
    all_files = []
    for path in scan_paths:
        if os.path.exists(path):
            try:
                files = [(f, path) for f in os.listdir(path) if f.endswith(".tar.gz") or f.endswith(".zip") or f.endswith(".rar")]
                all_files.extend(files)
            except:
                continue

    if not all_files:
        p_err("Không tìm thấy file nén .tar.gz, .zip, .rar nào trong ~/ hoặc /sdcard/Download")
        wait()
        return
    
    for i, (f, p) in enumerate(all_files):
        loc = "Download" if "Download" in p else "Home"
        print(f"[{i+1}] {f} ({loc})")
        
    c = input("\nChọn file để giải nén (0=hủy): ")
    if not c or c == "0" or not c.isdigit() or int(c) > len(all_files): return
    
    sel_file, sel_path = all_files[int(c)-1]
    full_path = os.path.join(sel_path, sel_file)
    
    target = os.path.join(HOME, "avatar")
    cfg_target = input(f"Nhập thư mục đích (Mặc định: {target}): ").strip()
    if cfg_target: target = cfg_target
    
    if os.path.exists(target):
        print(f"\n{C.Y}[!] Thư mục {target} đã tồn tại.{C.E}")
        dl = input(f"Bạn có muốn XÓA SẠCH thư mục cũ trước khi giải nén không? (y/N): ").strip().lower()
        if dl == 'y':
            p_info("Đang xóa dữ liệu cũ...")
            os.system(f"rm -rf '{target}'")
            
    os.makedirs(target, exist_ok=True)
    
    p_info(f"Đang tiến hành giải nén: {sel_file} vào {target}...")
    if sel_file.endswith(".tar.gz"):
        subprocess.run(["tar", "-xf", full_path, "-C", target])
    elif sel_file.endswith(".zip"):
        subprocess.run(["unzip", "-q", "-o", full_path, "-d", target])
    elif sel_file.endswith(".rar"):
        subprocess.run(["unrar", "x", "-y", "-o+", full_path, target + "/"])
        
    p_ok("Giải nén thành công!")
    cfg["game_dir"] = target
    cfg["status"]["source"] = True
    save_config(cfg)
    wait()

def setup_db(cfg):
    p_h("THIẾT LẬP DATABASE")
    game_dir = cfg.get("game_dir", "")
    if not cfg["status"].get("source") or not os.path.exists(game_dir):
        p_err("Bạn chưa giải nén Source! Hãy chạy mục [2] trước.")
        wait()
        return

    print("Hệ thống sẽ tự động:")
    print("1. Vá mã hóa file SQL")
    print("2. Khởi tạo & Cấu hình MariaDB")
    print("3. Tạo Database, User và Import dữ liệu\n")
    cf = input("Bấm Enter để bắt đầu... (hoặc gõ '0' để hủy): ")
    if cf == '0': return

    # A. Patch SQL
    p_info("Chuẩn bị SQL & Database...")
    sql_file = os.path.join(game_dir, "avt_teamobi.sql")
    sql_patched = os.path.join(game_dir, "avt_teamobi_mariadb.sql")
    if os.path.exists(sql_file):
        with open(sql_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        content = re.sub(r'utf8mb4_0900_ai_ci', 'utf8mb4_general_ci', content)
        with open(sql_patched, "w", encoding="utf-8") as f:
            f.write(content)
        p_ok("Đã vá file SQL cho MariaDB.")
    else:
        p_err(f"Không tìm thấy file {sql_file}")

    # B. Init MariaDB
    prefix = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
    data_dir = os.path.join(prefix, "var/lib/mysql")
    if not os.path.exists(os.path.join(data_dir, "mysql")):
        p_info("Đang khởi tạo database...")
        os.system(f"mariadb-install-db --datadir={data_dir} --auth-root-authentication-method=normal > /dev/null 2>&1")

    # C. Config my.cnf
    mycnf = os.path.join(prefix, "etc/my.cnf")
    db_port = cfg["db_port"]
    need_config = True
    if os.path.exists(mycnf):
        with open(mycnf, "r") as f:
            if str(db_port) in f.read():
                need_config = False
    
    if need_config:
        with open(mycnf, "a") as f:
            f.write(f"\n[mysqld]\nport={db_port}\nbind-address=127.0.0.1\n")
        p_ok(f"Đã cấu hình my.cnf chạy port {db_port}")

    # D. Bật DB
    if not port_open(db_port):
        p_info(f"Đang bật MariaDB ở port {db_port}...")
        log_db = os.path.join(HOME, "db.log")
        subprocess.Popen(f"mariadbd --datadir={data_dir} > {log_db} 2>&1", shell=True)
        t = 0
        while not port_open(db_port) and t < 15:
            time.sleep(1)
            t += 1
        if port_open(db_port):
            p_ok(f"Database đã hoạt động trên port {db_port}.")
        else:
            p_err(f"Không thể khởi động Database. Vui lòng kiểm tra log: {log_db}")
            wait()
            return
    else:
        p_ok(f"Database đã chạy ở port {db_port}")

    # E & F: Tạo DB, User, Import
    p_info("Tạo Database, User và Import SQL...")
    db_name = cfg["db_name"]
    db_user = cfg["db_user"]
    db_pass = cfg["db_pass"]
    os.system(f"mariadb -u root -e \"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4;\"")
    os.system(f"mariadb -u root -e \"CREATE USER IF NOT EXISTS '{db_user}'@'localhost' IDENTIFIED BY '{db_pass}'; GRANT ALL PRIVILEGES ON {db_name}.* TO '{db_user}'@'localhost'; FLUSH PRIVILEGES;\"")
    
    check_table = subprocess.run(f"mariadb -u root -N -e \"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='{db_name}';\"", shell=True, capture_output=True, text=True)
    if check_table.stdout.strip() == "0":
        if os.path.exists(sql_patched):
            p_info("Đang import dữ liệu SQL...")
            os.system(f"mariadb -u root {db_name} < {sql_patched}")
            p_ok("Import dữ liệu SQL thành công.")
    else:
        p_info("Database đã có dữ liệu, bỏ qua import.")

    cfg["status"]["db_setup"] = True
    save_config(cfg)
    p_ok("THIẾT LẬP DATABASE HOÀN TẤT!")
    wait()

def manage_server(cfg):
    actl = get_avatarctl(cfg)
    game_dir = cfg.get("game_dir", "")
    if not actl:
        p_err("Chưa có source! Vui lòng làm mục [2] trước.")
        wait()
        return

    while True:
        os.system("clear")
        p_h("VẬN HÀNH SERVER")
        st = "MỞ" if port_open(cfg["server_port"]) else "ĐÓNG"
        print(f" Port Game: {cfg['server_port']} ({st})\n")
        print(" [1] Trạng thái chi tiết (Status)")
        print(" [2] Chạy Server (Ngầm)")
        print(" [3] Chạy Server (Trực tiếp - Xem log)")
        print(" [4] Tắt Server")
        print(" [5] Khởi động lại (Restart)")
        print(" [0] Quay lại")
        
        ch = input(f"\n{C.BOLD}Chọn: {C.E}").strip()
        old_cwd = os.getcwd()
        os.chdir(game_dir)
        try:
            if ch == "1":
                actl.cmd_status()
                wait()
            elif ch == "2":
                actl.cmd_start()
                wait()
            elif ch == "3":
                os.system(f"java -Xmx{cfg['jvm_xmx']} -jar atea.jar")
                wait()
            elif ch == "4":
                actl.cmd_stop()
                wait()
            elif ch == "5":
                actl.cmd_restart()
                wait()
            elif ch == "0":
                break
        finally:
            os.chdir(old_cwd)

def manage_db(cfg):
    actl = get_avatarctl(cfg)
    game_dir = cfg.get("game_dir", "")
    if not actl:
        p_err("Chưa có source! Vui lòng làm mục [2] trước.")
        wait()
        return
        
    while True:
        os.system("clear")
        p_h("QUẢN LÝ DATABASE")
        st = "MỞ" if port_open(cfg["db_port"]) else "ĐÓNG"
        print(f" Port DB: {cfg['db_port']} ({st})\n")
        
        print(" [1] Bật Database")
        print(" [2] Tắt Database")
        print(" [3] Trạng thái Database")
        print(" [0] Quay lại")
        
        ch = input(f"\n{C.BOLD}Chọn: {C.E}").strip()
        old_cwd = os.getcwd()
        os.chdir(game_dir)
        try:
            if ch == "1":
                actl.db_start()
                wait()
            elif ch == "2":
                actl.db_stop()
                wait()
            elif ch == "3":
                actl.cmd_db_status()
                wait()
            elif ch == "0":
                break
        finally:
            os.chdir(old_cwd)

def manage_accounts(cfg):
    actl = get_avatarctl(cfg)
    game_dir = cfg.get("game_dir", "")
    if not actl:
        p_err("Chưa có source! Vui lòng làm mục [2] trước.")
        wait()
        return

    while True:
        os.system("clear")
        p_h("QUẢN LÝ TÀI KHOẢN")
        print(" [1] Xem danh sách tài khoản & nhân vật")
        print(" [2] Tạo tài khoản mới")
        print(" [3] Tặng Lượng / Xu cho nhân vật")
        print(" [4] Chạy SQL tùy chỉnh")
        print(" [0] Quay lại")
        
        ch = input(f"\n{C.BOLD}Chọn: {C.E}").strip()
        old_cwd = os.getcwd()
        os.chdir(game_dir)
        try:
            if ch == "1":
                actl.cmd_players()
                wait()
            elif ch == "2":
                u = input("Username (3-20 ký tự): ").strip()
                p = input("Password (tối thiểu 4 ký tự): ").strip()
                vnd = input("Số VND tặng (mặc định 0): ").strip()
                vnd = int(vnd) if vnd.isdigit() else 0
                if u and p:
                    actl.cmd_register(u, p, vnd)
                wait()
            elif ch == "3":
                print("Lưu ý: Nhân vật phải ĐĂNG XUẤT trước khi tặng.")
                actl.cmd_players()
                uid = input("\nNhập ID nhân vật (char_id) để tặng: ").strip()
                if uid.isdigit():
                    amt = input("Nhập số tiền muốn set (VD: 100000000): ").strip()
                    if amt.isdigit():
                        actl.cmd_sql(f"UPDATE players SET luong={amt}, xu={amt} WHERE id={uid};")
                        p_ok(f"Đã cập nhật tiền cho nhân vật {uid}!")
                wait()
            elif ch == "4":
                sql = input("Nhập câu SQL: ").strip()
                if sql:
                    actl.cmd_sql(sql)
                wait()
            elif ch == "0":
                break
        finally:
            os.chdir(old_cwd)

def manage_ports(cfg):
    game_dir = cfg.get("game_dir", "")
    while True:
        os.system("clear")
        p_h("CẤU HÌNH KẾT NỐI (PORT & IP)")
        print(" [1] Đổi Port Game (config.properties)")
        print(" [2] Đổi Port DB (database.properties & my.cnf)")
        print(" [3] Đổi IP (host=127.0.0.1)")
        print(" [4] Xem Config file hiện tại")
        print(" [0] Quay lại")
        
        ch = input(f"\n{C.BOLD}Chọn: {C.E}").strip()
        
        if ch == "1":
            new_port = input(f"Nhập Port mới (hiện tại {cfg['server_port']}): ").strip()
            if new_port.isdigit():
                cfg['server_port'] = int(new_port)
                c_prop = os.path.join(game_dir, "config.properties")
                if os.path.exists(c_prop):
                    with open(c_prop, "r") as f: content = f.read()
                    content = re.sub(r'server\.port=\d+', f'server.port={new_port}', content)
                    with open(c_prop, "w") as f: f.write(content)
                    p_ok("Đã cập nhật Port Game.")
                save_config(cfg)
            wait()
        elif ch == "2":
            new_port = input(f"Nhập Port DB mới (hiện tại {cfg['db_port']}): ").strip()
            if new_port.isdigit():
                cfg['db_port'] = int(new_port)
                d_prop = os.path.join(game_dir, "database.properties")
                if os.path.exists(d_prop):
                    with open(d_prop, "r") as f: content = f.read()
                    content = re.sub(r'port=\d+', f'port={new_port}', content)
                    with open(d_prop, "w") as f: f.write(content)
                prefix = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
                mycnf = os.path.join(prefix, "etc/my.cnf")
                if os.path.exists(mycnf):
                    with open(mycnf, "r") as f: content = f.read()
                    content = re.sub(r'port\s*=\s*\d+', f'port={new_port}', content)
                    with open(mycnf, "w") as f: f.write(content)
                p_ok("Đã cập nhật Port DB. Bạn cần restart Database.")
                save_config(cfg)
            wait()
        elif ch == "3":
            new_ip = input("Nhập IP mới (hiện tại thường là 127.0.0.1): ").strip()
            if new_ip:
                d_prop = os.path.join(game_dir, "database.properties")
                if os.path.exists(d_prop):
                    with open(d_prop, "r") as f: content = f.read()
                    content = re.sub(r'host=.*', f'host={new_ip}', content)
                    with open(d_prop, "w") as f: f.write(content)
                    p_ok(f"Đã cập nhật host thành {new_ip}")
            wait()
        elif ch == "4":
            actl = get_avatarctl(cfg)
            if actl:
                old_cwd = os.getcwd()
                os.chdir(game_dir)
                try: actl.cmd_config()
                finally: os.chdir(old_cwd)
            wait()
        elif ch == "0":
            break

def patch_jar(cfg):
    game_dir = cfg.get("game_dir", "")
    os.system("clear")
    p_h("VÁ MOD JAR (.jar)")
    
    scan_paths = [game_dir, "/sdcard/Download"]
    all_files = []
    for path in scan_paths:
        if os.path.exists(path):
            try:
                files = [(f, path) for f in os.listdir(path) if f.endswith(".jar")]
                all_files.extend(files)
            except: pass
                
    if not all_files:
        p_err("Không tìm thấy file .jar nào trong Server hoặc Download.")
        wait()
        return
        
    for i, (f, p) in enumerate(all_files):
        loc = "Download" if "Download" in p else "Server"
        print(f"[{i+1}] {f} ({loc})")
        
    c = input("\nChọn file .jar để vá IP (0=hủy): ")
    if not c or c == "0" or not c.isdigit() or int(c) > len(all_files): return
    
    sel_file, sel_path = all_files[int(c)-1]
    jar_path = os.path.join(sel_path, sel_file)
    
    old_ip = input("Nhập IP hiện tại của file jar (Mặc định: 127.0.0.1 - Bỏ trống nếu không đổi): ").strip() or "127.0.0.1"
    new_ip = input("Nhập IP mới (VD: 192.168.1.5): ").strip()
    
    old_port = input("Nhập Port hiện tại (Bỏ trống nếu không đổi): ").strip()
    new_port = ""
    if old_port:
        new_port = input("Nhập Port mới (VD: 19128): ").strip()
        
    if (new_ip and old_ip != new_ip) or (new_port and old_port != new_port):
        p_info("Đang tiến hành vá Mod Jar...")
        tmp_dir = os.path.join(game_dir, "tmp_jar")
        os.system(f"rm -rf '{tmp_dir}' && mkdir -p '{tmp_dir}'")
        os.system(f"unzip -q '{jar_path}' -d '{tmp_dir}'")
        
        old_ip_bytes = len(old_ip).to_bytes(2, 'big') + old_ip.encode('utf-8') if old_ip else b''
        new_ip_bytes = len(new_ip).to_bytes(2, 'big') + new_ip.encode('utf-8') if new_ip else b''
        
        old_port_bytes = len(old_port).to_bytes(2, 'big') + old_port.encode('utf-8') if old_port else b''
        new_port_bytes = len(new_port).to_bytes(2, 'big') + new_port.encode('utf-8') if new_port else b''
        
        patched = 0
        for root, _, files in os.walk(tmp_dir):
            for f in files:
                if f.endswith(".class") or f.endswith(".txt"):
                    fp = os.path.join(root, f)
                    with open(fp, "rb") as file: content = file.read()
                    
                    changed = False
                    if new_ip and old_ip != new_ip:
                        if old_ip_bytes in content:
                            content = content.replace(old_ip_bytes, new_ip_bytes)
                            changed = True
                        elif old_ip.encode('utf-8') in content:
                            content = content.replace(old_ip.encode('utf-8'), new_ip.encode('utf-8'))
                            changed = True
                            
                    if new_port and old_port != new_port:
                        if old_port_bytes in content:
                            content = content.replace(old_port_bytes, new_port_bytes)
                            changed = True
                        elif old_port.encode('utf-8') in content:
                            content = content.replace(old_port.encode('utf-8'), new_port.encode('utf-8'))
                            changed = True
                            
                    if changed:
                        with open(fp, "wb") as file: file.write(content)
                        patched += 1
        
        if patched > 0:
            out_name = input("\nNhập tên file xuất ra (Enter mặc định: avatar_tea_patched.jar): ").strip()
            if not out_name: out_name = "avatar_tea_patched.jar"
            if not out_name.endswith(".jar"): out_name += ".jar"
            
            dl_dir = "/sdcard/Download"
            if not os.path.exists(dl_dir): dl_dir = HOME
            
            out_path = os.path.join(dl_dir, out_name)
            os.system(f"cd '{tmp_dir}' && zip -q -r '{out_path}' .")
            
            p_ok(f"Đã vá thành công {patched} file (IP/Port).")
            p_ok(f"File đã được chuyển ra: {out_path}")
            print(f"{C.CY}Hãy dùng file này cài đặt để chơi nhé!{C.E}")
        else:
            p_err("Không tìm thấy IP/Port cũ trong bất kỳ file nào.")
        os.system(f"rm -rf '{tmp_dir}'")
    wait()

def manage_ram(cfg):
    p_h("CẤU HÌNH RAM JAVA JVM")
    print(f"RAM tối đa hiện tại đang cài đặt là: {C.G}{cfg['jvm_xmx']}{C.E}")
    new_ram = input(f"Nhập RAM tối đa (VD: 512m, 1g - Enter để hủy): ").strip()
    if new_ram:
        cfg['jvm_xmx'] = new_ram
        save_config(cfg)
        p_ok("Đã cập nhật cấu hình RAM. (Khởi động lại server để áp dụng)")
    wait()

def manage_logs(cfg):
    actl = get_avatarctl(cfg)
    game_dir = cfg.get("game_dir", "")
    if not actl:
        p_err("Chưa có source!")
        wait(); return

    while True:
        os.system("clear")
        p_h("XEM LOG HỆ THỐNG")
        print(" [1] Xem 50 dòng log Game cuối")
        print(" [2] Theo dõi log Game trực tiếp (Follow)")
        print(" [3] Xem 50 dòng log Database cuối")
        print(" [0] Quay lại")
        
        ch = input(f"\n{C.BOLD}Chọn: {C.E}").strip()
        old_cwd = os.getcwd()
        os.chdir(game_dir)
        try:
            if ch == "1":
                actl.cmd_logs(50, False)
                wait()
            elif ch == "2":
                p_info("Nhấn Ctrl + C để thoát xem log.")
                try: actl.cmd_logs(50, True)
                except: pass
                wait()
            elif ch == "3":
                actl.cmd_db_log(50)
                wait()
            elif ch == "0":
                break
        finally:
            os.chdir(old_cwd)

def manage_web(cfg):
    game_dir = cfg.get("game_dir", "")
    web_dir = os.path.join(game_dir, "web")
    
    while True:
        os.system("clear")
        p_h("QUẢN LÝ WEB ĐĂNG KÝ")
        
        web_open = port_open(8080)
        st = f"{C.G}ON{C.E}" if web_open else f"{C.R}OFF{C.E}"
        ip = get_local_ip()
        print(f" Trạng thái Web: {st}")
        if web_open:
            print(f" URL Web    : {C.CY}http://{ip}:8080{C.E}")
            print(f" URL Admin  : {C.CY}http://{ip}:8080/admin.php{C.E}")
            
        print("\n [1] Bật Web Đăng Ký (Chạy ngầm ở port 8080)")
        print(" [2] Tắt Web Đăng Ký")
        print(" [0] Quay lại")
        
        ch = input(f"\n{C.BOLD}Chọn: {C.E}").strip()
        
        if ch == "1":
            if not os.path.exists(web_dir) or not os.path.exists(os.path.join(web_dir, "index.php")):
                p_err("Không tìm thấy thư mục web hoặc index.php! Vui lòng tải về.")
            else:
                if not web_open:
                    p_info("Đang khởi động PHP Built-in Server...")
                    log_web = os.path.join(HOME, "web.log")
                    subprocess.Popen(f"php -S 0.0.0.0:8080 -t '{web_dir}' > '{log_web}' 2>&1", shell=True)
                    time.sleep(2)
                    if port_open(8080):
                        p_ok("Đã khởi động Web thành công ở port 8080!")
                    else:
                        p_err("Không thể khởi động Web, vui lòng kiểm tra xem PHP đã được cài đặt chưa.")
                else:
                    p_ok("Web Đăng ký đang hoạt động rồi!")
            wait()
        elif ch == "2":
            if web_open:
                p_info("Đang tắt dịch vụ Web...")
                os.system("pkill -f 'php -S'")
                time.sleep(1)
                p_ok("Đã tắt Web thành công!")
            else:
                p_info("Dịch vụ Web hiện không chạy.")
            wait()
        elif ch == "0":
            break

def manage_backup(cfg):
    game_dir = cfg.get("game_dir", "")
    while True:
        os.system("clear")
        p_h("BACKUP & RESTORE DATABASE")
        print(" [1] Tạo bản Backup (Export DB)")
        print(" [2] Phục hồi (Restore DB)")
        print(" [3] Import SQL từ file (Ghi đè DB)")
        print(" [0] Quay lại")
        
        ch = input(f"\n{C.BOLD}Chọn: {C.E}").strip()
        if ch == "1":
            db_name = cfg["db_name"]
            t_str = time.strftime("%Y%m%d_%H%M%S")
            b_dir = os.path.join(HOME, "avt_backups")
            os.makedirs(b_dir, exist_ok=True)
            out_path = os.path.join(b_dir, f"backup_{db_name}_{t_str}.sql")
            p_info(f"Đang xuất DB ra {out_path}...")
            os.system(f"mariadb-dump -u root {db_name} > \"{out_path}\"")
            if os.path.exists(out_path): p_ok("Backup thành công!")
            else: p_err("Backup thất bại.")
            wait()
        elif ch == "2":
            scan_paths = [HOME, "/sdcard/Download", os.path.join(HOME, "avt_backups")]
            all_files = []
            for path in scan_paths:
                if os.path.exists(path):
                    for f in os.listdir(path):
                        if f.endswith(".sql"):
                            all_files.append((f, path))
            
            if not all_files:
                p_err("Không tìm thấy file .sql nào.")
                wait()
                continue
                
            for i, (f, p) in enumerate(all_files):
                print(f"[{i+1}] {f} ({p})")
            
            c = input("\nChọn file để phục hồi (0=hủy): ")
            if c.isdigit() and 1 <= int(c) <= len(all_files):
                sel_f, sel_p = all_files[int(c)-1]
                db_name = cfg["db_name"]
                full_path = os.path.join(sel_p, sel_f)
                p_info(f"Đang phục hồi {sel_f} vào DB {db_name}...")
                res = os.system(f"mariadb -u root {db_name} < \"{full_path}\"")
                if res == 0: p_ok("Phục hồi thành công!")
                else: p_err("Có lỗi khi phục hồi.")
            wait()
        elif ch == "3":
            file_path = input("Nhập đường dẫn file .sql để import: ").strip()
            if os.path.exists(file_path):
                db_name = cfg["db_name"]
                p_info(f"Đang import {file_path} vào {db_name}...")
                os.system(f"mariadb -u root {db_name} < \"{file_path}\"")
                p_ok("Import thành công!")
            else:
                p_err("File không tồn tại!")
            wait()
        elif ch == "0":
            break

def main():
    while True:
        cfg = load_config()
        
        srv_open = port_open(cfg["server_port"])
        db_open = port_open(cfg["db_port"])
        
        srv_st = f"{C.G}ON{C.E}" if srv_open else f"{C.R}OFF{C.E}"
        db_st = f"{C.G}OK{C.E}" if db_open else f"{C.R}OFF{C.E}"
        web_open = port_open(8080)
        web_st = f"{C.G}ON{C.E}" if web_open else f"{C.R}OFF{C.E}"
        ip = get_local_ip()
        
        os.system("clear")
        print(f"""{C.CY}{C.BOLD}
==========================================
     AVATAR TEAMOBI - SERVER MANAGER
=========================================={C.E}
 {C.BOLD}RAM: {get_ram_bar()}
 {C.BOLD}IP:  {C.G}{ip}{C.E} | PORT: {cfg['server_port']} | DB PORT: {cfg['db_port']}
 Server: {srv_st} | DB: {db_st} | WEB: {web_st}
------------------------------------------
 [1] Cài đặt môi trường hệ thống{get_stat(cfg, 'packages')}
 [2] Giải nén Source game (.tar.gz/.zip){get_stat(cfg, 'source')}
 [3] Thiết lập Database (Auto Fix){get_stat(cfg, 'db_setup')}
 [4] Cấu hình Kết nối (Port Game & DB)
 [5] Cấu hình RAM Java JVM
 [6] QUẢN LÝ DATABASE
 [7] VẬN HÀNH GAME SERVER: {srv_st}
 [8] QUẢN LÝ TÀI KHOẢN
 [9] XEM LOG HỆ THỐNG
 [W] QUẢN LÝ WEB ĐĂNG KÝ: {web_st}
 [V] VÁ MOD JAR (.jar)
 [A] BACKUP & RESTORE DATABASE
 [0] THOÁT
------------------------------------------""")
        ch = input(f"{C.BOLD}Lựa chọn của bạn: {C.E}").strip().upper()
        
        if ch == "1": install_env(cfg)
        elif ch == "2": extract_source(cfg)
        elif ch == "3": setup_db(cfg)
        elif ch == "4": manage_ports(cfg)
        elif ch == "5": manage_ram(cfg)
        elif ch == "6": manage_db(cfg)
        elif ch == "7": manage_server(cfg)
        elif ch == "8": manage_accounts(cfg)
        elif ch == "9": manage_logs(cfg)
        elif ch == "W": manage_web(cfg)
        elif ch == "V": patch_jar(cfg)
        elif ch == "A": manage_backup(cfg)
        elif ch == "0": break
        time.sleep(0.1)

if __name__ == "__main__":
    main()
