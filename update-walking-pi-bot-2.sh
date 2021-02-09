rm -r -f ~/tcl-temp/* 2> ~/errors
rm -r -f ~/tcl-temp/.* 2>> ~/errors
git clone https://github.com/lewfer/walking-pi-bot-2 ~/tcl-temp -q
cp -r ~/tcl-temp/* ~/tcl/walking-pi-bot-2/
rm -r -f ~/tcl-temp/* 2>> ~/errors
rm -r -f ~/tcl-temp/.* 2>> ~/errors

