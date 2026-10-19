"""Removal-command regressions with the real Config and inert service boundaries."""
import asyncio
import importlib.util
import json
import logging
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def identity_decorator(**kwargs):
    return lambda callback: callback


class InertCog:
    @staticmethod
    def listener():
        return identity_decorator()


def load_actual_classes():
    """Import complete production modules without initializing Discord or HTTP."""
    discord = types.ModuleType("discord")
    discord.Interaction = discord.Message = discord.RawReactionActionEvent = object
    discord.Embed = object
    discord.ButtonStyle = types.SimpleNamespace(green=1, red=2)
    discord.ui = types.ModuleType("discord.ui")
    discord.ui.View = discord.ui.Button = object
    discord.ui.button = identity_decorator
    discord.app_commands = types.ModuleType("discord.app_commands")
    discord.app_commands.command = discord.app_commands.describe = identity_decorator
    discord.ext = types.ModuleType("discord.ext")
    discord.ext.commands = types.ModuleType("discord.ext.commands")
    discord.ext.commands.Cog = InertCog
    aiohttp = types.ModuleType("aiohttp")

    def forbid_session():
        raise AssertionError("A real HTTP session must not be constructed")

    aiohttp.ClientSession = forbid_session
    utils = types.ModuleType("utils")
    json_file = types.ModuleType("utils.jsonFile")
    json_file.fileHelper = lambda path: None
    modules = [discord, discord.ui, discord.app_commands, discord.ext,
               discord.ext.commands, aiohttp, utils, json_file]
    with patch.dict(sys.modules, {module.__name__: module for module in modules}):
        config = load_module("services_test_config", ROOT / "NinjaBot/utils/config.py")
        services = load_module("services_test_cog", ROOT / "NinjaBot/cogs/NinjaServices.py")
    return config.Config, services.NinjaServices


Config, NinjaServices = load_actual_classes()


class InertResponse:
    def __init__(self, status=200, data=None, error=None):
        self.status = status
        self.data = data
        self.error = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def json(self, **kwargs):
        if self.error:
            raise self.error
        return self.data


class InertHttp:
    def __init__(self, replies=()):
        self.replies = list(replies)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if not self.replies:
            raise AssertionError("Unexpected HTTP request")
        return self.replies.pop(0)

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def patch(self, url, **kwargs):
        return self.request("PATCH", url, **kwargs)


class RemoveServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.log_patch = patch.object(logging.getLogger("NinjaBot.services_test_cog"), "exception")
        self.log_patch.start()
        self.addCleanup(self.log_patch.stop)

    def create(self, approvers, replies=(), user_id=123, configured=True):
        config = Config("unused.json")
        config._configOptions = {
            "githubApiKey": "synthetic-test-value",
            "servicesGistId": "synthetic-gist",
        }
        if configured:
            config._configOptions["servicesApprovers"] = approvers
        cog = object.__new__(NinjaServices)
        cog.bot = types.SimpleNamespace(config=config)
        cog.http = InertHttp(replies)
        cog.gist_lock = asyncio.Lock()
        interaction = types.SimpleNamespace(
            user=types.SimpleNamespace(id=user_id),
            response=types.SimpleNamespace(send_message=AsyncMock(), defer=AsyncMock()),
            followup=types.SimpleNamespace(send=AsyncMock()),
        )
        return cog, interaction

    def gist_response(self):
        return InertResponse(data={"files": {"services.json": {
            "raw_url": "https://example.invalid/services.json"
        }}})

    async def assert_denied(self, approvers, configured=True):
        cog, interaction = self.create(approvers, configured=configured)
        await cog.remove_service(interaction, "example")
        interaction.response.send_message.assert_awaited_once_with(
            "You don't have permission to remove service listings.", ephemeral=True)
        interaction.response.defer.assert_not_awaited()
        interaction.followup.send.assert_not_awaited()
        self.assertEqual(cog.http.calls, [])
        self.assertFalse(cog.gist_lock.locked())

    async def test_other_user_is_denied_without_io(self):
        await self.assert_denied(["456"])

    async def test_missing_approvers_are_denied_without_io(self):
        await self.assert_denied(None, configured=False)

    async def test_empty_approvers_are_denied_without_io(self):
        await self.assert_denied([])

    async def test_null_approvers_are_denied_without_io(self):
        await self.assert_denied(None)

    async def test_numeric_entry_does_not_expand_existing_string_id_contract(self):
        await self.assert_denied([123])

    async def test_reviewer_removes_case_insensitive_match_and_preserves_others(self):
        original = {"services": [
            {"id": "a", "discord": "Example", "name": "Example Studio"},
            {"id": "b", "discord": "other", "name": "Other Studio"},
        ], "disclaimer": "retain this", "lastUpdated": "2020-01-01"}
        cog, interaction = self.create(["123"], [
            self.gist_response(), InertResponse(data=original), InertResponse()])
        await cog.remove_service(interaction, "eXaMpLe")
        interaction.response.defer.assert_awaited_once_with(ephemeral=True)
        interaction.response.send_message.assert_not_awaited()
        self.assertEqual([call[0] for call in cog.http.calls], ["GET", "GET", "PATCH"])
        content = cog.http.calls[-1][2]["json"]["files"]["services.json"]["content"]
        updated = json.loads(content)
        self.assertEqual(updated["services"], [
            {"id": "b", "discord": "other", "name": "Other Studio"}])
        self.assertEqual(updated["disclaimer"], "retain this")
        self.assertNotEqual(updated["lastUpdated"], "2020-01-01")
        interaction.followup.send.assert_awaited_once_with(
            "Successfully removed service listing for: eXaMpLe", ephemeral=True)
        self.assertFalse(cog.gist_lock.locked())

    async def test_reviewer_can_remove_last_listing(self):
        cog, interaction = self.create(["123"], [self.gist_response(),
            InertResponse(data={"services": [{"discord": "example"}]}), InertResponse()])
        await cog.remove_service(interaction, "example")
        content = cog.http.calls[-1][2]["json"]["files"]["services.json"]["content"]
        self.assertEqual(json.loads(content)["services"], [])

    async def test_no_match_does_not_patch(self):
        cog, interaction = self.create(["123"], [self.gist_response(),
            InertResponse(data={"services": [{"discord": "other"}]})])
        await cog.remove_service(interaction, "example")
        self.assertEqual([call[0] for call in cog.http.calls], ["GET", "GET"])
        interaction.followup.send.assert_awaited_once_with(
            "No service listing found for Discord user: example", ephemeral=True)

    async def test_failed_gist_fetch_does_not_patch(self):
        cog, interaction = self.create(["123"], [InertResponse(status=503)])
        await cog.remove_service(interaction, "example")
        self.assertEqual(len(cog.http.calls), 1)
        interaction.followup.send.assert_awaited_once_with("Failed to fetch services data.", ephemeral=True)

    async def test_missing_services_file_does_not_patch(self):
        cog, interaction = self.create(["123"], [InertResponse(data={"files": {}})])
        await cog.remove_service(interaction, "example")
        self.assertEqual(len(cog.http.calls), 1)
        interaction.followup.send.assert_awaited_once_with(
            "Gist structure invalid - missing services.json", ephemeral=True)

    async def test_json_failure_is_reported_and_releases_lock(self):
        cog, interaction = self.create(["123"], [self.gist_response(),
            InertResponse(error=ValueError("synthetic parse failure"))])
        await cog.remove_service(interaction, "example")
        self.assertEqual(len(cog.http.calls), 2)
        interaction.followup.send.assert_awaited_once_with("Error: synthetic parse failure", ephemeral=True)
        self.assertFalse(cog.gist_lock.locked())

    async def test_failed_patch_does_not_report_success(self):
        cog, interaction = self.create(["123"], [self.gist_response(),
            InertResponse(data={"services": [{"discord": "example"}]}), InertResponse(status=500)])
        await cog.remove_service(interaction, "example")
        self.assertEqual([call[0] for call in cog.http.calls], ["GET", "GET", "PATCH"])
        interaction.followup.send.assert_awaited_once_with("Failed to update services data.", ephemeral=True)


if __name__ == "__main__":
    unittest.main()
