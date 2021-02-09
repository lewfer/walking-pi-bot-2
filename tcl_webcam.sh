DATE=`date '+%Y-%m-%d %H:%M:%S'`
echo "Think Create Learn Robot service started at ${DATE}" | systemd-cat -p info

cd /home/pi/tcl/walking-pi-bot-2
python3 stream.py
