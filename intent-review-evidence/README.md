# Discord privileged-intent review evidence

These screenshots show the community-management NinjaBot (application `843169738556571680`). The separate AI support application is `1465030230107357275`.

The management bot uses Message Content for proactive cross-channel text-similarity checks and attachment/image-link flood detection. It compares ordinary messages that do not invoke the bot. Slash commands and mentions cannot supply those unsolicited messages. Moderation buffers stay in memory, and staff reports are posted in Discord.

- `thread-creation.png`: automatic support-thread welcome and moderation controls.
- `spam-moderation.png`: repeated spam enforcement reports in the staff moderation channel.
- `documentation-command.png`: a message-content command response linking a user to the VDO.Ninja documentation.

User handles have been redacted where needed. The management bot does not call AI providers, train models, or build a RAG index. The optional Ask the Bot action invokes the separate support application.
