import os
import sys
import urllib.request

# ------------------------------------------------------------------------------
# 1. CẤU HÌNH HỆ THỐNG GITHUB
# ------------------------------------------------------------------------------
BASE_URL = "https://raw.githubusercontent.com/acevnpro/rsv_termux/main/"

# Link APK dùng chung cho nhiều bản (để tiện đổi 1 lần áp dụng cho tất cả)
DEFAULT_APK = "https://drive.google.com/file/d/1K1bwBRhiyNLfEMuOo2Yujs2CGe9yMIip/view?usp=sharing"

# ------------------------------------------------------------------------------
# 2. KHAI BÁO DANH SÁCH PHIÊN BẢN (DỄ DÀNG NHÂN BẢN & SỬA LINK)
# ------------------------------------------------------------------------------
# Mẹo: Để thêm bản mới, bạn chỉ cần copy 1 dòng add_version(...) bên dưới!
# Cú pháp: add_version(ID, "Tên hiển thị", "Tên_File.py", "Link_SRC", "Link_APK")

VERSION_LIST = []

def add_ver(id_key, name, file_name, src_link, apk_link=DEFAULT_APK):
    """Hàm bổ trợ giúp thêm phiên bản nhanh chóng"""
    VERSION_LIST.append({
        "id": str(id_key),
        "name": name,
        "file": file_name,
        "drive_src": src_link,
        "drive_apk": apk_link
    })

# --- DANH SÁCH CÁC PHIÊN BẢN (CHỈNH SỬA TẠI ĐÂY) ---
add_ver(1, "nro1.py (bản free của Tuấn TM)", "nro1.py", 
        "https://drive.google.com/file/d/1llh3f5vyu_xksMGZIXsu1cr0axTuUbM1/view?usp=sharing", 
        "https://drive.google.com/file/d/1lRH7I86uUlqf3MBtfv8aWwo88Y-ucQrP/view?usp=sharing")

add_ver(2, "nro2.py (đang lỗi nhiệm vụ)", "nro2.py", 
        "https://drive.google.com/file/d/1wJzyRhii-rw25482R9gOS20ItqXEs9gQ/view?usp=sharing")

add_ver(3, "nro3.py (dùng ok hơi cũ)", "nro3.py", 
        "https://drive.google.com/file/d/1xGDGjNTqZHv9e-i1DOw_4wRiRyQp081M/view")

add_ver(4, "nro4.py (dùng ok mới nhất)", "nro4.py", 
        "https://drive.google.com/file/d/1kahsNgga4pH0gzFlMtAbvf45Np82Ex1I/view")

add_ver(5, "nro5.py (lỗi kén client)", "nro5.py", 
        "https://drive.google.com/file/d/1u8RRcE-zI1LBd4QcudtjyuYUTxpD5qfP/view?usp=sharing")

add_ver(6, "nso.py ( bản ninja school không có apk - giải nén zip lấy jar)", "nso.py", 
        "https://drive.google.com/drive/folders/THAY_LINK_DRIVE_SRC_BAN_6", 
        "Không có APK (Chỉ có JAR trong ZIP)")

add_ver(7, "nro4.py (bản mod cắt giảm nhiệm vụ - có thể lỗi)", "nro4.py", 
        "https://drive.google.com/file/d/1BA1aH1yxZFnq2h8xi98f18yOhR4r6nYu/view?usp=sharing")

# Ví dụ nhân bản bản 8: Chỉ cần bỏ comment dòng dưới và sửa thông tin
# add_ver(8, "nro6.py (bản thử nghiệm)", "nro6.py", "LINK_DRIVE_SRC_HERE")

# Chuyển đổi sang Dictionary để truy xuất nhanh
VERSIONS = {item["id"]: item for item in VERSION_LIST}

# ------------------------------------------------------------------------------
# 3. MÃ NGUỒN XỬ LÝ (KHÔNG CẦN CHỈNH SỬA PHẦN NÀY)
# ------------------------------------------------------------------------------
def display_drive_links(info):
    print("\n==========================================")
    print(f" LINK DRIVE CHO: {info['name'].upper()}")
    print("==========================================")
    print(f"📁 Link Drive SRC : {info['drive_src']}")
    print(f"📱 Link Drive APK : {info['drive_apk']}")
    print("==========================================")
    print("👉 Vui lòng copy đường link trên dán vào trình duyệt để tải SRC / APK.\n")

def download_and_replace(selected_key):
    info = VERSIONS[selected_key]
    selected_file = info["file"]
    
    display_drive_links(info)
    
    confirm = input("Bạn có muốn tải và cài đặt file Python phiên bản này không? (y/n): ").strip().lower()
    if confirm != 'y':
        print("[!] Đã hủy thao tác ghi đè file.")
        return

    url = BASE_URL + selected_file
    current_script = os.path.realpath(__file__)

    print(f"\n[*] Đang tải {selected_file} từ GitHub (acevnpro/rsv_termux)...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            content = response.read().decode('utf-8')
        
        with open(current_script, "w", encoding="utf-8") as f:
            f.write(content)
            
        print(f"[✓] Đã chuyển đổi thành công! 'rsv.py' đã được thay thế bằng '{selected_file}'.\n")
        os.execv(sys.executable, [sys.executable] + sys.argv)

    except Exception as e:
        print(f"[X] Lỗi trong quá trình tải hoặc cập nhật: {e}")

def main():
    while True:
        print("\n==========================================")
        print("     RSV TERMUX - RUN SERVER MANAGER      ")
        print("==========================================")
        for key, val in VERSIONS.items():
            print(f"[{key}] {val['name']}")
        print("[0] Thoát")
        print("==========================================")

        choice = input("Nhập lựa chọn phiên bản của bạn: ").strip()

        if choice in VERSIONS:
            download_and_replace(choice)
            break
        elif choice == "0":
            print("Đã thoát chương trình.")
            sys.exit()
        else:
            print("[X] Lựa chọn không hợp lệ, vui lòng thử lại!")

if __name__ == "__main__":
    main()
