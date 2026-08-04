import os
import sys
import urllib.request

# URL chứa nội dung file thô (raw) trên GitHub của bạn
# Chú ý: Thay 'main' bằng 'master' nếu branch mặc định của bạn là master
BASE_URL = "https://raw.githubusercontent.com/acevnpro/nro_termux/main/"

# Danh sách các phiên bản cấu hình
VERSIONS = {
    "1": {"name": "Phiên bản nro.py (Gốc)", "file": "nro.py"},
    "2": {"name": "Phiên bản nro3.py", "file": "nro3.py"},
    "3": {"name": "Phiên bản nro4.py", "file": "nro4.py"},
}

def download_and_replace(selected_file):
    url = BASE_URL + selected_file
    current_script = os.path.realpath(__file__) # Đường dẫn tới chính vnpro.py

    print(f"\n[*] Đang tải {selected_file} từ GitHub...")
    try:
        # Tải nội dung từ GitHub
        with urllib.request.urlopen(url) as response:
            content = response.read().decode('utf-8')
        
        # Ghi đè vào file vnpro.py hiện tại
        with open(current_script, "w", encoding="utf-8") as f:
            f.write(content)
            
        print(f"[✓] Cập nhật thành công! {current_script} đã được thay thế bằng {selected_file}.\n")
        
        # Khởi chạy lại script ngay lập tức bằng phiên bản mới đã ghi đè
        os.execv(sys.executable, [sys.executable] + sys.argv)

    except Exception as e:
        print(f"[X] Lỗi trong quá trình tải hoặc cập nhật: {e}")

def main():
    print("==========================================")
    print("      LỰA CHỌN PHIÊN BẢN NRO TERMUX       ")
    print("==========================================")
    for key, val in VERSIONS.items():
        print(f"[{key}] {val['name']}")
    print("[0] Thát")
    print("==========================================")

    choice = input("Nhập lựa chọn của bạn (1/2/3): ").strip()

    if choice in VERSIONS:
        download_and_replace(VERSIONS[choice]["file"])
    elif choice == "0":
        print("Đã thoát.")
        sys.exit()
    else:
        print("Lựa chọn không hợp lệ!")

if __name__ == "__main__":
    main()
