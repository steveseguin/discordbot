import logging
import asyncio
import discord
import aiohttp
import json
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
from datetime import datetime
import uuid

logger = logging.getLogger("NinjaBot." + __name__)


class ServiceApprovalView(View):
    """Buttons for approving/rejecting service submissions"""

    def __init__(self, cog):
        super().__init__(timeout=None)  # Persistent view - no timeout
        self.cog = cog

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green, custom_id="service_approve", emoji="✅")
    async def approve_button(self, interaction: discord.Interaction, button: Button):
        """Handle approve button click"""
        # Check if user is an approved reviewer
        approvers = self.cog.bot.config.get("servicesApprovers") if self.cog.bot.config.has("servicesApprovers") else []
        if str(interaction.user.id) not in approvers:
            await interaction.response.send_message("You don't have permission to approve listings.", ephemeral=True)
            return

        # Get the original webhook message (the one this message is replying to)
        message = interaction.message
        if not message or not message.reference:
            await interaction.response.send_message("Could not find submission data.", ephemeral=True)
            return

        # Fetch the referenced message (the webhook submission)
        try:
            original_message = await message.channel.fetch_message(message.reference.message_id)
        except Exception as e:
            logger.error(f"Could not fetch original message: {e}")
            await interaction.response.send_message("Could not find original submission.", ephemeral=True)
            return

        if not original_message.embeds:
            await interaction.response.send_message("Original message has no embed data.", ephemeral=True)
            return

        embed = original_message.embeds[0]

        # Parse the submission
        service_data = self.cog.parse_submission_embed(embed)
        if not service_data:
            await interaction.response.send_message("Could not parse submission data.", ephemeral=True)
            return

        await interaction.response.defer()

        # Add to Gist
        success = await self.cog.add_service_to_gist(service_data)

        if success:
            # Disable buttons and update the bot's reply message to show approved
            for item in self.children:
                item.disabled = True
            await message.edit(content=f"✅ **Approved** by {interaction.user.display_name}", view=self)

            await interaction.followup.send(f"Service listing for **{service_data.get('name', 'Unknown')}** has been approved and published!", ephemeral=True)

            # Announce in public channel
            await self.cog.announce_service(service_data)

            logger.info(f"Approved service listing: {service_data.get('name')} by {interaction.user.display_name}")
        else:
            await interaction.followup.send("Error: Could not publish service listing. Check bot logs.", ephemeral=True)

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.red, custom_id="service_reject", emoji="❌")
    async def reject_button(self, interaction: discord.Interaction, button: Button):
        """Handle reject button click"""
        # Check if user is an approved reviewer
        approvers = self.cog.bot.config.get("servicesApprovers") if self.cog.bot.config.has("servicesApprovers") else []
        if str(interaction.user.id) not in approvers:
            await interaction.response.send_message("You don't have permission to reject listings.", ephemeral=True)
            return

        message = interaction.message
        if not message or not message.reference:
            await interaction.response.send_message("Could not find submission data.", ephemeral=True)
            return

        # Fetch the referenced message (the webhook submission)
        try:
            original_message = await message.channel.fetch_message(message.reference.message_id)
        except Exception as e:
            logger.error(f"Could not fetch original message: {e}")
            await interaction.response.send_message("Could not find original submission.", ephemeral=True)
            return

        if not original_message.embeds:
            await interaction.response.send_message("Original message has no embed data.", ephemeral=True)
            return

        embed = original_message.embeds[0]

        # Disable buttons and update the bot's reply message to show rejected
        for item in self.children:
            item.disabled = True
        await message.edit(content=f"❌ **Rejected** by {interaction.user.display_name}", view=self)

        await interaction.response.send_message("Submission rejected.", ephemeral=True)

        logger.info(f"Rejected service listing by {interaction.user.display_name}")


class NinjaServices(commands.Cog):
    """
    Handles freelancer services submissions for Social Stream Ninja / VDO.Ninja.

    Workflow:
    1. User submits form on socialstream.ninja/docs/services.html
    2. Form POSTs to Discord webhook -> arrives in private review channel (servicesChannel)
    3. Admin clicks Approve/Reject button
    4. Bot updates GitHub Gist with approved service listing
    5. Bot announces the approved listing in public channel (servicesAnnounceChannel)
    6. Services page reads from Gist and displays approved listings
    """

    def __init__(self, bot) -> None:
        logger.debug(f"Loading {self.__class__.__name__}")
        self.bot = bot
        self.isInternal = True
        self.http = aiohttp.ClientSession()
        # Lock to prevent race conditions on gist updates
        self.gist_lock = asyncio.Lock()
        # Register persistent view
        self.approval_view = ServiceApprovalView(self)
        bot.add_view(self.approval_view)

    def cog_check(self, ctx) -> bool:
        """Only allow commands in guild context"""
        return ctx.guild is not None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Listen for webhook messages in the services channel and add approval buttons"""

        # Check if services feature is configured
        if not self.bot.config.has("servicesChannel"):
            return

        # Check if message is in the services channel
        if message.channel.id != int(self.bot.config.get("servicesChannel")):
            return

        # Check if it's a webhook message
        if not message.webhook_id:
            return

        # Check if it has embeds (our submission format)
        if not message.embeds:
            return

        # Check if it looks like a service submission (has the right fields)
        embed = message.embeds[0]
        if not embed.title or "Submission" not in embed.title:
            return

        # Reply with approval buttons (can't edit webhook messages)
        try:
            view = ServiceApprovalView(self)
            await message.reply(content="**Review this submission:**", view=view, mention_author=False)
            logger.info(f"Added approval buttons to service submission from webhook")
        except Exception as e:
            logger.exception(f"Error adding approval buttons: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """Fallback: Allow approving submissions via checkmark reaction on the original webhook message"""

        # Check if services feature is configured
        if not self.bot.config.has("servicesChannel"):
            return

        # Check if reaction is in the services channel
        if payload.channel_id != int(self.bot.config.get("servicesChannel")):
            return

        # Check if it's a checkmark or X reaction
        if str(payload.emoji) not in ["✅", "❌"]:
            return

        # Check if user is an approver
        approvers = self.bot.config.get("servicesApprovers") if self.bot.config.has("servicesApprovers") else []
        if str(payload.user_id) not in approvers:
            return

        # Ignore bot's own reactions
        if payload.user_id == self.bot.user.id:
            return

        try:
            channel = self.bot.get_channel(payload.channel_id)
            if not channel:
                return

            message = await channel.fetch_message(payload.message_id)
            if not message or not message.embeds:
                return

            embed = message.embeds[0]

            # Check if it looks like a service submission
            if not embed.title or "Submission" not in embed.title:
                return

            # Check if already processed (has footer indicating approval/rejection)
            if embed.footer and embed.footer.text and ("Approved" in embed.footer.text or "Rejected" in embed.footer.text):
                return

            user = self.bot.get_user(payload.user_id) or await self.bot.fetch_user(payload.user_id)

            if str(payload.emoji) == "✅":
                # Approve
                service_data = self.parse_submission_embed(embed)
                if not service_data:
                    logger.warning("Could not parse submission from reaction approval")
                    return

                success = await self.add_service_to_gist(service_data)
                if success:
                    await self.announce_service(service_data)
                    await channel.send(f"✅ **{service_data.get('name', 'Unknown')}** approved by {user.display_name} (via reaction)")
                    logger.info(f"Approved service listing via reaction: {service_data.get('name')} by {user.display_name}")
                else:
                    await channel.send(f"❌ Error approving service listing. Check bot logs.")

            elif str(payload.emoji) == "❌":
                # Reject
                await channel.send(f"❌ Submission rejected by {user.display_name} (via reaction)")
                logger.info(f"Rejected service listing via reaction by {user.display_name}")

        except Exception as e:
            logger.exception(f"Error processing reaction approval: {e}")

    async def announce_service(self, service_data: dict) -> None:
        """Announce an approved service listing in the public channel"""
        if not self.bot.config.has("servicesAnnounceChannel"):
            return

        try:
            announce_channel_id = int(self.bot.config.get("servicesAnnounceChannel"))
            announce_channel = self.bot.get_channel(announce_channel_id)

            if not announce_channel:
                logger.warning(f"Could not find announce channel {announce_channel_id}")
                return

            # Build announcement embed
            embed = discord.Embed(
                title=f"New Freelancer: {service_data.get('name', 'Unknown')}",
                description=service_data.get('description', '')[:500],
                color=0x77B255,
                url="https://socialstream.ninja/docs/services.html"
            )

            # Add platforms
            platforms = service_data.get('platforms', [])
            if platforms:
                platform_str = ", ".join(platforms)
                embed.add_field(name="Platforms", value=platform_str, inline=True)

            # Add service types
            service_types = service_data.get('serviceTypes', [])
            if service_types:
                types_str = ", ".join(service_types[:5])
                embed.add_field(name="Services", value=types_str, inline=True)

            # Add Discord contact
            discord_user = service_data.get('discord', '')
            if discord_user:
                embed.add_field(name="Discord", value=discord_user, inline=True)

            # Add social links
            socials = service_data.get('socials', {})
            if socials:
                social_links = []
                for platform, url in list(socials.items())[:3]:
                    social_links.append(f"[{platform.title()}]({url})")
                if social_links:
                    embed.add_field(name="Links", value=" | ".join(social_links), inline=False)

            embed.set_footer(text="View all services at socialstream.ninja/docs/services.html")

            await announce_channel.send(embed=embed)
            logger.info(f"Announced service listing for {service_data.get('name')} in channel {announce_channel_id}")

        except Exception as e:
            logger.exception(f"Error announcing service: {e}")

    def parse_submission_embed(self, embed: discord.Embed) -> dict:
        """Parse a Discord embed from the submission webhook into service data"""
        try:
            service = {
                "id": str(uuid.uuid4()),
                "addedDate": datetime.now().strftime("%Y-%m-%d")
            }

            for field in embed.fields:
                name = field.name.lower()
                value = field.value

                if name == "name" or name == "display name":
                    service["name"] = value
                elif name == "discord" or name == "discord username":
                    service["discord"] = value
                elif name == "description":
                    service["description"] = value
                elif name == "platforms":
                    # Parse platforms list and normalize to short codes
                    platforms = []
                    for p in value.split(","):
                        p = p.strip().lower()
                        if "social stream" in p or p == "ssn":
                            platforms.append("ssn")
                        elif "vdo" in p:
                            platforms.append("vdo")
                    service["platforms"] = platforms
                elif name == "service types" or name == "services":
                    # Parse service types list
                    service["serviceTypes"] = [s.strip() for s in value.split(",")]
                elif name == "social links" or name == "socials":
                    # Parse social links - expected format: "platform: url, platform: url"
                    socials = {}
                    for link in value.split("\n"):
                        link = link.strip()
                        if not link or link == "None":
                            continue
                        # Handle various formats
                        if ": " in link:
                            parts = link.split(": ", 1)
                            if len(parts) == 2:
                                socials[parts[0].lower()] = parts[1]
                        elif link.startswith("http"):
                            # Just a URL, try to detect platform
                            if "discord" in link.lower():
                                socials["discord"] = link
                            elif "twitter" in link.lower() or "x.com" in link.lower():
                                socials["twitter"] = link
                            elif "instagram" in link.lower():
                                socials["instagram"] = link
                            elif "youtube" in link.lower():
                                socials["youtube"] = link
                            else:
                                socials["website"] = link
                    service["socials"] = socials
                elif name == "portfolio" or name == "portfolio links" or name == "portfolio urls":
                    # Parse portfolio URLs
                    if value and value != "None":
                        service["portfolio"] = [url.strip() for url in value.split("\n") if url.strip() and url.strip() != "None"]
                elif name == "payment links" or name == "payment":
                    # Parse payment URLs
                    if value and value != "None":
                        service["paymentLinks"] = [url.strip() for url in value.split("\n") if url.strip() and url.strip() != "None"]
                elif name == "discord id":
                    # Store Discord user ID for avatar display
                    if value and value != "None":
                        service["discordId"] = value.strip()
                elif name == "avatar url":
                    # Store Discord avatar URL
                    if value and value != "None":
                        service["avatarUrl"] = value.strip()

            # Validate required fields
            if not service.get("name") or not service.get("discord") or not service.get("description"):
                logger.warning(f"Missing required fields in submission: {service}")
                return None

            return service

        except Exception as e:
            logger.exception(f"Error parsing submission embed: {e}")
            return None

    async def add_service_to_gist(self, service_data: dict) -> bool:
        """Add a new service listing to the GitHub Gist"""

        gh_headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"token {self.bot.config.get('githubApiKey')}"
        }

        gist_id = self.bot.config.get("servicesGistId")

        # Use lock to prevent race conditions when multiple approvals happen simultaneously
        async with self.gist_lock:
            try:
                # Fetch current gist content
                async with self.http.get(f"https://api.github.com/gists/{gist_id}", headers=gh_headers) as resp:
                    if resp.status != 200:
                        logger.error(f"Failed to fetch gist: {resp.status}")
                        return False

                    gist_api_data = await resp.json(content_type="application/json")

                    # Validate response structure
                    if "files" not in gist_api_data:
                        logger.error("Gist API response missing 'files' key")
                        return False
                    if "services.json" not in gist_api_data["files"]:
                        logger.error("Gist does not contain services.json file")
                        return False
                    if "raw_url" not in gist_api_data["files"]["services.json"]:
                        logger.error("Gist services.json missing raw_url")
                        return False

                    raw_url = gist_api_data["files"]["services.json"]["raw_url"]

                # Fetch current services data
                async with self.http.get(raw_url) as resp:
                    if resp.status != 200:
                        logger.error(f"Failed to fetch services.json: {resp.status}")
                        return False

                    gist_content = await resp.json(content_type=None)
                    if not gist_content:
                        # Initialize empty structure
                        gist_content = {
                            "lastUpdated": datetime.now().strftime("%Y-%m-%d"),
                            "disclaimer": "These listings are user-submitted and community-provided. Social Stream Ninja does not validate, endorse, or guarantee these services.",
                            "services": []
                        }

                # Check for duplicate (by discord username)
                existing = next((s for s in gist_content.get("services", [])
                               if s.get("discord", "").lower() == service_data.get("discord", "").lower()), None)

                if existing:
                    # Update existing entry
                    idx = gist_content["services"].index(existing)
                    service_data["id"] = existing.get("id", service_data["id"])  # Keep original ID
                    service_data["addedDate"] = existing.get("addedDate", service_data["addedDate"])  # Keep original date
                    gist_content["services"][idx] = service_data
                    logger.info(f"Updated existing service listing for {service_data.get('discord')}")
                else:
                    # Add new entry
                    gist_content["services"].append(service_data)
                    logger.info(f"Added new service listing for {service_data.get('discord')}")

                # Update lastUpdated
                gist_content["lastUpdated"] = datetime.now().strftime("%Y-%m-%d")

                # Push update to gist
                patch_data = {
                    "files": {
                        "services.json": {
                            "content": json.dumps(gist_content, indent=2)
                        }
                    }
                }

                async with self.http.patch(f"https://api.github.com/gists/{gist_id}", json=patch_data, headers=gh_headers) as resp:
                    if resp.status == 200:
                        logger.info("Successfully updated services gist")
                        return True
                    else:
                        logger.error(f"Failed to update gist: {resp.status}")
                        logger.error(await resp.text())
                        return False

            except Exception as e:
                logger.exception(f"Error updating services gist: {e}")
                return False

    @app_commands.command(name="removeservice", description="Remove a freelancer service listing")
    @app_commands.describe(discord_username="The Discord username of the service to remove")
    async def remove_service(self, interaction: discord.Interaction, discord_username: str) -> None:
        """Remove a service listing by Discord username"""

        # Check if user is an approved reviewer
        if str(interaction.user.id) not in self.bot.config.get("servicesApprovers", []):
            await interaction.response.send_message("You don't have permission to remove service listings.", ephemeral=True)
            return

        gh_headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"token {self.bot.config.get('githubApiKey')}"
        }

        gist_id = self.bot.config.get("servicesGistId")

        # Use lock to prevent race conditions
        async with self.gist_lock:
            try:
                await interaction.response.defer(ephemeral=True)

                # Fetch current gist content
                async with self.http.get(f"https://api.github.com/gists/{gist_id}", headers=gh_headers) as resp:
                    if resp.status != 200:
                        await interaction.followup.send("Failed to fetch services data.", ephemeral=True)
                        return

                    gist_api_data = await resp.json(content_type="application/json")

                    # Validate response structure
                    if "files" not in gist_api_data or "services.json" not in gist_api_data["files"]:
                        await interaction.followup.send("Gist structure invalid - missing services.json", ephemeral=True)
                        return

                    raw_url = gist_api_data["files"]["services.json"]["raw_url"]

                async with self.http.get(raw_url) as resp:
                    gist_content = await resp.json(content_type=None)

                # Find and remove the service
                services = gist_content.get("services", [])
                original_count = len(services)
                services = [s for s in services if s.get("discord", "").lower() != discord_username.lower()]

                if len(services) == original_count:
                    await interaction.followup.send(f"No service listing found for Discord user: {discord_username}", ephemeral=True)
                    return

                gist_content["services"] = services
                gist_content["lastUpdated"] = datetime.now().strftime("%Y-%m-%d")

                # Push update
                patch_data = {
                    "files": {
                        "services.json": {
                            "content": json.dumps(gist_content, indent=2)
                        }
                    }
                }

                async with self.http.patch(f"https://api.github.com/gists/{gist_id}", json=patch_data, headers=gh_headers) as resp:
                    if resp.status == 200:
                        await interaction.followup.send(f"Successfully removed service listing for: {discord_username}", ephemeral=True)
                    else:
                        await interaction.followup.send("Failed to update services data.", ephemeral=True)

            except Exception as e:
                logger.exception(f"Error removing service: {e}")
                await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)

    @app_commands.command(name="listservices", description="List all approved freelancer services")
    async def list_services(self, interaction: discord.Interaction) -> None:
        """List all currently approved services"""

        gist_id = self.bot.config.get("servicesGistId")
        if not gist_id:
            await interaction.response.send_message("Services feature is not configured.", ephemeral=True)
            return

        try:
            await interaction.response.defer(ephemeral=True)

            # Fetch services from gist via API to get dynamic raw_url (not hardcoded username)
            gh_headers = {
                "Accept": "application/vnd.github+json"
            }

            async with self.http.get(f"https://api.github.com/gists/{gist_id}", headers=gh_headers) as resp:
                if resp.status != 200:
                    await interaction.followup.send("Could not fetch services data.", ephemeral=True)
                    return

                gist_api_data = await resp.json(content_type="application/json")

                if "files" not in gist_api_data or "services.json" not in gist_api_data["files"]:
                    await interaction.followup.send("Gist structure invalid.", ephemeral=True)
                    return

                raw_url = gist_api_data["files"]["services.json"]["raw_url"]

            async with self.http.get(raw_url) as resp:
                if resp.status != 200:
                    await interaction.followup.send("Could not fetch services data.", ephemeral=True)
                    return

                data = await resp.json(content_type=None)

            services = data.get("services", [])

            if not services:
                await interaction.followup.send("No approved services yet.", ephemeral=True)
                return

            # Build embed
            embed = discord.Embed(
                title="Approved Freelancer Services",
                description=f"Total: {len(services)} listings",
                color=0x77B255
            )

            for svc in services[:10]:  # Limit to 10 to fit in embed
                name = svc.get("name", "Unknown")
                discord_user = svc.get("discord", "Unknown")
                service_types = ", ".join(svc.get("serviceTypes", [])[:3])
                embed.add_field(
                    name=name,
                    value=f"Discord: {discord_user}\nServices: {service_types}",
                    inline=True
                )

            if len(services) > 10:
                embed.set_footer(text=f"Showing 10 of {len(services)} listings. View all at socialstream.ninja/docs/services.html")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.exception(f"Error listing services: {e}")
            await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)

    async def getCommands(self) -> list:
        """Return the available commands as a list"""
        return []

    async def cog_unload(self) -> None:
        logger.debug(f"Shutting down {self.__class__.__name__}")
        await self.http.close()


async def setup(bot) -> None:
    await bot.add_cog(NinjaServices(bot))
