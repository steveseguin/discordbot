# discordbot
The Discord bot for VDO.Ninja

### Installation
to install, it's something like this,
```
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install python3
sudo apt-get install python3-pip
sudo apt-get install libffi-dev
sudo apt-get install python-dev
sudo pip3 install -U PyNaCl
sudo pip3 install -U "discord.py[voice]"
sudo pip3 install -U beautifulsoup4
sudo python3 server.py
```

### Setup
You need to create an app in Discord, then a bot of that app, then an invite link with permissions enabled. [Guide](https://discordpy.readthedocs.io/en/stable/discord.html)

You need to then use the token for that bot in the cfg file, renaming it to discordbot.cfg

Advanced users should setup the script as a system service, so it auto restarts as needed.

### TODO

Currently this bot uses discordpy 1.7.x; the code needs to be upgraded to 2.x tho
