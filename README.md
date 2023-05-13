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
sudo python3 main.py
```

### Setup
Discord API: You need to create an app in Discord, then a bot of that app, then an invite link with Administrator permissions enabled. [Discord Guide](https://discordpy.readthedocs.io/en/stable/discord.html)

You need to then use the token as "discordBotToken" for that bot in the cfg file, renaming it to discordbot.cfg

Reddit API: You also have to create an app on reddit and paste the client id and client secret into the config file. ("redditClientId" and "redditClientSecret" in the discordbot.cfg)

Youtube API: You have to create an app in the google api console, then enable the "YouTube Data API v3" and create a new API key. ("youtubeApiKey" in the discordbot.cfg)

Gitbook API: You have to create an api token in the personal settings -> developer settings.

Github API: You have to create an api token in settings -> Developer settings -> personal access token -> tokens (classic).

Advanced users should setup the script as a system service, so it auto restarts as needed or run everything inside a docker container.

### Notes

https://updates.vdo.ninja is where #update channel updates are posted, created via this bot

## Contributors of this repo
<a href="https://github.com/steveseguin/discordbot/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=steveseguin/discordbot" />
</a>
