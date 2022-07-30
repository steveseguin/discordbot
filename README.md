# discordbot
The Discord bot for VDO.Ninja

### Installation
to install, it's something like this:
```
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install python3
sudo apt-get install python3-pip
sudo pip3 install -r requirements.txt
sudo python3 server.py
```

### Setup
You need to create an app in Discord, then a bot of that app, then an invite link with Administrator permissions enabled. [Discord Guide](https://discordpy.readthedocs.io/en/stable/discord.html)

You need to then use the token as "discordBotToken" for that bot in the cfg file, renaming it to discordbot.cfg

You also have to create an app on reddit and paste the client id and client secret into the config file. (redditClientId and redditClientSecret)

Advanced users should setup the script as a system service, so it auto restarts as needed or run everything inside a docker container.