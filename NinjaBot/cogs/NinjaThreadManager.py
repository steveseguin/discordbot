import logging
import re
import discord
import embedBuilder
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

    @discord.ui.button(label="Close Thread", style=discord.ButtonStyle.success, custom_id="close")
    async def closeButton(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.ntm._close(interaction)

    @discord.ui.button(label="Change Title", style=discord.ButtonStyle.primary, custom_id="title")
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

# The buttons shown below the automated gitbook lens message
class LensReplyButtons(discord.ui.View):
    def __init__(self, NinjaThreadManager, threadCreationUser) -> None:
        super().__init__(timeout=None)
        self.ntm = NinjaThreadManager
        self.threadCreationUser = threadCreationUser

    @discord.ui.button(label="This answered my question", style=discord.ButtonStyle.success)
    async def closeButton(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.ntm._close(interaction)

    @discord.ui.button(label="This does NOT answer my question", style=discord.ButtonStyle.primary)
    async def titleButton(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_message("Thanks for the feedback. Please be patient while you wait for someone to answer." \
                                                "\nFeel free to use any above mentioned methods to search for an answer " \
                                                "yourself and close the thread if you do find it.", ephemeral=True)

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

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        ctx = await self.bot.get_context(message)
        # Check if config options are there and are the expected values
        if (not ctx.author == self.bot.user and not ctx.author.bot \
            and not isinstance(ctx.message.channel, discord.DMChannel) \
            and self.bot.config.has("autoThreadEnabledChannels") \
            and self.bot.config.has("autoThreadWelcomeMapping") \
            and str(ctx.channel.id) in self.bot.config.get("autoThreadEnabledChannels")):

            # Create thread
            createdThread = await ctx.message.create_thread(name=self._getThreadTitle(ctx.message.content), auto_archive_duration=10080, reason=__name__)
            # create embed from welcome message
            welcomeMapping = self.bot.config.get("autoThreadWelcomeMapping")
            try:
                welcomeText = self.bot.config.get(welcomeMapping[str(ctx.channel.id)])
                welcomeText = welcomeText.format(usermention=ctx.message.author.mention)
                embed = embedBuilder.ninjaEmbed(description=welcomeText)
                # Post welcome message to thread
                await createdThread.send(embed=embed, view=ThreadManagementButtons(self, ctx.message.author.id))
            except:
                # No welcome message
                pass

            # add logged in staff to thread
            loggedOnSupportStaff = self.bot.config.get("loggedOnSupportStaff")   
            for staff in loggedOnSupportStaff:
                user = self.bot.get_user(staff)
                # if user not in cache, try api request
                if not user:
                    user = await self.bot.fetch_user(staff)
                await createdThread.add_user(user)

            # lens LLM search
            # check if current channel has it enabled
            if ctx.message.content and str(ctx.channel.id) in self.bot.config.get("lensEnabledChannels"):
                NinjaDocs = self.bot.get_cog("NinjaDocs")
                lensAnswer = await NinjaDocs.getLensAnswer(ctx.message.content)
                if lensAnswer and not lensAnswer["text"].startswith("I don't know."):
                    lensEmbed = embedBuilder.ninjaEmbed(description=NinjaDocs.createEmbedTextFromLensResult(lensAnswer))
                    await createdThread.send("While you wait, here is what NinjaBot thinks might help you with " \
                                             "your question. If it satisfies your request, click the \"This answered my question\" " \
                                             "button above or use the /ask command to ask further specific questions.",
                                             embed=lensEmbed, view=LensReplyButtons(self, ctx.message.author.id))

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
        if interaction.user.id not in loggedOnSupportStaff:
            await interaction.response.send_message(f"You are not logged in to NinjaSupport! :x:", ephemeral=True)
            return
        loggedOnSupportStaff.remove(interaction.user.id)
        await self.bot.config.set("loggedOnSupportStaff", loggedOnSupportStaff)
        await interaction.response.send_message(f"You are now logged out of NinjaSupport :zzz: :no_bell:", ephemeral=True)

    async def cog_command_error(self, ctx, error) -> None:
        """Post error that happen inside this cog to channel"""
        await ctx.send(error)

    # get the first 10 words of a message or 30 chars
    def _getThreadTitle(self, message) -> None:
        match = re.match(r"^(?:\w+\s){1,10}", message)
        if match:
            return match.group(0)
        return message[:30]

    async def getCommands(self) -> list:
        """Return the available commands as a list"""
        return []

    async def cog_unload(self) -> None:
        logger.debug(f"Shutting down {self.__class__.__name__}")

async def setup(bot) -> None:
    await bot.add_cog(NinjaThreadManager(bot))