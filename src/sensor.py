import socket

class Sensor:
    def __init__(self, host_ip, host_port):
        self.host_ip = host_ip
        self.host_port = host_port
        self.client = None

        self.cmd_map = {
            "waste_oil_tank_level": "DM5000",               # 廃油タンクレベル [L]
            "meoh_level": "DM5100",                         # メタノールタンクレベル [L]
            "waste_oil_heater_temp": "DM19400",             # 廃油ヒーター現在値 [°C]
            "waste_oil_pump_flow_setting": "DM100",         # 廃油ポンプ流量設定値 [L/H]
            "waste_oil_tank_upper_limit": "DM10414",        # 廃油タンク上限 [L]
            "meoh_level_upper_limit": "DM110",              # メタノールレベル上限 [L]
            "waste_oil_heater_setting": "DM10401",          # 廃油ヒーター設定値 [°C]
            "inline_heater_setting": "DM10415",             # インラインヒーター設定値 [°C]
            "waste_oil_pump_flow": "DM1000",                # 廃油ポンプ流量 [L/H]
            "meoh_pump_flow": "DM1100",                     # メタノールポンプ流量 [L/H]
            "auto_heating_pump_flow_setting": "DM10500",    # 廃油ポンプ流量設定値（自動加熱）[L/H]
            "auto_operation_inline_heater_temp": "DM2104",  # 自動運転インラインヒーター設定温度 [°C]
            "moisture_removal_timer": "DM124"               # 水分除去タイマー [分]
        }

    def connect(self):
        try:
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.connect((self.host_ip, self.host_port))
            print("PLC connection success")
            return True
        except Exception as e:
            print(f"PLC connection failed")
            return False

    def disconnect(self):
        if self.client:
            self.client.close()
            print("PLC connection closed")

    def read(self, name, length=1):
        address = self.cmd_map.get(name)
        if not address:
            print("Invalid sensor name")
            return None
        
        if not self.client:
            print("Not connected to PLC")
            return None
        
        try:
            command = f"RDS {address} {length}\r"
            self.client.send(command.encode("ascii"))

            response = self.client.recv(1024).decode("ascii").strip()
            return response
        except Exception as e:
            print(f"Failed to read DM: {e}")
            return None
        
    def parse(self, response):
        try:
            if len(response) == 5:
                return int(response[:3]) + int(response[3:]) / 100
            return int(response)
        except Exception as e:
            print(f"Failed to parse response: {e}")
            return None
