import subprocess

def getWifiAps():
    result = subprocess.check_output('sudo iwlist wlan0 scan|grep SSID', shell=True).decode("utf-8") 
    result = result.split("\n")
    result = [x.strip() for x in result]
    result = [x[x.find("ESSID:")+7:-1] for x in result]
    return(result)

