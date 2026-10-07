"""Offline tests for the actual update-channel cog; no Discord/GitHub I/O."""

import ast
import asyncio
from copy import deepcopy
from datetime import datetime
from functools import partial
import json
import logging
from pathlib import Path
import re
import types
import unittest


def load_cog():
    source = Path(__file__).resolve().parents[1] / "NinjaBot/cogs/NinjaUpdates.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    cog = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    for node in cog.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            node.decorator_list = []
    namespace = {
        "asyncio": asyncio,
        "aiohttp": types.SimpleNamespace(ClientSession=lambda: None),
        "commands": types.SimpleNamespace(Cog=object),
        "discord": types.SimpleNamespace(Message=object),
        "datetime": datetime,
        "partial": partial,
        "json": json,
        "re": re,
        "logger": logging.getLogger("updates-test"),
    }
    exec(compile(ast.Module(body=[cog], type_ignores=[]), str(source), "exec"), namespace)
    return namespace["NinjaUpdates"]


class Config:
    def __init__(self):
        self.values = dict(updatesChannel="10", allowedUpdateUsers=["20"],
                           githubApiKey="synthetic", githubGistId="synthetic")

    def get(self, key):
        return self.values.get(key)

    def has(self, key):
        return key in self.values


def message(identifier, content=None):
    return types.SimpleNamespace(
        id=identifier, content=content or f"Update {identifier}",
        channel=types.SimpleNamespace(id=10),
        author=types.SimpleNamespace(id=20, name="Example", nick=None,
                                     display_avatar=types.SimpleNamespace(url="avatar")),
        attachments=[], channel_mentions=[], mentions=[])


class Response:
    def __init__(self, value, status=200, enter=None):
        self.value, self.status, self.enter = value, status, enter

    async def __aenter__(self):
        if self.enter:
            await self.enter()
        return self

    async def __aexit__(self, *args):
        return False

    async def json(self, **kwargs):
        return deepcopy(self.value)

    async def text(self):
        return "synthetic HTTP failure"


class Gist:
    """Inert versioned snapshots and full-file replacement, matching the cog API."""
    def __init__(self, rows=None):
        self.rows = deepcopy(rows or [dict(msgid="0", content="Old", timestamp=0)])
        self.snapshots = []
        self.patch_started = asyncio.Event()
        self.release_patch = asyncio.Event()
        self.patch_calls = 0
        self.active_patches = 0
        self.max_active_patches = 0
        self.block_first = True
        self.first_failure = None
        self.get_status = 200
        self.content_status = 200
        self.closed = False

    def get(self, url, **kwargs):
        if url.startswith("https://api.github.com/gists/"):
            self.snapshots.append(deepcopy(self.rows))
            return Response({"files": {"updates.json": {"raw_url": f"raw:{len(self.snapshots)-1}"}}}, self.get_status)
        return Response(self.snapshots[int(url.split(":")[1])], self.content_status)

    def patch(self, url, *, json, **kwargs):
        self.patch_calls += 1
        ordinal = self.patch_calls
        rows = __import__("json").loads(json["files"]["updates.json"]["content"])

        async def enter():
            self.active_patches += 1
            self.max_active_patches = max(self.max_active_patches, self.active_patches)
            try:
                if ordinal == 1 and self.block_first:
                    self.patch_started.set()
                    await self.release_patch.wait()
                if ordinal == 1 and isinstance(self.first_failure, BaseException):
                    raise self.first_failure
                if not (ordinal == 1 and self.first_failure == "http"):
                    self.rows = deepcopy(rows)
            finally:
                self.active_patches -= 1

        return Response(None, 500 if ordinal == 1 and self.first_failure == "http" else 200, enter)

    async def close(self):
        self.closed = True


class UpdatesTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = types.SimpleNamespace(config=Config())
        self.cog = load_cog()(self.bot)
        self.cog.http = self.gist = Gist()

    async def overlap(self, first, second):
        first_task = asyncio.create_task(first())
        await self.gist.patch_started.wait()
        second_task = asyncio.create_task(second())
        # Let the second handler reach the held lock or finish its unguarded write.
        for _ in range(10):
            await asyncio.sleep(0)
        self.gist.release_patch.set()
        return await asyncio.gather(first_task, second_task, return_exceptions=True)

    async def test_overlapping_posts_keep_both_entries(self):
        results = await self.overlap(lambda: self.cog.on_message(message(1)),
                                     lambda: self.cog.on_message(message(2)))
        self.assertEqual(results, [None, None])
        self.assertEqual({row["msgid"] for row in self.gist.rows}, {"0", "1", "2"})
        self.assertEqual(self.gist.max_active_patches, 1)

    async def test_raw_edit_and_new_post_both_survive(self):
        async def fetch_message(identifier):
            return message(identifier, "Edited")
        self.bot.get_channel = lambda identifier: types.SimpleNamespace(fetch_message=fetch_message)
        payload = types.SimpleNamespace(channel_id=10, message_id=0)
        await self.overlap(lambda: self.cog.on_raw_message_edit(payload),
                           lambda: self.cog.on_message(message(2)))
        rows = {row["msgid"]: row for row in self.gist.rows}
        self.assertEqual(set(rows), {"0", "2"})
        self.assertEqual(rows["0"]["content"], "Edited")
        self.assertEqual(rows["0"]["timestamp"], 0)

    async def test_latest_queued_edit_survives(self):
        await self.overlap(lambda: self.cog.on_message(message(0, "First edit")),
                           lambda: self.cog.on_message(message(0, "Second edit")))
        self.assertEqual(len(self.gist.rows), 1)
        self.assertEqual(self.gist.rows[0]["content"], "Second edit")

    async def test_failed_patch_releases_next_post(self):
        self.gist.first_failure = RuntimeError("synthetic transport error")
        results = await self.overlap(lambda: self.cog.on_message(message(1)),
                                     lambda: self.cog.on_message(message(2)))
        self.assertIsInstance(results[0], RuntimeError)
        self.assertIsNone(results[1])
        self.assertEqual({row["msgid"] for row in self.gist.rows}, {"0", "2"})

    async def test_http_patch_failure_releases_next_post(self):
        self.gist.first_failure = "http"
        await self.overlap(lambda: self.cog.on_message(message(1)),
                           lambda: self.cog.on_message(message(2)))
        self.assertEqual({row["msgid"] for row in self.gist.rows}, {"0", "2"})

    async def test_cancellation_releases_next_post(self):
        first = asyncio.create_task(self.cog.on_message(message(1)))
        await self.gist.patch_started.wait()
        first.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first
        await self.cog.on_message(message(2))
        self.assertEqual({row["msgid"] for row in self.gist.rows}, {"0", "2"})

    async def test_read_failure_then_success(self):
        self.gist.get_status = 503
        await self.cog.on_message(message(1))
        self.assertEqual(self.gist.patch_calls, 0)
        self.gist.get_status = 200
        self.gist.content_status = 503
        await self.cog.on_message(message(1))
        self.assertEqual(self.gist.patch_calls, 0)
        self.gist.content_status = 200
        self.gist.block_first = False
        await self.cog.on_message(message(2))
        self.assertEqual({row["msgid"] for row in self.gist.rows}, {"0", "2"})

    async def test_unrelated_messages_never_fetch(self):
        wrong_channel, wrong_author = message(1), message(2)
        wrong_channel.channel.id = 99
        wrong_author.author.id = 99
        await self.cog.on_message(wrong_channel)
        await self.cog.on_message(wrong_author)
        self.bot.config.values.pop("githubApiKey")
        await self.cog.on_message(message(3))
        self.assertEqual(self.gist.snapshots, [])

    async def test_retention_and_existing_metadata_preserved(self):
        self.gist.rows = [dict(msgid=str(i), timestamp=i, content="old", name="Kept") for i in range(75)]
        self.gist.block_first = False
        await self.cog.on_message(message(74, "Edited"))
        self.assertEqual(len(self.gist.rows), 70)
        self.assertEqual(self.gist.rows[0]["msgid"], "5")
        self.assertEqual(self.gist.rows[-1]["name"], "Kept")
        self.assertEqual(self.gist.rows[-1]["timestamp"], 74)


if __name__ == "__main__":
    unittest.main()
