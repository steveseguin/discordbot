# discordbot
The Discord bot for OBS.Ninja

### Installation
to install, it's something like this,
```
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install python3
sudo apt-get install python3-pip
sudo apt-get install libffi-dev
sudo apt-get install python-dev
sudo pip3 install PyNaCl
sudo python3 -m pip install -U "discord.py[voice]"
sudo python3 server.py
```

### Setup
You need to create an app in Discord, then a bot of that app, then an invite link with permissions enabled

You need to then use the token for that bot in the cfg file, renaming it to discordbot.cfg

Advanced users should setup the script as a system service, so it auto restarts as needed.
