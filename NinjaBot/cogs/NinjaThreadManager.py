# NinjaThreadManager.py
import logging
import re
import discord
import embedBuilder
import ai
from discord.ext import commands
from discord import app_commands

logger = logging.getLogger("NinjaBot." + __name__)

# The popup modal to rename a thread
class ThreadTitleChangeModal(discord.ui.Modal, title="Rename Thread"):
    newTitle = discord.ui.TextInput(label="New Title", required=True)

    def __init__(self, NinjaThreadManager, default="") -> None:
        super().__init__(timeout=None)
        self.ntm = NinjaThreadManager
        self.newTitle.default = default

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.ntm._title(interaction, self.newTitle)

# The buttons shown below the welcome message
class ThreadManagementButtons(discord.ui.View):
    def __init__(self, NinjaThreadManager, threadCreationUser) -> None:
        super().__init__(timeout=None)
        self.ntm = NinjaThreadManager
        self.threadCreationUser = threadCreationUser

    @discord.ui.button(label="Close Thread", style=discord.ButtonStyle.success, custom_id="close", emoji="✅")
    async def closeButton(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.ntm._close(interaction)

    @discord.ui.button(label="Change Title", style=discord.ButtonStyle.primary, custom_id="title", emoji="📑")
    async def titleButton(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(ThreadTitleChangeModal(self.ntm, interaction.channel.name))

    # Check if user is Moderator before calling callbacks
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # allow a user to close their own thread
        if hasattr(interaction, "user") and interaction.user.id == self.threadCreationUser \
            and hasattr(interaction, "data") and "custom_id" in interaction.data \
            and interaction.data.get("custom_id") == "close":
            return True
        # allow moderators to do everything everywhere
        if hasattr(interaction, "message") and hasattr(interaction.user, "roles") and discord.utils.get(interaction.user.roles, name="Moderator"):
            return True
        await interaction.response.send_message("Sorry, only staff can use this button", ephemeral=True)
        return False

# The buttons shown below the AI response message
class AIReplyButtons(discord.ui.View):
    def __init__(self, NinjaThreadManager, threadCreationUser) -> None:
        super().__init__(timeout=None)
        self.ntm = NinjaThreadManager
        self.threadCreationUser = threadCreationUser

    @discord.ui.button(label="This answered my question", style=discord.ButtonStyle.success, emoji="✅")
    async def closeButton(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.ntm._close(interaction)

    @discord.ui.button(label="This does NOT answer my question", style=discord.ButtonStyle.primary, emoji="❌")
    async def continueButton(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_message("Thanks for the feedback. Please be patient while you wait for someone to answer." \
                                                "\nFeel free to use any above mentioned methods to search for an answer " \
                                                "yourself and close the thread if you do find it.", ephemeral=True)

    @discord.ui.button(label="Ask a follow-up question", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def followupButton(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_message("You can ask a follow-up question by replying to the AI's message.", ephemeral=True)

    # Check user permissions before calling callbacks
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # allow the thread creation user to do everything
        if hasattr(interaction, "user") and interaction.user.id == self.threadCreationUser:
            return True
        # allow moderators to do everything
        if hasattr(interaction, "message") and hasattr(interaction.user, "roles") and discord.utils.get(interaction.user.roles, name="Moderator"):
            return True
        await interaction.response.send_message("Sorry, you can't use this button", ephemeral=True)
        return False

class NinjaThreadManager(commands.Cog):
    def __init__(self, bot) -> None:
        logger.debug(f"Loading {self.__class__.__name__}")
        self.bot = bot
        self.isInternal = True
        self.ai = ai.NinjaAI(bot)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        # Ignore bot messages
        if message.author == self.bot.user or message.author.bot:
            return
                
        # Handle reply to bot in an existing thread
        if isinstance(message.channel, discord.Thread) and message.reference and self.ai:
            try:
                # Get the message being replied to
                replied_message = await message.channel.fetch_message(message.reference.message_id)
                
                # If it's a reply to a bot message, process it for AI response
                if replied_message.author == self.bot.user:
                    # Get thread history for context
                    messages = []
                    async for msg in message.channel.history(limit=20):
                        messages.append({
                            "content": msg.content,
                            "author": {
                                "id": msg.author.id,
                                "bot": msg.author.bot
                            }
                        })
                    messages.reverse()  # Oldest first
                    
                    # Get AI response with channel context
                    channel_id_str = str(message.channel.parent_id)  # Parent channel of the thread
                    ai_response = await self.ai.get_ai_response(messages, channel_id_str)
                    
                    if ai_response:
                        embed = embedBuilder.ninjaEmbed(description=ai_response)
                        await message.reply(
                            embed=embed,
                            view=AIReplyButtons(self, message.channel.owner_id)
                        )
                    return
            except Exception as e:
                logger.exception(f"Error processing reply message: {e}")
        
        # Handle regular messages in threads - ONLY process initial messages, not any follow-ups
        if isinstance(message.channel, discord.Thread) and self.ai:
            try:
                channel_id_str = str(message.channel.parent_id)
                
                if self.bot.config.has("aiEnabledChannels") and channel_id_str in self.bot.config.get("aiEnabledChannels"):
                    # Get all messages in the thread so far
                    thread_messages = []
                    async for msg in message.channel.history(limit=10):
                        thread_messages.append({
                            "content": msg.content,
                            "author": {
                                "id": msg.author.id,
                                "bot": msg.author.bot
                            }
                        })
                    thread_messages.reverse()  # Convert to oldest first
                    
                    # Only respond if this is the first user message after the welcome message
                    # Check message count - if more than 2 (welcome + first message), don't respond automatically
                    user_messages = [msg for msg in thread_messages if not msg.get("author", {}).get("bot", False)]
                    
                    # Only respond if this is the first or second user message
                    if len(user_messages) <= 2:
                        # Check if there are any substantive bot responses already
                        has_ai_response = False
                        for msg in thread_messages:
                            if msg.get("author", {}).get("bot", False):
                                bot_content = msg.get("content", "")
                                # Check if this looks like an AI response (not just welcome message)
                                if "Here's what NinjaBot thinks" in bot_content:
                                    has_ai_response = True
                                    break
                        
                        # Only respond if there are no AI responses yet
                        if not has_ai_response:
                            # Check if we should respond based on message history
                            should_respond = await self.ai.should_respond_with_history(thread_messages, channel_id_str)
                            logger.info(f"Should respond based on message history: {should_respond}")
                            
                            if should_respond:
                                # Get AI response
                                ai_response = await self.ai.get_ai_response(thread_messages, channel_id_str)
                                
                                if ai_response:
                                    embed = embedBuilder.ninjaEmbed(description=ai_response)
                                    await message.channel.send(
                                        "**Here's what NinjaBot thinks might help with your question:**",
                                        embed=embed,
                                        view=AIReplyButtons(self, message.channel.owner_id)
                                    )
            except Exception as e:
                logger.exception(f"Error processing thread message: {e}")
        
        # Get context for regular message processing (thread creation)
        ctx = await self.bot.get_context(message)
        
        # Check if we should create a thread
        if (not isinstance(ctx.message.channel, discord.DMChannel) 
            and self.bot.config.has("autoThreadEnabledChannels") 
            and self.bot.config.has("autoThreadWelcomeMapping") 
            and str(ctx.channel.id) in self.bot.config.get("autoThreadEnabledChannels")):

            # Create thread
            try:
                createdThread = await ctx.message.create_thread(
                    name=self._getThreadTitle(ctx.message), 
                    auto_archive_duration=10080, 
                    reason=__name__
                )
                
                # Send welcome message
                welcomeMapping = self.bot.config.get("autoThreadWelcomeMapping")
                try:
                    if str(ctx.channel.id) in welcomeMapping:
                        welcomeText = self.bot.config.get(welcomeMapping[str(ctx.channel.id)])
                        welcomeText = welcomeText.format(usermention=ctx.message.author.mention)
                        embed = embedBuilder.ninjaEmbed(description=welcomeText)
                        await createdThread.send(embed=embed, view=ThreadManagementButtons(self, ctx.message.author.id))
                except Exception as e:
                    logger.exception(f"Error sending welcome message: {e}")
                
                # Add logged in staff to thread
                try:
                    # Fix: Get loggedOnSupportStaff without default value
                    loggedOnSupportStaff = self.bot.config.get("loggedOnSupportStaff")
                    if loggedOnSupportStaff is None:
                        loggedOnSupportStaff = []
                        
                    for staff in loggedOnSupportStaff:
                        user = self.bot.get_user(staff)
                        # if user not in cache, try api request
                        if not user:
                            user = await self.bot.fetch_user(staff)
                        await createdThread.add_user(user)
                except Exception as e:
                    logger.exception(f"Error adding staff to thread: {e}")
                
                # Check if AI should respond in this channel
                if self.ai and self.bot.config.has("aiEnabledChannels") and ctx.message.content:
                    # Fix: Get aiEnabledChannels without default value
                    ai_enabled_channels = self.bot.config.get("aiEnabledChannels")
                    if ai_enabled_channels is None:
                        ai_enabled_channels = []
                        
                    logger.info(f"Checking if AI should respond in channel: {ctx.channel.id}")
                    logger.debug(f"AI enabled channels: {ai_enabled_channels}")
                    
                    if self.bot.config.has("ai"):
                        logger.debug(f"AI config: {self.bot.config.get('ai')}")
                    
                    channel_id_str = str(ctx.channel.id)
                    logger.info(f"Current channel ID: {channel_id_str}")
                    logger.info(f"Channel in AI enabled list: {channel_id_str in ai_enabled_channels}")
                    
                    if channel_id_str in ai_enabled_channels:
                        try:
                            # Format message for AI
                            messages = [{
                                "content": ctx.message.content,
                                "author": {
                                    "id": ctx.message.author.id,
                                    "bot": False
                                }
                            }]
                            
                            # Check if AI should respond to this message
                            should_respond = await self.ai.should_respond(messages)
                            logger.info(f"AI should respond: {should_respond}")
                            
                            if should_respond:
                                # Get AI response with channel context
                                ai_response = await self.ai.get_ai_response(messages, channel_id_str)
                                
                                if ai_response:
                                    ai_embed = embedBuilder.ninjaEmbed(description=ai_response)
                                    await createdThread.send(
                                        "**Here's what NinjaBot thinks might help with your question. If it answers your question, click the button below or reply for more assistance:**",
                                        embed=ai_embed,
                                        view=AIReplyButtons(self, ctx.message.author.id)
                                    )
                        except Exception as e:
                            logger.exception(f"Error in AI response process: {e}")
            except Exception as e:
                logger.exception(f"Error creating thread: {e}")


    @app_commands.command(description="Change the thread title")
    @app_commands.describe(new_title="The new thread title")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_messages=True)
    async def title(self, interaction: discord.Interaction, new_title: str = None) -> None:
        if new_title:
            await self._title(interaction, new_title)
        else:
            await interaction.response.send_modal(ThreadTitleChangeModal(self, interaction.channel.name))

    async def _title(self, interaction, new_title) -> None:
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message("You can't change the title here since it's not a thread", ephemeral=True)
            return
        await interaction.response.send_message(f"Changing title to '{new_title}'", ephemeral=True)
        await interaction.channel.edit(name=new_title)

    @app_commands.command(description="Closes the thread")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_messages=True)
    async def close(self, interaction: discord.Interaction) -> None:
        await self._close(interaction)

    async def _close(self, interaction) -> None:
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message("You can't close this since it's not a thread", ephemeral=True)
            return
        await interaction.response.send_message(f"Thread was archived by {interaction.user.display_name}. Anyone can send a message to unarchive it.")
        if not interaction.channel.archived: await interaction.channel.edit(archived=True, reason="NinjaBot")

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_messages=True)
    async def login(self, interaction: discord.Interaction) -> None:
        """Login to automatic pings for support thread creations"""
        loggedOnSupportStaff = self.bot.config.get("loggedOnSupportStaff")
        if loggedOnSupportStaff is None:
            loggedOnSupportStaff = []
            
        if interaction.user.id in loggedOnSupportStaff:
            await interaction.response.send_message(f"You are already logged in to NinjaSupport! :x:", ephemeral=True)
            return
        loggedOnSupportStaff.append(interaction.user.id)
        await self.bot.config.set("loggedOnSupportStaff", loggedOnSupportStaff)
        await interaction.response.send_message(f"You are now logged in to NinjaSupport :white_check_mark: :bell:", ephemeral=True)

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_messages=True)
    async def logout(self, interaction: discord.Interaction) -> None:
        """Logout from automatic pings for support thread creations"""
        loggedOnSupportStaff = self.bot.config.get("loggedOnSupportStaff")
        if loggedOnSupportStaff is None:
            loggedOnSupportStaff = []
            
        if interaction.user.id not in loggedOnSupportStaff:
            await interaction.response.send_message(f"You are not logged in to NinjaSupport! :x:", ephemeral=True)
            return
        loggedOnSupportStaff.remove(interaction.user.id)
        await self.bot.config.set("loggedOnSupportStaff", loggedOnSupportStaff)
        await interaction.response.send_message(f"You are now logged out of NinjaSupport :zzz: :no_bell:", ephemeral=True)

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_messages=True)
    async def ask(self, interaction: discord.Interaction, question: str) -> None:
        """Get an AI-generated answer to a question"""
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message("This command can only be used in threads", ephemeral=True)
            # TODO: Ignore history if the current channel is not a thread
            return
            
        if not self.ai:
            await interaction.response.send_message("AI support is not available at the moment", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        # Get thread history for context
        messages = []
        async for msg in interaction.channel.history(limit=20):
            messages.append({
                "content": msg.content,
                "author": {
                    "id": msg.author.id,
                    "bot": msg.author.bot
                }
            })
        messages.reverse()  # Oldest first
        
        # Add the current question
        messages.append({
            "content": question,
            "author": {
                "id": interaction.user.id,
                "bot": False
            }
        })
        
        # Get AI response with channel context
        channel_id_str = str(interaction.channel.parent_id)  # Parent channel of the thread
        ai_response = await self.ai.get_ai_response(messages, channel_id_str)
        
        if ai_response:
            embed = embedBuilder.ninjaEmbed(description=ai_response)
            await interaction.followup.send(
                embed=embed,
                view=AIReplyButtons(self, interaction.channel.owner_id)
            )
        else:
            await interaction.followup.send("Sorry, I couldn't generate a response. Please try again or wait for a human moderator.")

    async def cog_command_error(self, ctx, error) -> None:
        """Post error that happen inside this cog to channel"""
        await ctx.send(error)

    # get the first 10 words of a message or 30 chars
    def _getThreadTitle(self, msg) -> None:
        message = msg.content
        match = re.match(r"^(?:\w+\W+){1,10}", message)
        if match:
            return match.group(0)[:30]
        if not message and msg.attachments:
            return "Image"
        return message[:30]

    async def getCommands(self) -> list:
        """Return the available commands as a list"""
        return []

    async def cog_unload(self) -> None:
        logger.debug(f"Shutting down {self.__class__.__name__}")
        if self.ai:
            await self.ai.close()

async def setup(bot) -> None:
    await bot.add_cog(NinjaThreadManager(bot))