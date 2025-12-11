# VDO.Ninja Discord Bot

A comprehensive Discord bot for the [VDO.Ninja community](https://discord.vdo.ninja), providing automated support, content updates, and community management features.

![Contributors](https://contrib.rocks/image?repo=steveseguin/discordbot)

## Features

### Community Support
- **Command System**: Access helpful information through a collection of easily invokable commands
- **Automatic Thread Creation**: Organizes support requests into threads for better management
- **AI-Powered Support**: Bot can provide immediate answers to common questions using LLM integration
- **Anti-Spam Protection**: Detects and manages spam messages and inappropriate content

### Content Management
- **Update Channel**: Posts from the Discord #update channel are automatically published to [updates.vdo.ninja](https://updates.vdo.ninja)
- **YouTube Monitoring**: Automatically posts new videos from specified YouTube channels
- **Reddit Integration**: Posts new content from r/VDONinja subreddit
- **Freelancer Services**: Approval-based system for managing a directory of community freelancers

### Administration
- **Thread Management**: Automatically creates, renames, and archives threads
- **Support Staff Tools**: Login/logout system for support staff to receive notifications
- **Services Moderation**: Approve/reject freelancer submissions with button-based workflow

## Installation

### Prerequisites
- Python 3.8+ 
- pip3
- A server to host the bot (Linux recommended)

### Basic Setup
```bash
# Clone the repository
git clone https://github.com/steveseguin/discordbot.git
cd discordbot

# Update and install dependencies
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install python3 python3-pip
sudo pip3 install -r requirements.txt

# Configure the bot (see Configuration section)
cp NinjaBot/discordbot.sample.cfg NinjaBot/discordbot.cfg
nano NinjaBot/discordbot.cfg

# Run the bot
sudo python3 main.py
```

## Configuration

The bot requires several API keys and configuration options. Copy the sample config file and edit with your credentials:

### Discord Setup
1. Create a Discord application at [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a bot for your application
3. Generate an invite link with Administrator permissions
4. Invite the bot to your server
5. Copy the bot token to `discordbot.cfg` as `discordBotToken`

### Reddit API (Optional)
1. Create an app on [Reddit](https://www.reddit.com/prefs/apps)
2. Copy the client ID and client secret to `discordbot.cfg` as `redditClientId` and `redditClientSecret`

### YouTube API (Optional)
1. Create a project in [Google API Console](https://console.developers.google.com/)
2. Enable the "YouTube Data API v3"
3. Create an API key
4. Add the key to `discordbot.cfg` as `youtubeApiKey`

### Gitbook API (Optional)
1. Create an API token in Gitbook personal settings → developer settings
2. Add to `discordbot.cfg` as `gitbookApiKey`

### Github API (Optional)
1. Create an API token in Github settings → Developer settings → Personal access tokens → Tokens (classic)
2. Add to `discordbot.cfg` as `githubApiKey`

### AI Integration (Optional)
The bot supports multiple AI providers for enhanced support capabilities. When enabled, the bot can automatically respond to questions in configured channels.

```json
"aiEnabledChannels": ["CHANNEL_ID"],
"ai": {
    "enabled": true,
    "service": "GEMINI",
    "api_key": "YOUR_API_KEY",
    "model": "gemini-2.0-flash",
    "temperature": 0.7,
    "max_tokens": 1500,
    "api_url": ""
}
```

**Supported AI Services:**
- `GEMINI` - Google's Gemini API (recommended: `gemini-2.0-flash`)
- `OPENAI` - OpenAI API (models like `gpt-4`, `gpt-3.5-turbo`)
- `OLLAMA` - Self-hosted Ollama (set `api_url` to your Ollama endpoint)

**Channel-Specific Instructions:**
You can customize the AI's behavior per channel using `channelInstructions`:
```json
"channelInstructions": {
    "SUPPORT_CHANNEL_ID": "You are helping in #support. Focus on troubleshooting...",
    "BUG_REPORTS_CHANNEL_ID": "You are helping in #bug-reports..."
}
```

### Freelancer Services Integration (Optional)
The bot can manage a freelancer services directory with an approval workflow:

1. Users submit their service via a web form that posts to a Discord webhook
2. Submissions appear in a private review channel with Approve/Reject buttons
3. Approved services are saved to a GitHub Gist and announced publicly

```json
"servicesChannel": "PRIVATE_REVIEW_CHANNEL_ID",
"servicesAnnounceChannel": "PUBLIC_ANNOUNCE_CHANNEL_ID",
"servicesGistId": "YOUR_GIST_ID",
"servicesApprovers": ["APPROVER_USER_ID"]
```

**Setup:**
1. Create a GitHub Gist with a `services.json` file (can be empty `{}` initially)
2. Create a Discord webhook pointing to your review channel
3. Add approver user IDs to `servicesApprovers`
4. The services page reads from the Gist to display approved listings

**Slash Commands:**
- `/listservices` - View all approved service listings
- `/removeservice <discord_username>` - Remove a listing (approvers only)

## Production Deployment

For production environments, it's recommended to set up the bot as a system service:

### Create a systemd service
```bash
sudo nano /etc/systemd/system/discordbot.service
```

Add the following content:
```
[Unit]
Description=VDO.Ninja Discord Bot
After=network.target

[Service]
User=your-username
WorkingDirectory=/path/to/discordbot
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl enable discordbot.service
sudo systemctl start discordbot.service
```

### Docker Deployment (Alternative)
For containerized deployments, you can use Docker:

```bash
# Build the image
docker build -t vdoninja-discordbot .

# Run the container
docker run -d \
  --name vdoninja-bot \
  --restart unless-stopped \
  -v /path/to/config:/app/NinjaBot \
  vdoninja-discordbot
```

## Updates Channel

The bot manages the [updates.vdo.ninja](https://updates.vdo.ninja) website, which displays updates from the Discord #updates channel. Messages posted by allowed users in the specified updates channel are automatically processed and published.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

For small code contributions, simply submit a PR. For larger changes or new features, please get in touch with the maintainers first.

