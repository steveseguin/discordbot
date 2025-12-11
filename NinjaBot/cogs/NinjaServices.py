import logging
import asyncio
import discord
import aiohttp
import json
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import uuid

logger = logging.getLogger("NinjaBot." + __name__)

class NinjaServices(commands.Cog):
    """
    Handles freelancer services submissions for Social Stream Ninja / VDO.Ninja.

    Workflow:
    1. User submits form on socialstream.ninja/docs/services.html
    2. Form POSTs to Discord webhook -> arrives in services channel
    3. Admin reacts with checkmark emoji to approve
    4. Bot updates GitHub Gist with approved service listing
    5. Services page reads from Gist and displays approved listings
    """

    def __init__(self, bot) -> None:
        logger.debug(f"Loading {self.__class__.__name__}")
        self.bot = bot
        self.isInternal = True
        self.http = aiohttp.ClientSession()
        # Lock to prevent race conditions on gist updates
        self.gist_lock = asyncio.Lock()
        # Emoji for approval (green checkmark)
        self.approve_emoji = "\u2705"  # ✅
        # Emoji for rejection (red X)
        self.reject_emoji = "\u274C"  # ❌

    def cog_check(self, ctx) -> bool:
        """Only allow commands in guild context"""
        return ctx.guild is not None

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """Listen for approval reactions on service submissions"""

        # Check if services feature is configured
        if not self.bot.config.has("servicesChannel") \
            or not self.bot.config.has("servicesGistId") \
            or not self.bot.config.has("githubApiKey") \
            or not self.bot.config.has("servicesApprovers"):
            return

        # Check if reaction is in the services channel
        if payload.channel_id != int(self.bot.config.get("servicesChannel")):
            return

        # Check if user is an approved reviewer
        if str(payload.user_id) not in self.bot.config.get("servicesApprovers"):
            return

        # Check if it's the approval emoji
        if str(payload.emoji) != self.approve_emoji:
            return

        # Fetch the message
        channel = self.bot.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            logger.warning(f"Message {payload.message_id} not found for approval")
            return
        except Exception as e:
            logger.exception(f"Error fetching message for approval: {e}")
            return

        # Check if it's a webhook message (service submission)
        if not message.webhook_id:
            return

        # Check if message has embeds (our submission format)
        if not message.embeds:
            return

        embed = message.embeds[0]

        # Parse the submission from embed fields
        service_data = self.parse_submission_embed(embed)
        if not service_data:
            logger.warning("Could not parse service submission embed")
            return

        # Add to the Gist
        success = await self.add_service_to_gist(service_data)

        # React and reply with error handling
        try:
            if success:
                # Add a checkmark reaction to confirm
                await message.add_reaction("\U0001F4BE")  # Floppy disk emoji to show saved
                # Reply to confirm
                await message.reply(f"Service listing for **{service_data.get('name', 'Unknown')}** has been approved and published!", mention_author=False)
                logger.info(f"Approved service listing: {service_data.get('name')}")
            else:
                await message.reply("Error: Could not publish service listing. Check bot logs.", mention_author=False)
        except discord.NotFound:
            logger.warning("Message was deleted before we could reply")
        except discord.Forbidden:
            logger.warning("Bot lacks permission to react or reply")
        except Exception as e:
            logger.exception(f"Error reacting/replying to approval: {e}")

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
                    # Parse platforms list
                    service["platforms"] = [p.strip() for p in value.split(",")]
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
