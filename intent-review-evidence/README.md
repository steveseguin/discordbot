# NinjaBot custom moderation

NinjaBot (application `843169738556571680`) detects unsolicited text repetition across channels and attachment/image-link flooding in the VDO.Ninja and Social Stream Ninja community.

[Watch the Discord moderation recording](https://updates.vdo.ninja/intent-review-evidence/moderation-demo.html) · [Download MP4](moderation-demo.mp4) · [Moderation source](../NinjaBot/cogs/NinjaAntiSpam.py)

## Attachment and image-link flooding

For each author in each channel, the bot counts messages containing attachments or supported image links within the preceding 30 seconds. It deletes messages beyond the first five and issues a temporary warning on the sixth. Ordinary text-only messages do not increment this counter. An attachment message counts once even if it contains multiple files.

The recording shows six test attachment messages arriving in Discord, the sixth being removed, and the warning appearing and clearing. It uses the unchanged moderation handler with synthetic member inputs backed by real Discord test posts. Deletion and warnings occur in Discord; no accounts are removed.

## Text comparison across channels

The bot compares an author's current text with their previous tracked text using SIFT4 string distance. Once the author's tracked activity spans multiple channels, identical text adds 1.5 abuse points and distance-1 text adds 1 point. A score of 3 triggers message cleanup and a kick. Bots and trusted staff/sponsor roles are excluded.

This comparison needs the text of ordinary messages, including messages that never mention or invoke the bot. The separate three-channel activity rule uses channel IDs and does not itself require message content.

## Why Message Content is needed

| Input or alternative | Relevance to these checks |
|---|---|
| Ordinary message text | Required to compare successive text and identify supported image links. |
| Attachments | Required to determine which messages increment the attachment counter. |
| Slash commands, mentions, DMs, and message commands | Supply user-selected inputs, not the unsolicited messages that automatic moderation must evaluate. |
| Discord AutoMod | Provides keyword/regex, generic spam, and mention-spam triggers. Its documented rule configuration does not expose the SIFT4 comparison or the per-author, per-channel attachment/image-link counter above. |

See Discord's [Message Content guidance](https://docs.discord.com/developers/gateway/you-might-not-need-a-privileged-intent#message-content-intent) and [AutoMod trigger configuration](https://docs.discord.com/developers/resources/auto-moderation#trigger-types).

## Data handling

Moderation buffers stay in memory. The latest tracked text is replaced by subsequent text; a cleanup task runs every two minutes and removes author buffers after more than 60 seconds of inactivity. Moderation reports stay in a staff channel in Discord. The management bot does not maintain a message-history archive, call AI providers, train models, or build a RAG index.

[Privacy policy](https://updates.vdo.ninja/privacy.html). The separately operated AI support application is `1465030230107357275`.
