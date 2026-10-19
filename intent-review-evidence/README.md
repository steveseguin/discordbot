# NinjaBot custom moderation

NinjaBot (application `843169738556571680`) detects unsolicited text repetition across channels and attachment/image-link flooding in the VDO.Ninja and Social Stream Ninja community.

[Watch the Discord moderation recording](https://updates.vdo.ninja/intent-review-evidence/moderation-demo.html) · [Download MP4](moderation-demo.mp4) · [Moderation source](../NinjaBot/cogs/NinjaAntiSpam.py)

## Attachment and image-link flooding

For each author in each channel, the bot counts messages containing attachments or supported image links within the preceding 30 seconds. It deletes messages beyond the first five and issues a temporary warning on the sixth. Ordinary text-only messages do not increment this counter. An attachment message counts once even if it contains multiple files.

The recording shows six test attachment messages arriving in Discord, the sixth being removed, and the warning appearing and clearing. It uses the unchanged moderation handler with synthetic member inputs backed by real Discord test posts. Deletion and warnings occur in Discord; no accounts are removed.

## Text comparison across channels

The bot compares a person's new message with their previous message. When their recent activity spans multiple channels, identical or almost identical text increases a spam score. Repeated violations lead to message removal and a kick. This catches repeated text even when it contains no banned words. Bots and trusted staff/sponsor roles are excluded. The linked source contains the exact comparison and scoring rules.

This comparison needs the text of ordinary messages, including messages that never mention or invoke the bot. The separate three-channel activity rule uses channel IDs and does not itself require message content.

## What stops working without Message Content?

Discord sends ordinary message events with empty text and attachment lists. NinjaBot can tell that someone posted, but cannot compare what they wrote or identify attachment/image-link messages. Counting every message instead would also penalize normal text conversations.

| Input or alternative | Relevance to these checks |
|---|---|
| Ordinary message text | Required to compare successive text and identify supported image links. |
| Attachments | Required to determine which messages increment the attachment counter. |
| Slash commands, mentions, DMs, and message commands | Require someone to send or select a message for the bot. People posting spam do not have to do that. |
| Discord AutoMod | Provides word/pattern filters, general spam detection, and mention limits. Its documented settings do not let us configure these comparisons between a person's recent messages or this combined attachment/image-link limit over 30 seconds. |

See Discord's [Message Content guidance](https://docs.discord.com/developers/gateway/you-might-not-need-a-privileged-intent#message-content-intent) and [AutoMod trigger configuration](https://docs.discord.com/developers/resources/auto-moderation#trigger-types).

## Data handling

Moderation buffers stay in memory. The latest tracked text is replaced by subsequent text; a cleanup task runs every two minutes and removes author buffers after more than 60 seconds of inactivity. Moderation reports stay in a staff channel in Discord. The management bot does not maintain a message-history archive, call AI providers, train models, or build an AI knowledge base.

[Privacy policy](https://updates.vdo.ninja/privacy.html). The separately operated AI support application is `1465030230107357275`.
