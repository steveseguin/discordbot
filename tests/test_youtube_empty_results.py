"""Offline polling tests; execute the actual method without loading Discord or Google SDKs."""
import ast
import logging
from pathlib import Path
from types import SimpleNamespace
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock


def load_checker():
    source = Path(__file__).resolve().parents[1] / "NinjaBot/cogs/NinjaYoutube.py"
    tree = ast.parse(source.read_text(encoding="utf8"), filename=str(source))
    cog = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "NinjaYoutube")
    method = next(node for node in cog.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "youtubeChecker")
    method.decorator_list = []

    async def execute(_executor, callback):
        return callback()

    namespace = {
        "logger": logging.getLogger("youtube-offline-test"),
        "asyncio": SimpleNamespace(get_event_loop=lambda: SimpleNamespace(run_in_executor=execute)),
        "datetime": datetime, "timezone": timezone, "timedelta": timedelta,
        "sleep": AsyncMock(),
    }
    module = ast.Module(body=[method], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(source), "exec"), namespace)
    return namespace["youtubeChecker"]


class YoutubePollingTests(unittest.IsolatedAsyncioTestCase):
    async def poll(self, response):
        values = {"youtubePostedVideo": ["already-posted"], "youtubeDiscordChannel": "123", "youtubeChannelId": "synthetic"}
        config = SimpleNamespace(get=values.get, set=AsyncMock())
        channel = SimpleNamespace(send=AsyncMock())
        request = SimpleNamespace(execute=lambda: response)
        youtube = SimpleNamespace(search=lambda: SimpleNamespace(list=lambda **kwargs: request))
        cog = SimpleNamespace(youtube=youtube, bot=SimpleNamespace(config=config, get_channel=lambda _id: channel))
        await load_checker()(cog)
        return config, channel

    async def test_empty_or_incomplete_results_are_a_no_op(self):
        for response in (None, {}, {"kind": "youtube#searchListResponse"}, {"kind": "youtube#searchListResponse", "items": []}):
            with self.subTest(response=response):
                config, channel = await self.poll(response)
                channel.send.assert_not_awaited()
                config.set.assert_not_awaited()

    async def test_normal_results_remain_oldest_first_and_are_persisted(self):
        def video(identifier):
            return {"kind": "youtube#searchResult", "id": {"kind": "youtube#video", "videoId": identifier},
                    "snippet": {"description": "Synthetic description", "title": "Synthetic title",
                                "publishedAt": datetime.now(timezone.utc).isoformat()}}
        config, channel = await self.poll({"kind": "youtube#searchListResponse", "items": [video("newer"), video("older")]})
        self.assertEqual([call.args[0].split("v=")[-1] for call in channel.send.await_args_list], ["older", "newer"])
        config.set.assert_awaited_once_with("youtubePostedVideo", ["already-posted", "older", "newer"])


if __name__ == "__main__":
    unittest.main()
