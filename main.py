import sys
import json

sys.path.append("src")

from src.sensor import Sensor
from src.sim7080g import SIM7080G

def main():
    '''
    host_ip = "192.168.0.10"
    host_port = 8501

    sensor = Sensor(host_ip, host_port)

    if sensor.connect():
        # 廃油タンクレベルを取得
        response = sensor.read("waste_oil_tank_level")
        if response:
            value = sensor.parse(response)
            print(f"廃油タンクレベル: {value} L")
        
        # 水分除去タイマーを取得
        response = sensor.read("moisture_removal_timer")
        if response:
            value = sensor.parse(response)
            print(f"水分除去タイマー: {value} 分")
    
    
    # 接続を切断
    sensor.disconnect()
    '''

    sim7080g = SIM7080G(port='/dev/ttyAMA0', baudrate=115200, debug=True)
    sim7080g.set_apn("soracom.io")

    if not sim7080g.check_start():
        print("Failed to initialize SIM7080G.")
        return

    sim7080g.set_network()
    sim7080g.check_network()

    endpoint = "http://funk.soracom.io"

    headers = {
        "Content-Type": "application/json"
    }

    data = {
        "table": "action",
        "action": "select",
        "query": "deviceId=eq.00000001&count=eq.1"
    }

    body = json.dumps({
        "body": json.dumps(data)
    })

    response = sim7080g.https_post(
        url=endpoint,
        headers=headers,
        body=body
    )

    print("Response:", response)

    data = {
        "table": "measure",
        "action": "insert",
        "query": "deviceId=eq.00000001&count=eq.1"
    }

    body = json.dumps({
        "body": json.dumps(data)
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

