cp update-walking-pi-bot-2.sh /home/pi/
chmod +x /home/pi/update-walking-pi-bot-2.sh
cp tcl_robot.service /etc/systemd/system/
cp tcl_webcam.service /etc/systemd/system/
sudo systemctl enable tcl_robot.service
sudo systemctl start tcl_robot.service
sudo systemctl enable tcl_webcam.service
sudo systemctl start tcl_webcam.service
