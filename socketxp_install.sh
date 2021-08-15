#!/bin/bash
#-------------------------------------------------
#  SocketXP IoT Agent Installation Script
#-------------------------------------------------

printUsage() {
    echo "Usage: "
    echo "$0 -a <auth-token> [ -d <device-id> ] [ -n <device-name> ] [ -g <device-group> ] [ -p <platform> ] [ -l <local-destination> ] [ -s <subdomain-prefix> ]"
    echo ""
    echo "Note:"
    echo "Command argument auth-token is mandatory.  All other arguments are optional."
    echo "Acceptable platform values: [ amd64, arm, arm64 ]" 
}

# Validate command line args
if [ $# -lt 1 ]; then
    printUsage
    exit
fi

while getopts 'a:d:n:g:p:l:s:' opt; do
    case $opt in
        a) authtoken=$OPTARG
        ;;
        d) device_id=$OPTARG
        ;;
        n) device_name=$OPTARG
        ;;
        g) device_group=$OPTARG
        ;;
        p) platform=$OPTARG
        ;;
        l) local_dest=$OPTARG
        ;;
        s) subdomain_prefix=$OPTARG
        ;;
        ?) echo "Error: Invalid command option"; printUsage; exit 1 
        ;;
    esac
done



if [ -z $authtoken ]; then
    echo "Error: authtoken is missing in the command argument."
    echo ""
    printUsage
    exit
fi

if [ ! -z $local_dest ]; then
    if [[ "$local_dest" == *"http"* ]]; then
        if [ -z $subdomain_prefix ]; then
            echo "Error: Please provide a subdomain prefix for your HTTP Service's Public URL"
            exit
        fi
    fi
fi

readSerialNum() {
    serialNum=$(cat /proc/cpuinfo | grep Serial | sed -En "s/(.*)Serial(.*): (.*)/\3/p")
    if [ "$serialNum" == "" ]; then
        echo "Error: Couldn't read the device serial number from the kernel.  Please provide a device ID as an argument to the command."
        echo ""
        printUsage
        exit
    fi
}

# Read RPi serial number from the kernel
if [ -z $device_id ]; then
    readSerialNum
    device_id=$serialNum
fi

if [ -z $device_name ]; then
    device_name="None"
fi

if [ -z $device_group ]; then
    device_group="None"
fi

setPlatform() {

    if [ ! -z $platform ] && [ "$platform" != "amd64" ] && [ "$platform" != "arm" ] \
                    && [ "$platform" != "arm64" ]; then
        echo "### Invalid value for platform argument"
        printUsage
        exit 
    fi
    
    if [ -z $platform ]; then
        output=$(uname -m) 
        if [ "$output" == "x86_64" ]; then
            platform="linux"
        elif [ "$output" == "aarch64" ] || [ "$output" == "arm64" ]; then
            platform="arm64"
        else
            platform="arm"
        fi
    else
        platform=$platform
        if [ "$platform" == "amd64" ]; then
            platform="linux"
        fi
    fi
}

# Invoke setPlatform()
setPlatform $*

echo "+++ Downloading and installing $platform version"
curl -O https://portal.socketxp.com/download/$platform/socketxp
if [ $? -eq 0 ]; then
    echo "+++ SocketXP Download Completed."
else 
    echo "### Error: SocketXP download failed!"
    exit 
fi

chmod +wx socketxp
sudo mv socketxp /usr/local/bin

if [ $? -eq 0 ]; then
    echo "+++ SocketXP Install Completed."
else 
    echo "### Error: SocketXP install failed!"
    exit 
fi

if [ -z $local_dest ]; then
    config="{
        \"authtoken\": \"$authtoken\",
        \"tunnel_enabled\": true,
        \"tunnels\" : [{
            \"destination\": \"tcp://127.0.0.1:22\",
            \"protocol\": \"tcp\",
            \"iot_device_id\": \"$device_id\",              
            \"iot_device_name\": \"$device_name\",   
            \"iot_device_group\": \"$device_group\"      
        }]
    }"
else
    if [[ "$local_dest" == *"http"* ]]; then
        config="{
            \"authtoken\": \"$authtoken\",
            \"tunnel_enabled\": true,
            \"tunnels\" : [{
                \"destination\": \"$local_dest\",
                \"protocol\": \"http\",
                \"custom_domain\": \"\",
                \"subdomain\": \"$subdomain_prefix-$device_id\"
            }]
        }"
    fi

    if [[ "$local_dest" == *"tcp"* ]]; then
 
        config="{
            \"authtoken\": \"$authtoken\",
            \"tunnel_enabled\": true,
            \"tunnels\" : [{
                \"destination\": \"$local_dest\",
                \"protocol\": \"tcp\",
                \"iot_device_id\": \"$device_id\",              
                \"iot_device_name\": \"$device_name\",   
                \"iot_device_group\": \"$device_group\"      
            }]
        }"
    fi
fi

# Write config to file
echo $config > $HOME/config.json

# Login to SocketXP Gateway using authtoken
/usr/local/bin/socketxp login $authtoken
if [ $? -eq 0 ]; then
    echo "+++ SocketXP Login Completed"
else 
    echo "### Error: SocketXP login failed!"
    exit 
fi

# Configure and run SocketXP agent as a linux systemd daemon service
sudo /usr/local/bin/socketxp service install --config $HOME/config.json
if [ $? -eq 0 ]; then
    echo "+++ SocketXP Service Install Completed"
else 
    echo "### Error: SocketXP Service Install failed!"
    exit 
fi

sudo systemctl daemon-reload
if [ $? -eq 0 ]; then
    echo "+++ SocketXP Service Daemon-Reload Completed"
else 
    echo "### Error: SocketXP Service daemon-reload failed!"
    exit 
fi

sudo systemctl start socketxp
if [ $? -eq 0 ]; then
    echo "+++ SocketXP Service Kickstarted"
else 
    echo "### Error: SocketXP Service start failed!"
    exit 
fi

# Enable socketxp service to start always on reboot.
sudo systemctl enable socketxp
if [ $? -eq 0 ]; then
    echo "+++ Enabled SocketXP Service to start always on reboot"
else 
    echo "### Error: SocketXP Service enable failed!"
    exit 
fi
