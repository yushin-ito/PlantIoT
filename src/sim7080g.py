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

    def send_at_command(self, command, back, timeout=1.0):
        buffer = ''
        self.modem.write((command + '\r\n').encode())
        self.time.sleep(timeout)
        if self.modem.inWaiting():
            self.time.sleep(0.1)
            buffer = self.modem.read(self.modem.inWaiting())
        if buffer != '':
            if back not in buffer.decode():
                print(command + ' ERROR')
                print(command + ' back:\t' + buffer.decode())
                return 0
            else:
                if self.debug:
                    print(buffer.decode())
                return 1
        else:
            print(command + ' no response')
            return 0

    def send_at_command_and_wait_response(self, command, back, timeout=1.0):
        buffer = b''
        self.modem.write((command + '\r\n').encode())
        self.time.sleep(timeout)
        if self.modem.inWaiting():
            self.time.sleep(0.1)
            buffer = self.modem.read(self.modem.inWaiting())
        if buffer != '':
            if back not in buffer.decode():
                if self.debug:
                    print(command + ' ERROR')
                    print(command + ' back:\t' + buffer.decode())
                return buffer
            else:
                if self.debug:
                    print(buffer.decode())
                return buffer
        else:
            print(command + ' no response')
        return buffer
    
    def set_debug_level(self, level=2):
        if level not in [0, 1, 2]:
            print("Invalid level.")
            return False
        return self.send_at_command(f"AT+CMEE={level}", "OK")

    def init(self, retry=5):
        self.send_at_command("AT", "OK")
        self.time.sleep(1)
        for i in range(retry):
            if self.send_at_command("AT", "OK") == 1:
                print('SIM7080G is ready\r\n')
                self.send_at_command("ATE1", "OK")
                self.send_at_command("AT+GMR", "OK")
                return 1
            else:
                print('SIM7080G is not ready\r\n')
                self.time.sleep(5)
        return 0

    def set_network(self):
        self.send_at_command("AT+CFUN=0", "OK")
        self.send_at_command("AT+CNMP=38", "OK")
        self.send_at_command("AT+CMNB=1", "OK")
        self.send_at_command("AT+CFUN=1", "OK")

    def check_network(self):
        if self.send_at_command("AT+CPIN?", "READY") != 1:
            print("SIM7080G is not ready\r\n")
        for i in range(1, 10):
            if self.send_at_command("AT+CGATT?", "1"):
                print('SIM7080G is online\r\n')
                break
            else:
                print('SIM7080G is offline\r\n')
                self.time.sleep(5)
                continue
        self.send_at_command("AT+CSQ", "OK")
        self.send_at_command("AT+CPSI?", "OK")
        self.send_at_command("AT+COPS?", "OK")
        if self.username:
            self.send_at_command(f'AT+CNCFG=0,1,"{self.apn}","{self.username}","{self.password}"', "OK")
        else:
            self.send_at_command(f'AT+CNCFG=0,1,"{self.apn}"', "OK")
        if self.send_at_command('AT+CNACT=0,1', 'ACTIVE'):
            print("Network is ready\r\n")
        else:
            print("Network is not ready\r\n")
        self.send_at_command('AT+CNACT?', 'OK')
    
    def set_http_headers(self, headers):
        for key, value in headers.items():
            self.send_at_command(f'AT+SHAHEAD="{key}","{value}"', 'OK')

    def set_http_length(self, bodylen=1024, headerlen=350):
        self.send_at_command(f'AT+SHCONF="BODYLEN",{bodylen}', 'OK')
        self.send_at_command(f'AT+SHCONF="HEADERLEN",{headerlen}', 'OK')

    def set_http_content(self):
        self.send_at_command('AT+SHCHEAD', 'OK')
        self.send_at_command('AT+SHAHEAD="Content-Type","application/json"', 'OK')

    def close(self):
        self.send_at_command('AT+SHDISC', 'OK')

    def http_get(self, url, headers={}):
        self.send_at_command(f'AT+SHCONF="URL","{url}"', 'OK')
        self.set_http_length()
        self.send_at_command('AT+SHCONN', 'OK', 3)
        if headers:
            self.set_http_headers(headers)
        if self.send_at_command('AT+SHSTATE?', '1'):
            response = str(self.send_at_command_and_wait_response(f'AT+SHREQ="{url}",1', 'OK', 8))
            try:
                status_code = int(response[response.rfind(',') - 3:response.rfind(',')])
                print(f"Code: {status_code}")

                packet_length = int(response[response.rfind(',') + 1:-5])
                if packet_length > 0:
                    response_data = self.send_at_command_and_wait_response(f'AT+SHREAD=0,{packet_length}', 'OK', 5).decode()
                    print("Response: ", response_data)
                    return {
                        "code": 200,
                        "data": response_data
                    }
                else:
                    print("No response received\r\n")
                    return {
                        "code": None,
                        "data": None
                    }
            except ValueError:
                print("ValueError in HTTP GET\r\n")
                return {
                    "code": None,
                    "data": None
                }
        else:
            print("HTTP connection disconnected\r\n")
            return {
                "code": None,
                "data": None
            }
        
    def http_post(self, url, headers={}, body=None):
        print("HTTP POST")
        self.send_at_command(f'AT+SHCONF="URL","{url}"', 'OK')
        bodylen = len(body) if body else 0
        self.set_http_length(bodylen)
        self.send_at_command('AT+SHCONN', 'OK', 3)
        if headers:
            self.set_http_headers(headers)
        if self.send_at_command('AT+SHSTATE?', '1'):
            if body and self.send_at_command(f'AT+SHBOD={bodylen},10000', '>'):
                self.send_at_command(body, 'OK', 1)
            response = str(self.send_at_command_and_wait_response(f'AT+SHREQ="{url}",3', 'OK', 8))
            try:
                status_code = int(response[response.rfind(',') - 3:response.rfind(',')])
                print(f"Code: {status_code}")

                packet_length = int(response[response.rfind(',') + 1:-5])
                if packet_length > 0:
                    response_data = self.send_at_command_and_wait_response(f'AT+SHREAD=0,{packet_length}', 'OK', 5).decode()
                    print("Response: ", response_data)
                    return {
                        "code": status_code,
                        "data": response_data
                    }
                else:
                    print("No response received\r\n")
                    return {
                        "code": status_code,
                        "data": None
                    }
            except ValueError:
                print("ValueError in HTTP POST\r\n")
                return {
                    "code": None,
                    "data": None
                }
        else:
            print("HTTP connection disconnected\r\n")
            return {
                "code": None,
                "data": None
            }


    def https_get(self, url, headers={}):
        print("HTTPS GET")
        self.send_at_command('AT+CSSLCFG="ignorertctime",1,1', 'OK')
        self.send_at_command('AT+CSSLCFG="sslversion",1,3', 'OK')
        self.send_at_command('AT+SHSSL=1,""', 'OK')
        self.send_at_command(f'AT+SHCONF="URL","{url}"', 'OK')
        self.set_http_length()
        self.send_at_command('AT+SHCONN', 'OK', 5)
        if headers:
            self.set_http_headers(headers)
        if self.send_at_command('AT+SHSTATE?', '1'):
            response = str(self.send_at_command_and_wait_response(f'AT+SHREQ="{url}",1', 'OK', 8))
            try:
                status_code = int(response[response.rfind(',') - 3:response.rfind(',')])
                print(f"Code: {status_code}")

                packet_length = int(response[response.rfind(',') + 1:-5])
                if packet_length > 0:
                    response_data = self.send_at_command_and_wait_response(f'AT+SHREAD=0,{packet_length}', 'OK', 5).decode()
                    print("Response: ", response_data)
                    return {
                        "code": 200,
                        "data": response_data
                    }
                else:
                    print("No response received\r\n")
                    return {
                        "code": None,
                        "data": None
                    }
            except ValueError:
                print("ValueError in HTTPS GET\r\n")
                return {
                    "code": None,
                    "data": None
                }
        else:
            print("HTTPS connection disconnected\r\n")
            return {
                "code": None,
                "data": None
            }

    def https_post(self, url, headers={}, body=None):
        print("HTTPS POST")
        self.send_at_command('AT+CSSLCFG="ignorertctime",1,1', 'OK')
        self.send_at_command('AT+CSSLCFG="sslversion",1,3', 'OK')
        self.send_at_command('AT+SHSSL=1,""', 'OK')
        self.send_at_command(f'AT+SHCONF="URL","{url}"', 'OK')
        bodylen = len(body) if body else 0
        self.set_http_length(bodylen)
        self.send_at_command('AT+SHCONN', 'OK', 5)
        if headers:
            self.set_http_headers(headers)
        if self.send_at_command('AT+SHSTATE?', '1'):
            if body and self.send_at_command(f'AT+SHBOD={bodylen},10000', '>'):
                self.send_at_command(body, 'OK', 1)
            response = str(self.send_at_command_and_wait_response(f'AT+SHREQ="{url}",3', 'OK', 8))
            try:
                status_code = int(response[response.rfind(',') - 3:response.rfind(',')])
                print(f"Code: {status_code}")

                packet_length = int(response[response.rfind(',') + 1:-5])
                if packet_length > 0:
                    response_data = self.send_at_command_and_wait_response(f'AT+SHREAD=0,{packet_length}', 'OK', 5).decode()
                    print("Response: ", response_data)
                    return {
                        "code": status_code,
                        "data": response_data
                    }
                else:
                    print("No response received\r\n")
                    return {
                        "code": status_code,
                        "data": None
                    }
            except ValueError:
                print("ValueError in HTTPS POST\r\n")
                return {
                    "code": None,
                    "data": None
                }
        else:
            print("HTTPS connection disconnected\r\n")
            return {
                "code": None,
                "data": None
            }