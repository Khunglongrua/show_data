
import requests
import json

TOKEN = '6832278362:AAGrNR3SXo2tavGw-9LtX_fG9Dqf2G6icVc'
url = f'https://api.telegram.org/bot{TOKEN}/getUpdates'

response = requests.get(url).json()

# In toàn bộ dữ liệu trả về để kiểm tra
print(json.dumps(response, indent=4, ensure_ascii=False))
