import os
import sys
import json

sys.path.append("src")

from src.kv8000 import KV8000
from src.sim7080g import SIM7080G

host_ip = "192.168.0.10"
host_port = 8501

count_file_path = f"{os.path.dirname(__file__)}/storage/count.txt"

def main():
    sim7080g = SIM7080G(port='/dev/ttyAMA0', baudrate=115200, debug=True)
    sim7080g.set_apn("soracom.io")

    if not sim7080g.init():
        return

    sim7080g.set_network()
    sim7080g.check_network()

    endpoint = "http://funk.soracom.io"
    headers = {
        "Content-Type": "application/json"
    }

    # Actionテーブルから取得する
    params = {
        "table": "action",
        "action": "select",
        "query": "deviceId=eq.00000001&count=eq.1"
    }
    body = json.dumps({
        "body": json.dumps(params)
    })
    response = sim7080g.https_post(
        url=endpoint,
        headers=headers,
        body=body
    )

    response_body = json.loads(response.get("body", "{}"))
    print("Body:", response_body)

    for action in response_body.get("data", []):
        plantId = action.get("plantId")                
        sensorId = action.get("sensorId")
        count = action.get("count")
        command = action.get("command")

    # countを更新する
    os.makedirs(os.path.dirname(count_file_path), exist_ok=True)
    with open(count_file_path, "w") as file:
        file.write(str(count))

    # コマンドを送信する
    kv8000 = KV8000(host_ip, host_port)

    if kv8000.connect():
        response = kv8000.send_command(command)
        if response:
            value = kv8000.parse(response)

    print("Value:", value)
    
    # 接続を切断
    kv8000.disconnect()

    # Measureテーブルに挿入する
    data = {
        "sensorId": sensorId,
        "value": value,
        "plantId": plantId,
        "count": count
    }
    params = {
        "table": "measure",
        "action": "insert",
        "data": json.dumps(data)
    }
    body = json.dumps({
        "body": json.dumps(params)
    })
    response = sim7080g.https_post(
        url=endpoint,
        headers=headers,
        body=body
    )

    print("Response:", response)
    
    sim7080g.close()

if __name__ == "__main__":
    main()

