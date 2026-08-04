import os, json, socket, subprocess, time, re, sys, glob

class C:
    H='\033[95m';B='\033[94m';CY='\033[96m';G='\033[92m'
    Y='\033[93m';R='\033[91m';E='\033[0m';BOLD='\033[1m'

def p_h(t): print(f"\n{C.B}{C.BOLD}=== {t} ==={C.E}")
def p_ok(t): print(f"{C.G}[✓] {t}{C.E}")
def p_err(t): print(f"{C.R}[✗] {t}{C.E}")
def p_info(t): print(f"{C.CY}[i] {t}{C.E}")

def run_sql(query, fetch=False):
    cfg = load_config()
    db_pw = "123456"
    if cfg.get('lamp_backend', 'termux') == 'ksweb':
        cmd = f"mariadb --skip-ssl -h 127.0.0.1 -P 3306 -u root -p{db_pw} {cfg['db_name']} -e \"{query}\""
        if fetch:
            cmd = f"mariadb --skip-ssl -h 127.0.0.1 -P 3306 -u root -p{db_pw} {cfg['db_name']} --batch --skip-column-names -e \"{query}\""
    else:
        socket_path = f"{PREFIX}/tmp/mysql.sock"
        cmd = f"mariadb --socket={socket_path} -u root -p{db_pw} {cfg['db_name']} -e \"{query}\""
        if fetch:
            cmd = f"mariadb --socket={socket_path} -u root -p{db_pw} {cfg['db_name']} --batch --skip-column-names -e \"{query}\""
            
    if fetch:
        try: return subprocess.check_output(cmd, shell=True).decode().strip()
        except: return ""
    else:
        return os.system(cmd)

def patch_binary_string(data, old_sub, new_sub):
    """Vá một phần chuỗi bên trong một entry UTF-8 (tag 0x01) với việc tính toán lại độ dài chuẩn Java"""
    old_b = old_sub.encode('utf-8')
    new_b = new_sub.encode('utf-8')
    new_data = bytearray(data)
    i = 0
    modified = False
    while i < len(new_data) - 3:
        if new_data[i] == 0x01: # Tag Utf8
            length = int.from_bytes(new_data[i+1:i+3], byteorder='big')
            if i + 3 + length <= len(new_data):
                content = new_data[i+3:i+3+length]
                if old_b in content:
                    old_str = content.decode('utf-8', errors='ignore')
                    new_str = old_str.replace(old_sub, new_sub)
                    new_str_b = new_str.encode('utf-8')
                    new_len_b = len(new_str_b).to_bytes(2, byteorder='big')
                    # Thay thế entry cũ bằng entry mới: [Tag][Len][Bytes]
                    new_entry = b'\x01' + new_len_b + new_str_b
                    new_data[i : i + 3 + length] = new_entry
                    i += 3 + len(new_str_b)
                    modified = True
                    continue
        i += 1
    return bytes(new_data) if modified else data

def patch_source_code():
    """Tự động vá lỗi bảo trì và giới hạn IP trong source code Java"""
    server_java = os.path.join(HOME, "src/main/java/Exe_Z/server/Server.java")
    if os.path.exists(server_java):
        p_info("Đang vá Server.java...")
        with open(server_java, 'r', encoding='utf-8') as f: content = f.read()
        
        # 1. Xóa bỏ bảo trì định kỳ
        content = content.replace("AutoMaintenance.maintenance(0, 0, 0);", "// AutoMaintenance.maintenance(0, 0, 0);")
        
        # 2. Ép isStop = false khi khởi động
        if "NinjaSchool.isStop = false;" not in content:
            content = content.replace("public static void start() {\n        try {\n            setOffline();", 
                                      "public static void start() {\n        try {\n            NinjaSchool.isStop = false;\n            setOffline();")
        
        # 3. Mở giới hạn IP cho localhost (127.0.0.1)
        if "!ip.equals(\"127.0.0.1\")" not in content:
            old_check = "if (number >= Config.getInstance().getIpAddressLimit()) {"
            new_check = "if (!ip.equals(\"127.0.0.1\") && number >= Config.getInstance().getIpAddressLimit()) {"
            content = content.replace(old_check, new_check)
            
        with open(server_java, 'w', encoding='utf-8') as f: f.write(content)
        p_ok("Đã vá Source Code thành công!")
    else:
        p_err("Không tìm thấy Server.java để vá!")

def resolve_ip(domain):
    try:
        if re.match(r"^\d+\.\d+\.\d+\.\d+$", domain): return domain
        return socket.gethostbyname(domain)
    except: return domain

def get_ram_bar():
    try:
        res = subprocess.check_output("free -m", shell=True).decode()
        lines = res.split('\n')
        mem = lines[1].split()
        total, used = int(mem[1]), int(mem[2])
        percent = int(used * 100 / total)
        bar_len = 15
        filled = int(percent * bar_len / 100)
        bar = "█" * filled + "░" * (bar_len - filled)
        color = C.G if percent < 70 else (C.Y if percent < 90 else C.R)
        return f"{color}[{bar}] {percent}%{C.E}"
    except: return "[N/A]"

# TỰ ĐỘNG NHẬN DIỆN MÔI TRƯỜNG TERMUX
PREFIX = os.environ.get('PREFIX', '/data/data/com.termux/files/usr')
HOME = os.environ.get('HOME', '/data/data/com.termux/files/home')
TMP = f"{PREFIX}/tmp"
SOCKET = f"{TMP}/mysql.sock"
CONFIG_FILE = os.path.join(HOME, "nso_config.json")
# BASE_DIR = thư mục chứa mã nguồn (src/, pom.xml, ...)
BASE_DIR = HOME  # Mặc định, sẽ cập nhật sau khi giải nén

def get_free_port(start_port):
    port = start_port
    while port < start_port + 10:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.2)
        if s.connect_ex(('127.0.0.1', port)) != 0:
            s.close()
            return port
        s.close()
        port += 1
    return start_port

def load_config():
    # Giá trị mặc định ban đầu
    defaults = {"db_name":"nsoz","tcp_domain":get_local_ip(),"tcp_port":14444,
                "mode":"offline","jvm_xmx":"512m",
                "lamp_backend":"termux",
                "web_port": 8080,
                "local_game_port": 14444,
                "base_dir": HOME,
                "status":{"env":False,"db_web":False}}
    
    cfg = defaults.copy()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE,'r') as f:
                saved_cfg = json.load(f)
                cfg.update(saved_cfg)
        except: pass
    else:
        # Chỉ tìm port trống nếu chưa có cấu hình
        cfg['web_port'] = get_free_port(8080)
        cfg['web_url'] = f"http://{get_local_ip()}:{cfg['web_port']}"
        save_config(cfg)
        
    return cfg

def save_config(cfg):
    with open(CONFIG_FILE,'w') as f: json.dump(cfg,f,indent=4)

def get_local_ip():
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        s.connect(("8.8.8.8",80));ip=s.getsockname()[0];s.close();return ip
    except: return "127.0.0.1"

def is_port_open(port):
    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.settimeout(0.3)
    res=s.connect_ex(('127.0.0.1',port));s.close();return res==0

def is_java_running():
    try:
        out=subprocess.check_output("ps -ef | grep '[j]ava.*Nso-jar'",shell=True,stderr=subprocess.DEVNULL).decode().strip()
        return len(out)>0
    except: return False

def is_installed():
    """Kiểm tra đã giải nén mã nguồn chưa"""
    return os.path.exists(os.path.join(HOME, "pom.xml")) or os.path.exists(os.path.join(HOME, "src"))

def is_db_running():
    try:
        # Thay vì dùng -x (khớp tuyệt đối), chúng ta dùng pgrep thông thường để tăng độ nhạy
        subprocess.check_output("pgrep mariadbd || pgrep mysqld", shell=True)
        return True
    except:
        return False

# ==========================================
# CHẾ ĐỘ CÀI ĐẶT LẦN ĐẦU
# ==========================================
def first_time_setup():
    os.system("clear")
    print(f"""{C.CY}{C.BOLD}
==========================================
  NSO SERVER - THIẾT LẬP LẦN ĐẦU
=========================================={C.E}
{C.Y}Chào mừng bạn! Để bắt đầu, hãy làm theo
các bước bên dưới:{C.E}
------------------------------------------
 [1] TÌM & GIẢI NÉN FILE TỪ DOWNLOAD
 [2] CÀI ĐẶT MÔI TRƯỜNG & DATABASE
 [3] BUILD SERVER (MAVEN)
 [0] THOÁT
------------------------------------------""")
    ch = input("Lựa chọn: ")

    if ch == "1":
        find_and_extract()
    elif ch == "2":
        install_env_fresh()
    elif ch == "3":
        full_setup()
    elif ch == "0":
        return False
    return True

def find_and_extract():
    p_h("TÌM FILE NÉN TRONG THƯ MỤC DOWNLOAD")
    
    # Quét các thư mục Download phổ biến trên Android
    search_dirs = [
        "/sdcard/Download", "/sdcard/Downloads",
        "/storage/emulated/0/Download", "/storage/emulated/0/Downloads",
        "/sdcard"
    ]
    
    found = []
    for d in search_dirs:
        if os.path.isdir(d):
            for ext in ["*.tar.gz", "*.tgz", "*.zip"]:
                found.extend(glob.glob(os.path.join(d, f"*nso*{ext}")))
                found.extend(glob.glob(os.path.join(d, f"*NSO*{ext}")))
                found.extend(glob.glob(os.path.join(d, f"*Exe*{ext}")))
    
    # Loại bỏ trùng lặp
    found = list(set(found))
    
    if not found:
        p_err("Không tìm thấy file nén nào!")
        print(f"\n{C.Y}Hướng dẫn:{C.E}")
        print("1. Tải file nén từ link được chia sẻ")
        print("2. Lưu vào thư mục Download của điện thoại")
        print("3. Quay lại đây và thử lại")
        print(f"\n{C.CY}Hoặc nhập đường dẫn thủ công:{C.E}")
        manual = input("Đường dẫn (Enter để bỏ qua): ").strip()
        if manual and os.path.exists(manual):
            found = [manual]
        else:
            input("\nEnter..."); return
    
    print(f"\n{C.G}Tìm thấy {len(found)} file:{C.E}")
    for i, f in enumerate(found):
        size = os.path.getsize(f) / (1024*1024)
        print(f"  [{i+1}] {os.path.basename(f)} ({size:.1f} MB)")
    
    ch = input(f"\nChọn file (1-{len(found)}): ").strip()
    try:
        idx = int(ch) - 1
        chosen = found[idx]
    except:
        p_err("Lựa chọn không hợp lệ"); input("\nEnter..."); return
    
    p_info(f"Đang giải nén {os.path.basename(chosen)}...")
    
    if chosen.endswith(".zip"):
        ret = os.system(f"unzip -o '{chosen}' -d {HOME}")
    else:
        ret = os.system(f"tar xzf '{chosen}' -C {HOME}")
    
    if ret == 0:
        # Tìm thư mục vừa giải nén (chứa pom.xml)
        for item in os.listdir(HOME):
            pom = os.path.join(HOME, item, "pom.xml")
            if os.path.isdir(os.path.join(HOME, item)) and os.path.exists(pom):
                # Di chuyển nội dung vào HOME
                src_dir = os.path.join(HOME, item)
                os.system(f"cp -rn {src_dir}/* {HOME}/ 2>/dev/null")
                os.system(f"cp -rn {src_dir}/.* {HOME}/ 2>/dev/null")
                p_ok(f"Đã giải nén từ thư mục: {item}")
                break
        
        if is_installed():
            print(f"\n{C.G}{C.BOLD}🎉 GIẢI NÉN THÀNH CÔNG!{C.E}")
            print(f"Bây giờ hãy chọn [2] để cài môi trường.")
        else:
            p_ok("Đã giải nén! Kiểm tra lại cấu trúc thư mục.")
    else:
        p_err("Giải nén thất bại!")
    input("\nEnter...")

def install_env_fresh():
    p_h("CÀI ĐẶT MÔI TRƯỜNG VẠN NĂNG")
    print(f"\n{C.H}Chọn Backend chạy Web & Database:{C.E}")
    print("[1] Termux LAMP (Cài đặt nội bộ, khuyên dùng máy mạnh)")
    print("[2] KSWEB Hybrid (Dùng App ngoài, ổn định nhất cho máy yếu/lỗi)")
    b = input("Chọn (1/2): ")
    cfg = load_config()
    if b == "2":
        cfg['lamp_backend'] = 'ksweb'
        save_config(cfg)
        setup_ksweb()
        return

    cfg['lamp_backend'] = 'termux'
    save_config(cfg)
    p_info("Đang cập nhật và cài đặt các gói cần thiết...")
    
    # Giải phóng tiến trình treo trước khi cài
    os.system("pkill -9 mariadbd mariadbd-safe nginx php-fpm > /dev/null 2>&1")
    
    # Bổ sung procps để có pgrep, pkill chuẩn
    pkgs = "openjdk-17 mariadb nginx php php-fpm maven wget git tmux lsof tar zip unzip procps cloudflared"
    if os.system(f"pkg update -y && pkg install {pkgs} -y") == 0:
        p_ok("Môi trường cơ bản đã sẵn sàng!")
        # Tự động chạy thiết lập DB & Web luôn cho tiện
        full_setup()
    else:
        p_err("Cài đặt gặp lỗi. Hãy kiểm tra kết nối mạng của bạn.")
    input("\nEnter...")


def setup_ksweb():
    p_h("THIẾT LẬP KSWEB HYBRID")
    p_info("Vui lòng thực hiện các bước sau trên điện thoại:")
    print("1. Cài đặt và mở ứng dụng KSWEB.")
    print("2. Bật Lighttpd (hoặc Nginx) trên cổng 8080.")
    print("3. Bật MySQL trên cổng 3306.")
    input(f"\n{C.G}Nhấn Enter khi KSWEB đã BẬT thành công...{C.E}")
    
    cfg = load_config()
    
    # Tự động kết nối và đổi mật khẩu KSWEB thành 123456
    p_info("Đang tự động cấu hình Database KSWEB...")
    os.system("pkg install mariadb -y > /dev/null 2>&1")
    
    # Kiểm tra xem mật khẩu đã được thiết lập là 123456 chưa
    ret_pw = os.system("mariadb --skip-ssl -h 127.0.0.1 -P 3306 -u root -p123456 -e 'SELECT 1;' > /dev/null 2>&1")
    if ret_pw == 0:
        p_ok("Kết nối thành công! Mật khẩu MySQL đã được cấu hình là 123456.")
        # Đảm bảo root@127.0.0.1 có đủ quyền
        os.system("mariadb --skip-ssl -h 127.0.0.1 -P 3306 -u root -p123456 -e \"GRANT ALL PRIVILEGES ON *.* TO 'root'@'127.0.0.1' IDENTIFIED BY '123456' WITH GRANT OPTION; FLUSH PRIVILEGES;\" > /dev/null 2>&1")
    else:
        # Thử kết nối không pass (KSWEB mặc định pass rỗng)
        ret_empty = os.system("mariadb --skip-ssl -h 127.0.0.1 -P 3306 -u root -e 'SELECT 1;' > /dev/null 2>&1")
        if ret_empty == 0:
            p_info("Phát hiện mật khẩu mặc định rỗng. Đang đổi mật khẩu thành 123456...")
            r1 = os.system("mariadb --skip-ssl -h 127.0.0.1 -P 3306 -u root -e \"UPDATE mysql.user SET Password=PASSWORD('123456') WHERE User='root'; FLUSH PRIVILEGES;\" > /dev/null 2>&1")
            if r1 != 0:
                os.system("mariadb --skip-ssl -h 127.0.0.1 -P 3306 -u root -e \"ALTER USER 'root'@'localhost' IDENTIFIED BY '123456'; FLUSH PRIVILEGES;\" > /dev/null 2>&1")
            os.system("mariadb --skip-ssl -h 127.0.0.1 -P 3306 -u root -p123456 -e \"GRANT ALL PRIVILEGES ON *.* TO 'root'@'127.0.0.1' IDENTIFIED BY '123456' WITH GRANT OPTION; FLUSH PRIVILEGES;\" > /dev/null 2>&1")
            p_ok("Đã cấu hình mật khẩu MySQL KSWEB thành 123456!")
        else:
            p_err("Không kết nối được MySQL KSWEB! Kiểm tra lại App KSWEB đã bật chưa hoặc mật khẩu đã bị đổi khác.")
    
    # Tạo db và import
    db = cfg["db_name"]
    sql = os.path.join(HOME, "SQL/nsoz.sql")
    os.system(f"mariadb --skip-ssl -h 127.0.0.1 -P 3306 -u root -p123456 -e 'CREATE DATABASE IF NOT EXISTS {db} CHARACTER SET utf8mb4;' > /dev/null 2>&1")
    if os.path.exists(sql):
        os.system(f"mariadb --skip-ssl -h 127.0.0.1 -P 3306 -u root -p123456 {db} < '{sql}' > /dev/null 2>&1")
        p_ok("Đã tạo Database và Import dữ liệu!")
    
    # Tự động copy Web ra htdocs
    p_info("Đang xuất mã nguồn Web ra KSWEB htdocs...")
    htdocs = "/sdcard/htdocs/nso_web"
    os.system(f"mkdir -p {htdocs}")
    src_web = os.path.join(HOME, "nso_web")
    if not os.path.isdir(src_web):
        src_web = os.path.join(HOME, "web")
    if os.path.isdir(src_web):
        os.system(f"cp -r {src_web}/* {htdocs}/")
        # Vá PHP kết nối localhost -> 127.0.0.1
        os.system(f'find {htdocs} -name "*.php" -exec sed -i \'s/"localhost"/"127.0.0.1"/g\' {{}} +')
        p_ok(f"Đã xuất Web ra {htdocs}!")
    
    # Vá config.properties: tắt SSL cho JDBC kết nối KSWEB MySQL
    prop = os.path.join(HOME, "config.properties")
    if os.path.exists(prop):
        p_info("Đang vá config.properties để tắt SSL cho JDBC...")
        with open(prop, 'r', encoding='utf-8', errors='ignore') as f:
            t = f.read()
        # Thêm useSSL=false nếu chưa có
        if 'useSSL=false' not in t:
            # Tìm dòng db.driver và thêm dòng jdbc.extra sau nó
            t = t.replace('db.driver=com.mysql.cj.jdbc.Driver',
                           'db.driver=com.mysql.cj.jdbc.Driver\ndb.url.extra=?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC')
        # Đảm bảo db.host=127.0.0.1
        import re as _re
        t = _re.sub(r'db\.host=.*', 'db.host=127.0.0.1', t)
        t = _re.sub(r'db\.password=.*', 'db.password=123456', t)
        with open(prop, 'w', encoding='utf-8') as f:
            f.write(t)
        p_ok("Đã vá config.properties (useSSL=false, db.host=127.0.0.1)!")
    
    p_ok("THIẾT LẬP KSWEB HOÀN TẤT!")
    print("Vui lòng vào [4] để Vá IP & Build Server.")
    input("\nEnter...")

def full_setup():
    p_h("THIẾT LẬP DB & WEB")
    cfg = load_config()

    # =============================================
    # BƯỚC 1: Dọn dẹp toàn bộ dịch vụ cũ
    # =============================================
    p_info("Đang dọn dẹp tiến trình cũ...")
    os.system("killall -9 nginx php-fpm mariadbd mariadbd-safe 2>/dev/null")
    os.system("pkill -9 -f mariadbd; pkill -9 -f nginx; pkill -9 -f php-fpm > /dev/null 2>&1")
    os.system(f"rm -f {SOCKET} {TMP}/mysqld.sock")
    time.sleep(2)

    # =============================================
    # BƯỚC 2: Khởi tạo dữ liệu MariaDB nếu chưa có
    # =============================================
    if not os.path.exists(os.path.join(PREFIX, "var/lib/mysql/mysql")):
        p_info("Đang khởi tạo Database lần đầu...")
        os.system("mariadb-install-db --datadir=$PREFIX/var/lib/mysql > /dev/null 2>&1 || mysql_install_db > /dev/null 2>&1")
    os.system(f"mkdir -p {PREFIX}/var/run/mysqld {TMP}")

    # =============================================
    # BƯỚC 3: Bật MariaDB chế độ bypass xác thực
    # (skip-grant-tables để tránh lỗi unix_socket)
    # =============================================
    p_info("Đang khởi động MariaDB (chế độ cài đặt)...")
    os.system(f"mariadbd-safe --socket={SOCKET} --skip-grant-tables --skip-networking > /dev/null 2>&1 &")
    
    socket_ready = False
    for i in range(30):
        if os.path.exists(SOCKET):
            socket_ready = True
            break
        time.sleep(1)
    
    if not socket_ready:
        p_err("MariaDB không khởi động được! Thử lại sau.")
        input("\nEnter..."); return

    # =============================================
    # BƯỚC 4: Tạo Database và Import SQL
    # =============================================
    db = cfg["db_name"]
    p_info(f"Đang tạo database '{db}'...")
    os.system(f"mariadb --socket={SOCKET} -e 'CREATE DATABASE IF NOT EXISTS {db} CHARACTER SET utf8mb4;'")

    sql = os.path.join(HOME, "SQL/nsoz.sql")
    if os.path.exists(sql):
        p_info(f"Đang import dữ liệu vào '{db}' (vui lòng chờ)...")
        ret = os.system(f"mariadb --socket={SOCKET} {db} < '{sql}'")
        if ret == 0:
            p_ok("Import SQL thành công!")
        else:
            p_err("Import SQL gặp lỗi (có thể do dữ liệu đã tồn tại - bỏ qua)")
    else:
        p_err(f"Không tìm thấy file SQL tại: {sql}")

    # =============================================
    # BƯỚC 5: Vá bảng global_priv để đổi plugin
    # xác thực từ unix_socket -> mysql_native_password
    # (Đây là bước quan trọng nhất - cho phép Java kết nối qua TCP)
    # =============================================
    p_info("Đang cấu hình xác thực cho root@localhost...")
    sql_fix = (
        "UPDATE mysql.global_priv SET priv=JSON_SET(priv,"
        "  '$.plugin', 'mysql_native_password',"
        "  '$.authentication_string', '',"
        "  '$.password_last_changed', UNIX_TIMESTAMP()"
        ") WHERE user='root' AND host='localhost';"
    )
    os.system(f"mariadb --socket={SOCKET} -e \"{sql_fix}\"")

    # Thêm user root@127.0.0.1 vào global_priv
    sql_insert = (
        "INSERT IGNORE INTO mysql.global_priv (Host, User, Priv) VALUES ("
        "'127.0.0.1', 'root', "
        "'{\"access\":18446744073709551615,\"version_id\":100512,"
        "\"plugin\":\"mysql_native_password\",\"authentication_string\":\"\"}'"
        ");"
    )
    os.system(f"mariadb --socket={SOCKET} -e \"{sql_insert}\"")

    # =============================================
    # BƯỚC 6: Khởi động lại MariaDB bình thường + TCP
    # =============================================
    p_info("Đang khởi động lại MariaDB với TCP 3306...")
    os.system("pkill -9 -f mariadbd")
    time.sleep(3)
    os.system(f"rm -f {SOCKET} {TMP}/mysqld.sock")
    os.system(f"mariadbd-safe --socket={SOCKET} --port=3306 --bind-address=127.0.0.1 > /dev/null 2>&1 &")
    
    for i in range(30):
        if os.path.exists(SOCKET):
            break
        time.sleep(1)
    time.sleep(2)

    # =============================================
    # BƯỚC 7: Cấp quyền TCP cho Java (JDBC)
    # Chạy SAU khi restart - lúc này server có privilege tables
    # =============================================
    p_info("Đang cấu hình mật khẩu và quyền TCP cho Java...")
    # Lúc này pass vẫn đang trống nên không dùng -p cho lệnh đầu tiên
    os.system(f"mariadb --socket={SOCKET} -u root -e \"ALTER USER 'root'@'localhost' IDENTIFIED BY '123456';\"")
    # Các lệnh sau dùng -p123456 vì pass đã có hiệu lực. Tạo user nếu chưa có.
    os.system(f"mariadb --socket={SOCKET} -u root -p123456 -e \"CREATE USER IF NOT EXISTS 'root'@'127.0.0.1' IDENTIFIED BY '123456';\"")
    os.system(f"mariadb --socket={SOCKET} -u root -p123456 -e \"GRANT ALL PRIVILEGES ON *.* TO 'root'@'127.0.0.1' WITH GRANT OPTION;\"")
    os.system(f"mariadb --socket={SOCKET} -u root -p123456 -e \"CREATE USER IF NOT EXISTS 'root'@'%' IDENTIFIED BY '123456';\"")
    os.system(f"mariadb --socket={SOCKET} -u root -p123456 -e \"GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;\"")
    os.system(f"mariadb --socket={SOCKET} -u root -p123456 -e \"FLUSH PRIVILEGES;\"")
    os.system(f"ln -sf {SOCKET} {TMP}/mysqld.sock")
    p_ok("Database đã sẵn sàng và cho phép kết nối TCP!")

    # =============================================
    # BƯỚC 8: Cấu hình và bật Nginx + PHP-FPM
    # =============================================
    p_info(f"Đang cấu hình Web trên Port {cfg['web_port']}...")
    os.system("pkill -9 nginx; pkill -9 php-fpm")
    time.sleep(1)
    web_dir = os.path.join(HOME, "nso_web")
    os.makedirs(web_dir, exist_ok=True)

    # Tự động copy file web từ thư mục web/ vào nso_web/ nếu nso_web còn trống
    src_web = os.path.join(HOME, "web")
    if os.path.isdir(src_web):
        existing_files = os.listdir(web_dir)
        if not existing_files:
            p_info("Đang copy file web vào thư mục phục vụ...")
            os.system(f"cp -rf {src_web}/. {web_dir}/")
            os.system(f"chmod -R 755 {web_dir}/")
            p_ok("Copy file web thành công!")
        # Vá tất cả file PHP: đổi 'localhost' -> '127.0.0.1'
        # để PHP kết nối MySQL qua TCP thay vì Unix Socket
        p_info("Đang vá kết nối Database trong file PHP...")
        os.system(f'find {web_dir} -name "*.php" -exec sed -i \'s/"localhost"/"127.0.0.1"/g\' {{}} +')
        os.system(f"find {web_dir} -name '*.php' -exec sed -i \"s/'localhost'/'127.0.0.1'/g\" {{}} +")
        p_ok("Vá PHP localhost -> 127.0.0.1 hoàn tất!")
    
    # Tạo thư mục logs và file thông báo mặc định
    p_info("Đang khởi tạo thư mục logs và file thông báo...")
    log_tb = os.path.join(HOME, "logs", "thongbao")
    os.makedirs(log_tb, exist_ok=True)
    tb_file = os.path.join(log_tb, "thongbao.txt")
    new_msg = "Chào mừng các bạn đến với NSO termux với SRC được chia sẻ bởi Trưởng Quốc Thiện tại https://nsoexe.com/ được chỉnh sửa để chạy trên termux bởi VN Pro chúc các bạn chơi game vui vẻ !"
    if not os.path.exists(tb_file):
        with open(tb_file, "w", encoding="utf-8") as f:
            f.write(new_msg)
    else:
        try:
            with open(tb_file, "r", encoding="utf-8", errors="ignore") as f:
                curr = f.read().strip()
            if "NSO PRO MANAGER" in curr or curr == "":
                with open(tb_file, "w", encoding="utf-8") as f:
                    f.write(new_msg)
                p_ok("Đã tự động nâng cấp câu chào mới nhất!")
        except: pass
    p_ok("Khởi tạo logs thành công!")

    nginx_conf = os.path.join(PREFIX, "etc/nginx/nginx.conf")
    conf_content = f"""worker_processes  1;
events {{ worker_connections  1024; }}
http {{
    include       mime.types;
    default_type  application/octet-stream;
    sendfile        on;
    keepalive_timeout  65;
    server {{
        listen       {cfg['web_port']};
        server_name  localhost;
        root         {web_dir};
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

    fpm_conf = os.path.join(PREFIX, "etc/php-fpm.d/www.conf")
    if os.path.exists(fpm_conf):
        os.system(f"sed -i 's/^listen = .*/listen = 127.0.0.1:9000/' {fpm_conf}")

    os.system("pkill -9 -f nginx; pkill -9 -f php-fpm > /dev/null 2>&1")
    time.sleep(1)
    os.system("php-fpm; nginx")
    p_ok(f"Web sẵn sàng tại: http://{get_local_ip()}:{cfg['web_port']}")

    # =============================================
    # BƯỚC 9: Build Server
    # =============================================
    p_info("Đang build server (Maven)...")
    ret = subprocess.run(["mvn", "clean", "package", "-DskipTests"], cwd=HOME)
    if ret.returncode == 0:
        print(f"\n{C.G}{C.BOLD}🚀 THIẾT LẬP HOÀN TẤT! Server sẵn sàng chạy.{C.E}")
        print(f"  -> Vào [6] để bật Game Server.")
    else:
        p_err("Build Maven thất bại! Kiểm tra mã nguồn src/")
    input("\nEnter...")

# ==========================================
# QUẢN LÝ TÀI KHOẢN (Ported from nro.py)
# ==========================================
def manage_account():
    p_h("QUẢN LÝ TÀI KHOẢN")
    print("[1] Liệt kê 20 tài khoản mới nhất")
    print("[2] Tìm kiếm tài khoản theo tên")
    print("[3] Đổi mật khẩu")
    print("[0] Quay lại")
    ch = input("\nChọn: ")
    
    if ch == "1":
        res = run_sql("SELECT username, status FROM users ORDER BY id DESC LIMIT 20;", fetch=True)
        if res:
            print(f"\n{C.Y}{'Username'.ljust(15)} | {'Trạng thái'}{C.E}")
            print("-" * 30)
            for line in res.split('\n'):
                parts = line.split('\t')
                if len(parts) >= 2:
                    print(f"{parts[0].ljust(15)} | {'Hoạt động' if parts[1]=='0' else 'Bị khóa'}")
        else: p_err("Không có dữ liệu.")
    elif ch == "2":
        name = input("Nhập tên tài khoản: ")
        res = run_sql(f"SELECT username, status FROM users WHERE username LIKE '%{name}%';", fetch=True)
        if res:
            for line in res.split('\n'): print(f" > {line.replace('\t', ' - ')}")
        else: p_err("Không tìm thấy.")
    elif ch == "3":
        name = input("Tên tài khoản: ")
        pw = input("Mật khẩu mới: ")
        if run_sql(f"UPDATE users SET password='{pw}' WHERE username='{name}';") == 0:
            p_ok("Đã đổi mật khẩu!")
        else: p_err("Thất bại.")
    input("\nEnter...")

# ==========================================
# QUẢN LÝ KẾT NỐI (Ported from nro.py)
# ==========================================
def manage_tcp(cfg):
    p_h("CẤU HÌNH KẾT NỐI & NGROK")
    mode_str = cfg.get('mode', 'offline').upper()
    print(f"Chế độ hiện tại: {C.H}{mode_str}{C.E}")
    print(f"Địa chỉ hiện tại: {C.Y}{cfg['tcp_domain']}:{cfg['tcp_port']}{C.E}")
    
    print(f"\n[1] Cài đặt Ngrok (ARM64)")
    print(f"[2] Khởi chạy & Quản lý Ngrok")
    print(f"[3] Online: Tự động lấy từ Ngrok API")
    print(f"[4] Online: Tìm TCP theo Link (Playit/Ngrok)")
    print(f"[5] Online: Nhập IP/Port thủ công")
    print(f"[6] Offline: Chạy mạng LAN/WiFi")
    print(f"[7] Online: Mở cổng Web (Ngrok HTTP)")
    print(f"[8] Online: Mở cổng Web (Cloudflare)")
    print(f"[0] Quay lại")
    ch = input(f"\n{C.BOLD}Chọn: {C.E}")

    if ch == "1":
        p_info("Đang cài đặt Ngrok...")
        os.system("wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.tgz -O ngrok.tgz")
        os.system("tar -xvzf ngrok.tgz && mv ngrok $PREFIX/bin/ && chmod +x $PREFIX/bin/ngrok && rm ngrok.tgz")
        token = input("\nNhập Authtoken Ngrok (Enter để bỏ qua nếu đã cài): ").strip()
        if token:
            os.system(f"ngrok config add-authtoken {token}")
            p_ok("Đã cấu hình Authtoken!")
        p_ok("Cài đặt xong!")
    elif ch == "2":
        sc = input("\n[1] Chạy trực tiếp\n[2] Chạy ngầm (Tmux)\n[0] Tắt Ngrok\nChọn: ")
        if sc == "1": os.system(f"ngrok tcp {cfg['local_game_port']}")
        elif sc == "2":
            os.system(f"pkill -9 ngrok; tmux new-session -d -s nso_ngrok 'ngrok tcp {cfg['local_game_port']}'")
            p_ok("Đang chạy ngầm (nso_ngrok)")
        elif sc == "0": os.system("pkill -9 ngrok"); p_ok("Đã tắt")
    elif ch == "3":
        try:
            import urllib.request
            with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels") as r:
                tunnels = json.loads(r.read().decode()).get('tunnels', [])
                tcp_tunnels = [t for t in tunnels if t.get('proto') == 'tcp']
                if not tcp_tunnels: p_err("Không thấy TCP tunnel!"); input(); return
                url = tcp_tunnels[0].get('public_url', '').replace('tcp://', '')
                if ':' in url:
                    d, p = url.rsplit(':', 1)
                    cfg['tcp_domain'] = resolve_ip(d); cfg['tcp_port'] = int(p); cfg['mode'] = 'online'
                    save_config(cfg); p_ok(f"Đã lưu: {cfg['tcp_domain']}:{p}")
        except: p_err("Lỗi Ngrok API")
    elif ch == "4":
        link = input("Nhập địa chỉ (Domain:Port): ").strip().replace("tcp://", "")
        if ':' in link:
            d, p = link.rsplit(':', 1)
            cfg['tcp_domain'] = resolve_ip(d); cfg['tcp_port'] = int(p); cfg['mode'] = 'online'
            save_config(cfg); p_ok("OK")
    elif ch == "6":
        cfg["mode"] = "offline"; cfg["tcp_domain"] = get_local_ip(); cfg["tcp_port"] = cfg['local_game_port']
        save_config(cfg); p_ok(f"OFFLINE: {cfg['tcp_domain']}")
    elif ch == "7":
        backend = cfg.get('lamp_backend', 'termux')
        active_web_port = 8080 if backend == 'ksweb' else cfg.get('web_port', 8080)
        os.system("pkill -9 ngrok 2>/dev/null; tmux kill-session -t nso_ngrok_web 2>/dev/null")
        os.system(f"tmux new-session -d -s nso_ngrok_web 'ngrok http {active_web_port}'")
        p_ok(f"Ngrok HTTP Web started on port {active_web_port}")
        p_info("Đợi vài giây để lấy link ở màn hình chính...")
    elif ch == "8":
        backend = cfg.get('lamp_backend', 'termux')
        active_web_port = 8080 if backend == 'ksweb' else cfg.get('web_port', 8080)
        if os.system("command -v cloudflared >/dev/null") != 0:
            p_info("Đang cài đặt cloudflared...")
            os.system("pkg update -y && pkg install cloudflared -y")
        os.system("tmux kill-session -t nso_cf 2>/dev/null")
        os.system(f"tmux new-session -d -s nso_cf 'cloudflared tunnel --protocol http2 --url http://127.0.0.1:{active_web_port} 2>&1 | tee {TMP}/cf.log'")
        p_ok(f"Cloudflare Tunnel started on port {active_web_port}")
        p_info("Đợi vài giây để lấy link ở màn hình chính...")
    input("\nEnter...")

def config_ram(cfg):
    p_h("CẤU HÌNH RAM & SWAP")
    try:
        mem = subprocess.check_output("free -m", shell=True).decode()
        lines = mem.split('\n')
        m_line = lines[1].split()
        total, used = int(m_line[1]), int(m_line[2])
        avail = int(m_line[6]) if len(m_line)>6 else total-used
        
        swap_line = lines[2].split() if len(lines)>2 else []
        swap_total = int(swap_line[1]) if swap_line else 0
        swap_used = int(swap_line[2]) if swap_line else 0
        
        pct = int(used * 20 / total)
        print(f"  RAM Thật: [{'█' * pct}{'░' * (20-pct)}] {used}MB / {total}MB")
        if swap_total > 0:
            print(f"  RAM Ảo (Swap): {swap_used}MB / {swap_total}MB")
        
        suggest = max(min(avail - 150, 1024), 256)
        p_info(f"Gợi ý an toàn cho máy này: {suggest}MB")
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
        if os.system("command -v su > /dev/null") != 0:
            p_err("Máy bạn chưa ROOT!"); return
        size_gb = input("Nhập dung lượng Swap (GB) [2]: ").strip() or "2"
        sw_file = os.path.join(HOME, "swapfile")
        p_info(f"Đang tạo {size_gb}GB Swap...")
        os.system(f"su -c 'swapoff {sw_file} 2>/dev/null; dd if=/dev/zero of={sw_file} bs=1M count={int(size_gb)*1024}; chmod 600 {sw_file}; mkswap {sw_file}; swapon {sw_file}'")
        p_ok("Đã kích hoạt RAM ảo thành công!")
    input("\nEnter...")

def toggle_lamp():
    p_h("QUẢN LÝ DỊCH VỤ LAMP")
    cfg = load_config()
    backend = cfg.get('lamp_backend', 'termux')
    print(f"  Chế độ hiện tại: {C.H}{backend.upper()}{C.E}")
    
    if backend == 'termux':
        db_on = is_db_running()
        web_on = is_port_open(cfg['web_port'])
    else:
        db_on = is_port_open(3306)
        web_on = is_port_open(8080)
        
    print(f"  MariaDB : {'[ON]' if db_on else '[OFF]'}")
    print(f"  Web     : {'[ON]' if web_on else '[OFF]'} (Port {8080 if backend == 'ksweb' else cfg['web_port']})")
    print("-" * 40)
    lan_ip = get_local_ip()
    print(f"{C.G}👉 THÔNG TIN ĐƯỜNG DẪN TRUY CẬP & QUẢN LÝ:{C.E}")
    if backend == 'termux':
        print(f"  * Web Đăng Ký: {C.G}http://{lan_ip}:8080/{C.E}")
        print(f"  * Quản lý SQL: Dùng App di động {C.CY}SQLin{C.E} hoặc phần mềm PC ({C.Y}HeidiSQL, Navicat{C.E})")
        print(f"    - Kết nối IP: {C.G}{lan_ip}{C.E} (hoặc {C.G}127.0.0.1{C.E}) | Port: {C.G}3306{C.E}")
        print(f"    - Username: {C.G}root{C.E} | Mật khẩu: {C.G}123456{C.E}")
    else:
        print(f"  * Web Đăng Ký: {C.G}http://{lan_ip}:8080/nso_web/{C.E}")
        print(f"  * Cách cài phpMyAdmin trên KSWEB:")
        print(f"    1. Mở app KSWEB -> Vuốt sang tab {C.CY}Tools{C.E} (Công cụ)")
        print(f"    2. Chạm dòng {C.CY}phpMyAdmin{C.E} -> Chọn OK để tải và tự cấu hình")
        print(f"    3. Quay lại tab STATUS -> Gạt tắt bật lại {C.CY}Lighttpd{C.E} để mở cổng 8001")
        print(f"  * phpMyAdmin Link: {C.G}http://{lan_ip}:8001{C.E} (hoặc {C.G}http://localhost:8001{C.E})")
        print(f"    - Username: {C.G}root{C.E} | Mật khẩu: {C.G}123456{C.E}")
        print(f"  * Quản lý SQL: Dùng App di động {C.CY}SQLin{C.E} hoặc PC client kết nối cổng {C.G}3306{C.E}")
    print("-" * 40)
    if backend == 'termux':
        print("[A] BẬT TẤT CẢ  [S] TẮT TẤT CẢ")
        print("[3] Chuyển đổi sang chế độ KSWEB")
    else:
        print(f"{C.CY}KSWEB được bật/tắt từ chính ứng dụng KSWEB.{C.E}")
        print("[3] Chuyển đổi sang chế độ Termux LAMP")
    print("[0] Quay lại")
    ch=input("\nChọn: ").lower()
    
    if ch == '3':
        if backend == 'termux':
            p_info("Đang gỡ/tắt Termux LAMP và chuyển sang KSWEB...")
            os.system("killall -9 nginx php-fpm mariadbd mariadbd-safe 2>/dev/null")
            os.system("pkill -9 -f mariadbd; pkill -9 -f nginx; pkill -9 -f php-fpm > /dev/null 2>&1")
            cfg['lamp_backend'] = 'ksweb'
            save_config(cfg)
            setup_ksweb()
        else:
            p_info("Đang chuyển sang Termux LAMP...")
            cfg['lamp_backend'] = 'termux'
            save_config(cfg)
            p_ok("Đã chuyển mode! Hãy vào [Cài đặt môi trường] để cài lại Termux LAMP nếu cần.")
            input("\nEnter...")
        return

    if ch=='a':
        os.system("pkill -9 -f mariadbd; pkill -9 -f nginx; pkill -9 -f php-fpm > /dev/null 2>&1")
        os.system(f"rm -f {SOCKET} {TMP}/mysqld.sock")
        # Bật MariaDB kèm mở cổng 3306
        os.system(f"mariadbd-safe --socket={SOCKET} --port=3306 --bind-address=127.0.0.1 > /dev/null 2>&1 &")
        os.system("php-fpm; nginx")
        # Chờ và link socket thông minh
        time.sleep(2)
        if os.path.exists(SOCKET):
            os.system(f"ln -sf {SOCKET} {TMP}/mysqld.sock")
        p_ok("Đã bật LAMP (Cơ chế Universal).")
    elif ch=='s':
        p_info("Đang tiêu diệt tận gốc các dịch vụ...")
        os.system("pkill -9 -f mariadbd > /dev/null 2>&1")
        os.system("pkill -9 -f nginx > /dev/null 2>&1")
        os.system("pkill -9 -f php-fpm > /dev/null 2>&1")
        os.system(f"rm -f {SOCKET} {TMP}/mysqld.sock")
        p_ok("Đã tắt sạch các dịch vụ (Cơ chế Full-Match Kill).")
    input("\nEnter...")

def _make_run_script(cfg):
    script=os.path.join(HOME,"run_server.sh")
    jar=os.path.join(HOME,"target","Nso-jar-with-dependencies.jar")
    xmx = cfg.get('jvm_xmx', '512m')
    with open(script,"w") as f:
        f.write(f"#!/bin/bash\ncd {HOME}\nexec java -Djava.awt.headless=true -Xmx{xmx} -jar {jar}\n")
    os.chmod(script,0o755)
    return script

def toggle_server(cfg):
    p_h("QUẢN LÝ GAME SERVER")
    jar=os.path.join(HOME,"target","Nso-jar-with-dependencies.jar")
    is_on=is_port_open(cfg['tcp_port']) or is_java_running()
    if is_on:
        p_ok("Server ĐANG CHẠY.")
        print("[1] Tắt Server  [2] Xem Console (Tmux)  [0] Quay lại")
        ch=input("\nChọn: ")
        if ch=="1":
            os.system("pkill -9 java; tmux kill-session -t nso_game 2>/dev/null"); p_ok("Đã tắt.")
        elif ch=="2":
            if os.system("tmux has-session -t nso_game 2>/dev/null")==0:
                os.system("tmux attach -t nso_game")
            else: p_err("Không có session tmux.")
    else:
        p_err("Server ĐANG TẮT.")
        print("[1] Bật ngầm (Tmux)  [2] Bật trực tiếp  [0] Quay lại")
        ch=input("\nChọn: ")
        if ch in ["1","2"]:
            if not os.path.exists(jar): p_err("Chưa có JAR! Build trước."); input(); return
            os.system("pkill -9 java 2>/dev/null; tmux kill-session -t nso_game 2>/dev/null")
            time.sleep(1)
            script=_make_run_script(cfg)
            if ch=="1":
                os.system(f"tmux new-session -d -s nso_game '{script}'")
                p_ok("Server khởi động ngầm (tmux: nso_game).")
                p_info("Đợi 15s rồi kiểm tra [8].")
            else:
                p_info("Ctrl+C để dừng."); os.system(script)
    input("\nEnter...")

def check_status(cfg):
    p_h("TRẠNG THÁI HỆ THỐNG")
    items = [
        ("MariaDB Database", is_db_running()),
        ("Web Registration", is_port_open(cfg['web_port'])),
        ("NSO Game Server", is_port_open(cfg['tcp_port'])),
        ("Web Admin Bridge", is_port_open(9999))
    ]
    for label, ok in items:
        s = f"{C.G}Đang chạy{C.E}" if ok else f"{C.R}Đã dừng{C.E}"
        print(f"  {label.ljust(22)}: {s}")
    if is_java_running() and not is_port_open(cfg['tcp_port']):
        p_info("Java đang chạy nhưng chưa mở cổng (đang khởi động?).")
    input("\nEnter...")

def package_portable(cfg):
    p_h("ĐÓNG GÓI PORTABLE")
    out=os.path.join(HOME,"nso_portable.tar.gz")
    exc="--exclude='target' --exclude='*.log' --exclude='nso_config.json' --exclude='.git' --exclude='run_server.sh'"
    # Đóng gói toàn bộ thư mục HOME (trừ các file tạm)
    dirs = "src SQL Data item_roi nso_web config.properties pom.xml nso.py"
    existing = " ".join([d for d in dirs.split() if os.path.exists(os.path.join(HOME, d))])
    cmd = f"cd {HOME} && tar czf {out} {exc} {existing}"
    if os.system(cmd)==0:
        sz=os.path.getsize(out)/(1024*1024)
        p_ok(f"Đóng gói xong! ({sz:.1f} MB)")
        print(f"  File: {C.Y}{out}{C.E}")
        print(f"\n  {C.BOLD}Chia sẻ:{C.E}")
        print(f"  {C.G}cp {out} /sdcard/{C.E}")
        print(f"  Gửi qua Zalo/Drive, người nhận chạy:")
        print(f"  {C.CY}pkg install python -y && wget <URL>/nso.py && python nso.py{C.E}")
    else: p_err("Đóng gói thất bại!")
    input("\nEnter...")

# ==========================================
# VÁ CLIENT JAR
# ==========================================
def patch_jar_menu():
    p_h("VÁ CLIENT (.JAR)")
    dl_path = "/sdcard/Download"
    if not os.path.exists(dl_path): 
        p_err("Không tìm thấy thư mục Download!")
        return
    
    jars = [f for f in os.listdir(dl_path) if f.endswith(".jar")]
    if not jars:
        p_err("Không có file .jar nào trong Download.")
        return
    
    print("Danh sách file:")
    for i, f in enumerate(jars): print(f" [{i+1}] {f}")
    print(" [0] Quay lại")
    
    sel = input("\nChọn file: ")
    if sel == "0" or not sel.isdigit(): return
    
    jar_name = jars[int(sel)-1]
    jar_path = os.path.join(dl_path, jar_name)
    
    new_host = input(f"Nhập IP/Domain mới (mặc định localhost): ") or "127.0.0.1"
    new_port = input(f"Nhập Port mới (mặc định 14444): ") or "14444"
    
    p_info("Đang vá... vui lòng đợi...")
    tmp_dir = os.path.join(HOME, "tmp_jar")
    os.system(f"rm -rf {tmp_dir} && mkdir -p {tmp_dir}")
    
    import zipfile
    try:
        with zipfile.ZipFile(jar_path, 'r') as zip_ref:
            zip_ref.extractall(tmp_dir)
            
        count = 0
        for root, dirs, files in os.walk(tmp_dir):
            for file in files:
                if file.endswith(".class"):
                    fpath = os.path.join(root, file)
                    with open(fpath, 'rb') as f: data = f.read()
                    
                    # Tìm và vá các định dạng thường gặp
                    # 1. socket://127.0.0.1:14444
                    # 2. Local:127.0.0.1:14444:0:0
                    # Chúng ta sẽ tìm theo chuỗi con để linh hoạt
                    
                    # Vá cả IP và Port cùng lúc để tránh lỗi lệch offset
                    new_data = patch_binary_string(data, "127.0.0.1", new_host)
                    new_data = patch_binary_string(new_data, "14444", new_port)
                    
                    if new_data != data:
                        with open(fpath, 'wb') as f: f.write(new_data)
                        count += 1
        
        # Đóng gói lại
        custom_name = input(f"\nNhập tên file mới (mặc định {jar_name.replace('.jar', '_PATCHED')}): ")
        if custom_name:
            if not custom_name.endswith(".jar"): custom_name += ".jar"
            out_name = custom_name
        else:
            out_name = jar_name.replace(".jar", "_PATCHED.jar")
            
        # Thử lưu vào Download, nếu lỗi thì lưu vào HOME
        out_path = os.path.join(dl_path, out_name)
        try:
            # Kiểm tra quyền ghi bằng cách tạo file tạm
            test_f = os.path.join(dl_path, ".test_write")
            with open(test_f, "w") as f: f.write("test")
            os.remove(test_f)
        except:
            p_info("Không có quyền ghi vào /sdcard/Download. Chuyển sang lưu tại HOME.")
            out_path = os.path.join(HOME, out_name)
        
        with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
            for root, dirs, files in os.walk(tmp_dir):
                for file in files:
                    full_p = os.path.join(root, file)
                    rel_p = os.path.relpath(full_p, tmp_dir)
                    zip_out.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), tmp_dir))
        p_ok(f"Đã vá xong {count} file class!"); print(f"File lưu tại: {C.G}{out_path}{C.E}")
    except Exception as e: p_err(f"Lỗi: {e}")
    finally: os.system(f"rm -rf {tmp_dir}")
    input("\nEnter...")

def manage_web_download():
    """Đưa bản vá lên web để người chơi tải về"""
    p_h("QUẢN LÝ LINK TẢI GAME")
    
    # Quét ở 2 nơi: HOME và /sdcard/Download
    scan_dirs = [HOME, "/sdcard/Download"]
    all_jars = []
    
    for d in scan_dirs:
        if os.path.exists(d):
            for f in os.listdir(d):
                if f.endswith(".jar"):
                    all_jars.append(os.path.join(d, f))
                    
    if not all_jars:
        p_err("Không có file .jar nào trong HOME hoặc /sdcard/Download!")
        return
    
    print("Danh sách file .jar tìm thấy:")
    for i, p in enumerate(all_jars):
        folder = "DOWNLOAD" if "/sdcard/Download" in p else "HOME"
        fname = os.path.basename(p)
        print(f" [{i+1}] [{folder}] {fname}")
    print(" [0] Quay lại")
    
    sel = input("\nChọn file muốn đưa lên Web: ")
    if sel == "0" or not sel.isdigit(): return
    
    src_path = all_jars[int(sel)-1]
    jar_name = os.path.basename(src_path)
    web_dir = os.path.join(HOME, "nso_web")
    dest_path = os.path.join(web_dir, "nso_game.jar")
    
    if not os.path.exists(web_dir):
        p_err("Thư mục web không tồn tại!")
        return
        
    p_info(f"Đang đưa {jar_name} lên Web...")
    import shutil
    try:
        shutil.copy2(src_path, dest_path)
        p_ok("Đã cập nhật link tải game thành công!")
        p_info(f"Người chơi có thể tải tại: [Web URL]/nso_game.jar")
    except Exception as e:
        p_err(f"Lỗi: {e}")
    input("\nEnter...")

def get_public_web_url():
    cf_log = f"{TMP}/cf.log"
    if os.path.exists(cf_log) and os.system("tmux has-session -t nso_cf > /dev/null 2>&1") == 0:
        try:
            with open(cf_log, "r") as f:
                content = f.read()
                match = re.search(r"https://[A-Za-z0-9-]+\.trycloudflare\.com", content)
                if match: return match.group(0)
        except: pass
        
    import urllib.request
    for port in [4040, 4041]:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/tunnels", timeout=1) as r:
                tunnels = json.loads(r.read().decode()).get('tunnels', [])
                for t in tunnels:
                    if t.get('proto') in ['https', 'http']:
                        return t.get('public_url')
        except: pass
    return None

def main():
    cfg=load_config()
    while True:
        if not is_installed():
            if not first_time_setup(): break
            continue
        os.system("clear")
        backend = cfg.get('lamp_backend', 'termux')
        # Kiểm tra trạng thái phù hợp với từng backend
        if backend == 'ksweb':
            db_ok = is_port_open(3306)
            web_ok = is_port_open(8080)
            web_port_display = 8080
        else:
            db_ok = is_db_running()
            web_ok = is_port_open(cfg['web_port'])
            web_port_display = cfg['web_port']
        db_st  = f"{C.G}ON{C.E}"  if db_ok  else f"{C.R}OFF{C.E}"
        web_st = f"{C.G}ON{C.E}"  if web_ok  else f"{C.R}OFF{C.E}"
        game_st = f"{C.G}ON{C.E}" if is_port_open(cfg['tcp_port']) else f"{C.R}OFF{C.E}"
        backend_str = f"{C.CY}[KSWEB]{C.E}" if backend == 'ksweb' else f"{C.Y}[LAMP]{C.E}"
        web_link = get_public_web_url()
        if web_link and backend == 'ksweb':
            if not web_link.endswith('/nso_web/'):
                web_link = web_link.rstrip('/') + '/nso_web/'
        link_str = f" LINK WEB: {C.CY}{web_link}{C.E}\n" if web_link else ""
        print(f"""{C.CY}{C.BOLD}
==========================================
      NSO PRO MANAGER - Exe_Z Terminal
========================================={C.E}
 {C.G}tôi tạo ra app này để mod những game này thành game pvp 
 hoặc các chế độ khác tương tự mà không cần cày quốc 
 ae ai có chung ý tưởng nhớ share cho mọi người để 
 chúng ta cùng vui vẻ nhé{C.E}
------------------------------------------
 IP LAN: {C.G}{get_local_ip()}{C.E} | TCP: {C.Y}{cfg.get('tcp_domain', '127.0.0.1')}:{cfg.get('tcp_port', 14444)}{C.E}
 RAM: {get_ram_bar()}
 DB: {db_st} | WEB: {web_st}:{web_port_display} | GAME: {game_st} | {backend_str}
{link_str}------------------------------------------
 [1] THIẾT LẬP MÔI TRƯỜNG VẠN NĂNG (MỚI)
 [2] THIẾT LẬP DATABASE & WEB
 [3] CẤU HÌNH KẾT NỐI (IP/Tunnel)
 [4] VÁ IP & BUILD SERVER
 [5] BẬT / TẮT LAMP
 [6] BẬT / TẮT GAME SERVER
 [7] QUẢN LÝ TÀI KHOẢN
 [8] KIỂM TRA TRẠNG THÁI
 [9] ĐÓNG GÓI PORTABLE
 [10] VÁ CLIENT (.JAR)
 [11] ĐƯA GAME LÊN WEB
 [12] CẤU HÌNH RAM JVM
 [L] TẢI SRC & APK (Link Google Drive)
 [0] THOÁT
------------------------------------------""")
        ch=input(f"{C.BOLD}Lựa chọn: {C.E}")
        if ch=="1": install_env_fresh()
        elif ch=="2":
            if backend == 'ksweb': setup_ksweb()
            else: full_setup()
        elif ch=="3": manage_tcp(cfg)
        elif ch=="4":
            patch_source_code()
            prop=os.path.join(HOME,"config.properties")
            if os.path.exists(prop):
                with open(prop,'r',encoding='utf-8') as f: t=f.read()
                t=re.sub(r'db\.host=.*','db.host=127.0.0.1',t)
                t=re.sub(r'server\.port=.*',f'server.port={cfg["tcp_port"]}',t)
                with open(prop,'w',encoding='utf-8') as f: f.write(t)
                p_ok("Đã vá config.properties!")
            subprocess.run(["mvn","clean","package","-DskipTests"],cwd=HOME)
            input("\nEnter...")
        elif ch=="5": toggle_lamp()
        elif ch=="6": toggle_server(cfg)
        elif ch=="7": manage_account()
        elif ch=="8": check_status(cfg)
        elif ch=="9": package_portable(cfg)
        elif ch=="10": patch_jar_menu()
        elif ch=="11": manage_web_download()
        elif ch=="12": config_ram(cfg)
        elif ch.lower() == 'l':
            p_h("TẢI SRC & APK")
            print(f"""
{C.CY}📥 Link tải SRC (mã nguồn server):{C.E}
  {C.G}https://drive.google.com/file/d/1OS85oyU63x8BPL9vfbZp0C2B7I5xpmPc/view?usp=sharing{C.E}

{C.Y}Hướng dẫn: Copy link phía trên và dán vào trình duyệt trên máy tính hoặc điện thoại để tải về .{C.E}
""")
            input("\nNhấn Enter để quay lại...")
        elif ch=="0": break
        time.sleep(0.1)

if __name__=="__main__": main()
