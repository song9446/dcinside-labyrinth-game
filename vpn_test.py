import requests
from pprint import pprint
import subprocess, base64, os, sys, tempfile, time


def getVpngateServerList(country_keyword="Korea"):
    raw_data = requests.get('http://www.vpngate.net/api/iphone/').text
    lines = (i.split(',') for i in raw_data.splitlines())
    filtered = [i for i in lines if len(i)>1 and country_keyword in i[6 if len(country_keyword)==2 else 5]]
    #print([i[2] for i in filtered])
    #sorted = sorted(filtered, key=lambda i: float(i[2]), reverse=True)
    #print(best)
    return filtered
    
def startOpenvpn(config_data):
    _, temp_path = tempfile.mkstemp()
    with open(temp_path, 'w') as f:
        f.write(base64.b64decode(config_data))
        f.write('\nscript-security 2\nup /etc/openvpn/update-resolv-conf\ndown /etc/openvpn/update-resolv-conf')
    p = subprocess.Popen(['sudo', 'openvpn', '--config', temp_path])
    return p

def stopOpenvpn(p):
    try:
        p.kill()
    except:
        pass
    while p.poll() != 0:
        time.sleep(1)
    
startOpenvpn("Korea")
