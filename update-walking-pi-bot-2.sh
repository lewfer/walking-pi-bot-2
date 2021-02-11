rm -r -f /home/pi/tcl-temp/* 2> ~/errors
rm -r -f /home/pi/tcl-temp/.* 2>> ~/errors
git clone https://github.com/lewfer/walking-pi-bot-2 /home/pi/tcl-temp -q
cp -r /home/pi/tcl-temp/* /home/pi/tcl/walking-pi-bot-2/
rm -r -f /home/pi/tcl-temp/* 2>> ~/errors
rm -r -f /home/pi/tcl-temp/.* 2>> ~/errors
sudo systemctl restart tcl_robot.service
