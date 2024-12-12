import serial
import time

class SIM7080G:
    def __init__(self, port='/dev/ttyAMA0', baudrate=115200, debug=False):
        self.time = time
        self.port = port
        self.baudrate = baudrate
        self.modem = serial.Serial(self.port, self.baudrate)
        self.modem.flushInput()
        self.debug = debug

    def set_apn(self, apn, username="", password=""):
        self.apn = apn
        self.username = username
        self.password = password

    def send_at(self, command, back, timeout=1.5):
        rec_buff = ''
        self.modem.write((command + '\r\n').encode())
        self.time.sleep(timeout)
        if self.modem.inWaiting():
            self.time.sleep(0.1)
            rec_buff = self.modem.read(self.modem.inWaiting())
        if rec_buff != '':
            if back not in rec_buff.decode():
                print(command + ' ERROR')
                print(command + ' back:\t' + rec_buff.decode())
                return 0
            else:
                if self.debug:
                    print(rec_buff.decode())
                return 1
        else:
            print(command + ' no response')
            return 0

    def send_at_wait_resp(self, command, back, timeout=1.5):
        rec_buff = b''
        self.modem.write((command + '\r\n').encode())
        self.time.sleep(timeout)
        if self.modem.inWaiting():
            self.time.sleep(0.1)
            rec_buff = self.modem.read(self.modem.inWaiting())
        if rec_buff != '':
            if back not in rec_buff.decode():
                if self.debug:
                    print(command + ' ERROR')
                    print(command + ' back:\t' + rec_buff.decode())
                return rec_buff
            else:
                if self.debug:
                    print(rec_buff.decode())
                return rec_buff
        else:
            print(command + ' no response')
        return rec_buff
    
    def set_debug_level(self, level=2):
        if level not in [0, 1, 2]:
            print("Invalid level. Please use 0, 1, or 2.")
            return False
        return self.send_at(f"AT+CMEE={level}", "OK")

    def check_start(self):
        self.send_at("AT", "OK")
        self.time.sleep(1)
        for i in range(1, 4):
            if self.send_at("AT", "OK") == 1:
                print('------SIM7080G is ready------\r\n')
                self.send_at("ATE1", "OK")
                self.send_at("AT+GMR", "OK")
                return 1
            else:
                print('------SIM7080G is starting up, please wait------\r\n')
                self.time.sleep(5)
        return 0

    def set_network(self):
        print("Setting to LTE mode:\n")
        self.send_at("AT+CFUN=0", "OK")
        self.send_at("AT+CNMP=38", "OK")
        self.send_at("AT+CMNB=1", "OK")
        self.send_at("AT+CFUN=1", "OK")

    def check_network(self):
        if self.send_at("AT+CPIN?", "READY") != 1:
            print("------Please check whether the SIM card has been inserted!------\n")
        for i in range(1, 10):
            if self.send_at("AT+CGATT?", "1"):
                print('------SIM7080G is online------\r\n')
                break
            else:
                print('------SIM7080G is offline, please wait...------\r\n')
                self.time.sleep(5)
                continue
        self.send_at("AT+CSQ", "OK")
        self.send_at("AT+CPSI?", "OK")
        self.send_at("AT+COPS?", "OK")
        if self.username:
            self.send_at(f'AT+CNCFG=0,1,"{self.apn}","{self.username}","{self.password}"', "OK")
        else:
            self.send_at(f'AT+CNCFG=0,1,"{self.apn}"', "OK")
        if self.send_at('AT+CNACT=0,1', 'ACTIVE'):
            print("Network activation is successful\n")
        else:
            print("Please check the network and try again!\n")
        self.send_at('AT+CNACT?', 'OK')
    
    def set_http_headers(self, headers):
        for key, value in headers.items():
            self.send_at(f'AT+SHAHEAD="{key}","{value}"', 'OK')

    def set_http_length(self, bodylen=1024, headerlen=350):
        self.send_at(f'AT+SHCONF="BODYLEN",{bodylen}', 'OK')
        self.send_at(f'AT+SHCONF="HEADERLEN",{headerlen}', 'OK')

    def set_http_content(self):
        self.send_at('AT+SHCHEAD', 'OK')
        self.send_at('AT+SHAHEAD="Content-Type","application/json"', 'OK')

    def close(self):
        self.send_at('AT+SHDISC', 'OK')

    def http_get(self, url, headers={}):
            print("HTTP GET")
            self.send_at(f'AT+SHCONF="URL","{url}"', 'OK')
            self.set_http_length()
            self.send_at('AT+SHCONN', 'OK', 3)
            if headers:
                self.set_http_headers(headers)
            if self.send_at('AT+SHSTATE?', '1'):
                response = str(self.send_at_wait_resp(f'AT+SHREQ="{url}",1', 'OK', 8))
                try:
                    get_pack_len = int(response[response.rfind(',') + 1:-5])
                    if get_pack_len > 0:
                        response_data = self.send_at_wait_resp(f'AT+SHREAD=0,{get_pack_len}', 'OK', 5).decode()
                        print("Response: ", response_data)
                        return {
                            "code": 200,
                            "data": response_data
                        }
                    else:
                        print("HTTP GET failed!\n")
                        return {
                            "code": None,
                            "data": None
                        }
                except ValueError:
                    print("ValueError in HTTP GET response!\n")
                    return {
                        "code": None,
                        "data": None
                    }
            else:
                print("HTTP connection disconnected, please check and try again\n")
                return {
                    "code": None,
                    "data": None
                }
        
    def http_post(self, url, headers={}, data=None):
        print("HTTP POST")
        self.send_at(f'AT+SHCONF="URL","{url}"', 'OK')
        bodylen = len(data) if data else 0
        self.set_http_length(bodylen)
        self.send_at('AT+SHCONN', 'OK', 3)
        if headers:
            self.set_http_headers(headers)
        if self.send_at('AT+SHSTATE?', '1'):
            if data and self.send_at(f'AT+SHBOD={bodylen},10000', '>'):
                self.send_at(data, 'OK', 1)
            response = str(self.send_at_wait_resp(f'AT+SHREQ="{url}",3', 'OK', 8))
            try:
                post_status = int(response[response.rfind(',') - 3:response.rfind(',')])
                print(f"HTTP POST Status: {post_status}\n")

                get_pack_len = int(response[response.rfind(',') + 1:-5])
                if get_pack_len > 0:
                    response_data = self.send_at_wait_resp(f'AT+SHREAD=0,{get_pack_len}', 'OK', 5).decode()
                    print("Response: ", response_data)
                    return {
                        "code": post_status,
                        "data": response_data
                    }
                else:
                    print("No response data received.\n")
                    return {
                        "code": post_status,
                        "data": None
                    }
            except ValueError:
                print("ValueError in HTTP POST response!\n")
                return {
                    "code": None,
                    "data": None
                }
        else:
            print("HTTP connection disconnected, please check and try again\n")
            return {
                "code": None,
                "data": None
            }


    def https_get(self, url, headers={}):
        print("HTTPS GET")
        self.send_at('AT+CSSLCFG="ignorertctime",1,1', 'OK')
        self.send_at('AT+CSSLCFG="sslversion",1,3', 'OK')
        self.send_at('AT+SHSSL=1,""', 'OK')
        self.send_at(f'AT+SHCONF="URL","{url}"', 'OK')
        self.set_http_length()
        self.send_at('AT+SHCONN', 'OK', 5)
        if headers:
            self.set_http_headers(headers)
        if self.send_at('AT+SHSTATE?', '1'):
            response = str(self.send_at_wait_resp(f'AT+SHREQ="{url}",1', 'OK', 8))
            try:
                get_pack_len = int(response[response.rfind(',') + 1:-5])
                if get_pack_len > 0:
                    response_data = self.send_at_wait_resp(f'AT+SHREAD=0,{get_pack_len}', 'OK', 5).decode()
                    print("Response: ", response_data)
                    return {
                        "code": 200,
                        "data": response_data
                    }
                else:
                    print("HTTPS GET failed!\n")
                    return {
                        "code": None,
                        "data": None
                    }
            except ValueError:
                print("ValueError in HTTPS GET response!\n")
                return {
                    "code": None,
                    "data": None
                }
        else:
            print("HTTPS connection disconnected, please check and try again\n")
            return {
                "code": None,
                "data": None
            }

    def https_post(self, url, headers={}, data=None):
        print("HTTPS POST")
        self.send_at('AT+CSSLCFG="ignorertctime",1,1', 'OK')
        self.send_at('AT+CSSLCFG="sslversion",1,3', 'OK')
        self.send_at('AT+SHSSL=1,""', 'OK')
        self.send_at(f'AT+SHCONF="URL","{url}"', 'OK')
        bodylen = len(data) if data else 0
        self.set_http_length(bodylen)
        self.send_at('AT+SHCONN', 'OK', 5)
        if headers:
            self.set_http_headers(headers)
        if self.send_at('AT+SHSTATE?', '1'):
            if data and self.send_at(f'AT+SHBOD={bodylen},10000', '>'):
                self.send_at(data, 'OK', 1)
            response = str(self.send_at_wait_resp(f'AT+SHREQ="{url}",3', 'OK', 8))
            try:
                post_status = int(response[response.rfind(',') - 3:response.rfind(',')])
                print(f"HTTPS POST Status: {post_status}\n")

                get_pack_len = int(response[response.rfind(',') + 1:-5])
                if get_pack_len > 0:
                    response_data = self.send_at_wait_resp(f'AT+SHREAD=0,{get_pack_len}', 'OK', 5).decode()
                    print("Response: ", response_data)
                    return {
                        "code": post_status,
                        "data": response_data
                    }
                else:
                    print("No response data received.\n")
                    return {
                        "code": post_status,
                        "data": None
                    }
            except ValueError:
                print("ValueError in HTTPS POST response!\n")
                return {
                    "code": None,
                    "data": None
                }
        else:
            print("HTTPS connection disconnected, please check and try again\n")
            return {
                "code": None,
                "data": None
            }