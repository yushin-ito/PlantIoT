import os
import sys
import json
import time
import keyboard

sys.path.append("src")

from src.kv8000 import KV8000
from src.sim7080g import SIM7080G

device_id = "00000001"
host_ip = "192.168.0.10"
host_port = 8501
polling_interval = 20
max_polling_count = 10

count_file_path = f"{os.path.dirname(__file__)}/storage/count.txt"

def main():
    try:
        sim7080g = SIM7080G(port='/dev/ttyAMA0', baudrate=115200, debug=True)
        sim7080g.set_apn("soracom.io")

        if not sim7080g.init():
            raise Exception("Failed to initialize SIM7080G")

        sim7080g.set_network()
        sim7080g.check_network()

        endpoint = "http://funk.soracom.io"
        headers = {
            "Content-Type": "application/json"
        }

        # deviceテーブルを更新する
        data = {
            "active": True
        }
        params = {
            "table": "device",
            "action": "update",
            "condition": "deviceId=eq.00000001",
            "data": json.dumps(data)
        }
        request_body = json.dumps({
            "body": json.dumps(params)
        })
        response = sim7080g.https_post(
            url=endpoint,
            headers=headers,
            body=request_body
        )

        if(response.get("status") != 200):
            raise Exception("Failed to update device table")
        
        while True:
            if keyboard.read_event(): 
                break
            
            # actionテーブルから取得する
            params = {
                "table": "action",
                "action": "select",
                "query": "deviceId=eq.00000001&count=eq.1"
            }
            request_body = json.dumps({
                "body": json.dumps(params)
            })
            response = sim7080g.https_post(
                url=endpoint,
                headers=headers,
                body=request_body
            )

            if(response.get("status") != 200):
                raise Exception("Failed to select action table")

            response_body = json.loads(response.get("body"))

            for action in json.loads(response_body.get("data")):
                plant_id = action.get("plantId")
                control_id = action.get("controlId")                
                sensor_id = action.get("sensorId")
                count = action.get("count")
                command = action.get("command")

                if control_id:
                    # コマンドを送信する
                    kv8000 = KV8000(host_ip, host_port)

                    if kv8000.connect():
                        response = kv8000.send_command(command)
                    else:
                        raise Exception("Failed to connect to KV8000")
                    
                    # 接続を切断
                    kv8000.disconnect()
                        
                if sensor_id:
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
                    else: 
                        raise Exception("Failed to connect to KV8000")
                    
                    # 接続を切断
                    kv8000.disconnect()

                    # measureテーブルに挿入する
                    data = {
                        "sensorId": sensor_id,
                        "value": value,
                        "plantId": plant_id,
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

                    if(response.get("status") != 200):
                        raise Exception("Failed to insert measure table")
                    
            time.sleep(polling_interval)
        
        # deviceテーブルを更新する
        data = {
            "active": False
        }
        params = {
            "table": "device",
            "action": "update",
            "condition": "deviceId=eq.00000001",
            "data": json.dumps(data)
        }
        
        sim7080g.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()  

