import schedule
import time
import subprocess

# Cấu hình danh sách các file Python và thời gian lặp lại tương ứng (phút)
scripts = [
    {"file": "Breakout_Long2.py", "interval": 1},
    {"file": "Entry_Long2.py", "interval": 1},  # Ví dụ file khác với thời gian lặp 2 phút
 #   {"file": "find_inchimoku.py", "interval":60},
    {"file": "Cross_Drivers.py", "interval":1}

]

# Tạo từ điển để đếm số lần đã thực thi từng file
execution_count = {script['file']: 0 for script in scripts}

def run_script(file_to_run):
    print(f"Bot đang chạy {file_to_run}...")  # In ra trước khi thực thi
    try:
        # Thực thi file Python
        subprocess.run(["python", file_to_run])
        execution_count[file_to_run] += 1
        print(f"Đã thực thi {file_to_run} thành công! (Lần {execution_count[file_to_run]})")
    except Exception as e:
        print(f"Lỗi khi thực thi {file_to_run}: {e}")

# Đặt lịch chạy cho từng file với thời gian lặp lại riêng
for script in scripts:
    schedule.every(script["interval"]).minutes.do(run_script, script["file"])

print("Đang chờ để thực thi các script theo lịch trình. Nhấn Ctrl+C để dừng lại.")
while True:
    schedule.run_pending()
    time.sleep(1)
