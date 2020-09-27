import requests
import json
from prometheus_client import Gauge
import prometheus_client
from requests.adapters import HTTPAdapter
import time
import configparser

config = configparser.ConfigParser()
config.read('config.ini')


password = config.get('config', 'PASSWORD')
route_ip = config.get('config', 'ROUTE_IP')
sleep_time = config.getint('config', 'SLEEP_TIME')
exporter_port = config.getint('config', 'EXPORTER_PORT')
max_retries = config.getint('config', 'MAX_RETRIES')
timeout = config.getint('config', 'TIMEOUT')


s = requests.Session()
s.mount('http://', HTTPAdapter(max_retries=max_retries))
s.mount('https://', HTTPAdapter(max_retries=max_retries))


def get_token():
    url = "http://" + route_ip + "/api/login"
    payload = {
        "password": password
    }
    headers = {
        'Content-Type': 'text/plain'
    }
    payload = json.dumps(payload)
    response = s.request("POST", url, headers=headers, data=payload,timeout=timeout)
    token = json.loads(response.text.encode('utf8'))['data']['token']
    return token


def get_status(token):
    url = "http://" + route_ip + "/api/api_wrapper"
    payload = {
        "payload": [
            {
                "method": "system.get_system_load"
            }
        ],
        "version": "1.0.0",
        "action": "call"
    }
    headers = {
        'X-Token': token,
        'Cookie': '__guid=133949070.1308984322575506200.1596668655520.2163; '
                  'monitor_count=31; d2admin-1.5.6-uuid=; '
                  'd2admin-1.5.6-token=' + token,
    }
    payload = json.dumps(payload)

    response = s.request("POST", url, headers=headers, data=payload,timeout=timeout)

    status = json.loads(response.text)
    cpu_load = status['result'][0]['data']['cpu']
    mem_load = status['result'][0]['data']['mem']
    up_time = status['debug_info']['rt_time_in']

    payload = {
        "payload": [
            {
                "method": "idc.get_all"
            }, {
                "method": "wan.ipstat.get_realspeed"
            }
        ],
        "version": "1.0.0",
        "action": "call"
    }
    payload = json.dumps(payload)
    headers = {
        'X-Token': token,
        'Cookie': '__guid=133949070.1308984322575506200.1596668655520.2163; '
                  'monitor_count=31; d2admin-1.5.6-uuid=; '
                  'd2admin-1.5.6-token=' + token,
    }
    response = s.request("POST", url, headers=headers, data=payload,timeout=timeout)
    status = json.loads(response.text)
    # 每个设备的数据
    device_list = []
    for i in status['result'][0]['data']['device_list']:
        device_uid = i['uid']
        device_conn_type = i['options']['conn_type']
        device_mac = i['options']['mac']
        for j in status['result'][1]['data']['details']:
            if device_mac == j['mac']:
                device_upload = j['upload']
                device_download = j['download']
                device_upload_speed = j['upload_speed']
                device_download_speed = j['download_speed']

        device_ip = i['options']['ip']
        device_name = i['options']['name']
        device_status = {
            "device_uid": device_uid,
            "device_upload": device_upload,
            "device_download": device_download,
            "device_upload_speed": device_upload_speed,
            "device_download_speed": device_download_speed,
            "device_conn_type": device_conn_type,
            "device_ip": device_ip,
            "device_name": device_name
        }
        device_list.append(device_status)
    # 路由器总的数据
    route_download = status['result'][1]['data']['total']['download']
    route_download_speed = status['result'][1]['data']['total']['download_speed']
    route_upload = status['result'][1]['data']['total']['upload']
    route_upload_speed = status['result'][1]['data']['total']['upload_speed']
    route_status = {
        "cpu_load": cpu_load,
        "mem_load": mem_load,
        "up_time": up_time,
        "route_download": route_download,
        "route_download_speed": route_download_speed,
        "route_upload": route_upload,
        "route_upload_speed": route_upload_speed,
        "device_list": device_list
    }
    return route_status


if __name__ == '__main__':
    prometheus_client.start_http_server(exporter_port)
    jdwifi_prom = Gauge("JD", "jdwifi status", ["jdwifi_status"])
    jdwifi_client_prom = Gauge("JDclient", "JDclient status",
                               ["device_name", "device_uid", "device_conn_type", "device_ip", "des"])
    print("server start at " + str(exporter_port))
    print("blog: www.bboy.app")
    while True:
        try:
            token = get_token()
            route_status = get_status(token)

            cpu_load = route_status['cpu_load']
            mem_load = route_status['mem_load']
            up_time = route_status['up_time']
            route_download = route_status['route_download']
            route_download_speed = route_status['route_download_speed']
            route_upload = route_status['route_upload']
            route_upload_speed = route_status['route_upload_speed']

            jdwifi_prom.labels("cpu_load").set(float(cpu_load))
            jdwifi_prom.labels("mem_load").set(float(mem_load))
            jdwifi_prom.labels("up_time").set(float(up_time))
            jdwifi_prom.labels("route_download").set(float(route_download))
            jdwifi_prom.labels("route_download_speed").set(float(route_download_speed))
            jdwifi_prom.labels("route_upload").set(float(route_upload))
            jdwifi_prom.labels("route_upload_speed").set(float(route_upload_speed))

            for i in route_status['device_list']:
                device_uid = i['device_uid']
                device_upload = i['device_upload']
                device_download = i['device_download']
                device_upload_speed = i['device_upload_speed']
                device_download_speed = i['device_download_speed']
                device_conn_type = i['device_conn_type']
                device_ip = i['device_ip']
                device_name = i['device_name']

                jdwifi_client_prom.labels(device_name=device_name, device_uid=device_uid,
                                          device_conn_type=device_conn_type, device_ip=device_ip,
                                          des="device_upload").set(
                    float(device_upload))
                jdwifi_client_prom.labels(device_name=device_name, device_uid=device_uid,
                                          device_conn_type=device_conn_type, device_ip=device_ip,
                                          des="device_download").set(
                    float(device_download))
                jdwifi_client_prom.labels(device_name=device_name, device_uid=device_uid,
                                          device_conn_type=device_conn_type, device_ip=device_ip,
                                          des="device_upload_speed").set(
                    float(device_upload_speed))
                jdwifi_client_prom.labels(device_name=device_name, device_uid=device_uid,
                                          device_conn_type=device_conn_type, device_ip=device_ip,
                                          des="device_download_speed").set(
                    float(device_download_speed))
        except Exception as e:
            print(e)
        time.sleep(sleep_time)
