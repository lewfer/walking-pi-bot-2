cp update-walking-pi-bot-2.sh ~
cp tcl_robot.service /etc/systemd/system/
sudo systemctl enable tcl_robot.service
sudo systemctl start tcl_robot.service
