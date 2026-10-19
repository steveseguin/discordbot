"""Offline lifecycle regressions using the actual NinjaBot class and inert Discord APIs.

Run with: python -m unittest discover -s tests -p 'test_startup_recovery.py' -v
No Discord connection, credentials, cog side effects, or network are used.
"""
import ast
import asyncio
import logging
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock


EXTENSIONS = (
    'cogs.NinjaBotUtils', 'cogs.NinjaAntiSpam', 'cogs.NinjaBotHelp',
    'cogs.NinjaGithub', 'cogs.NinjaDynCmds', 'cogs.NinjaReddit',
    'cogs.NinjaYoutube', 'cogs.NinjaUpdates', 'cogs.NinjaThreadManager',
    'cogs.NinjaServices',
)
THREAD_MANAGER = 'cogs.NinjaThreadManager'


class ExtensionAlreadyLoaded(Exception):
    pass


class OfflineBot:
    """Only the Bot API seams used by the selected lifecycle methods."""
    def __init__(self, **kwargs):
        self.extensions = {}
        self.user = 'offline-bot'
        self.loads = []
        self.reloads = []
        self.fail_load = None
        self.fail_reload = None
        self.fail_sync = False
        self.pause_name = None
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.active = 0
        self.max_active = 0
        self.presence = []
        self.syncs = 0
        self.tree = SimpleNamespace(copy_global_to=lambda **kw: None,
                                    sync=self.sync, on_error=None)

    async def load_extension(self, name):
        # discord.py 2.6.3 rejects names already in the extensions mapping.
        if name in self.extensions:
            raise ExtensionAlreadyLoaded(name)
        self.loads.append(name)
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(0)
            if name == self.pause_name:
                self.entered.set()
                await self.release.wait()
            if name == self.fail_load:
                self.fail_load = None
                raise OSError('synthetic initialization failure')
            self.extensions[name] = object()
        finally:
            self.active -= 1

    async def reload_extension(self, name):
        self.reloads.append(name)
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(0)
            if name == self.fail_reload:
                self.fail_reload = None
                raise OSError('synthetic reload failure')
            # A failed reload preserves the previous extension in discord.py.
            self.extensions[name] = object()
        finally:
            self.active -= 1

    async def sync(self, **kwargs):
        self.syncs += 1
        await asyncio.sleep(0)
        if self.fail_sync:
            self.fail_sync = False
            raise OSError('synthetic sync failure')

    async def change_presence(self, **kwargs):
        self.presence.append(kwargs)


def load_bot():
    path = Path(os.environ.get('NINJABOT_MAIN',
                str(Path(__file__).resolve().parents[1] / 'NinjaBot/main.py')))
    module = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    cls = next(n for n in module.body if isinstance(n, ast.ClassDef) and n.name == 'NinjaBot')
    # Execute the complete, unmodified class, excluding import-time logging/config IO.
    namespace = {
        'asyncio': asyncio, 'commands': SimpleNamespace(Bot=OfflineBot),
        'discord': SimpleNamespace(Message=object, Interaction=object,
                    Object=lambda **kw: SimpleNamespace(**kw),
                    Status=SimpleNamespace(online='online'), Game=lambda name: name),
        'logger': logging.getLogger('offline-startup-test'),
        'intents': object(), 'mentions': object(),
    }
    exec(compile(ast.Module(body=[cls], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace['NinjaBot'](SimpleNamespace(get={'commandPrefix': '!', 'guild': '123'}.get))


class StartupRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_clean_startup_loads_order_and_syncs(self):
        bot = load_bot()
        await bot.on_ready()
        self.assertEqual(bot.loads, list(EXTENSIONS))
        self.assertEqual(bot.syncs, 1)
        self.assertEqual(bot.tree.on_error, bot.on_app_command_error)
        self.assertEqual(len(bot.presence), 1)

    async def test_repeated_ready_does_not_reload_cogs(self):
        bot = load_bot()
        await bot.on_ready()
        installed = dict(bot.extensions)
        await bot.on_ready()
        await bot.on_ready()
        self.assertEqual(bot.loads, list(EXTENSIONS))
        self.assertEqual(bot.extensions, installed)
        self.assertEqual(bot.reloads, [])
        self.assertEqual(bot.syncs, 3)

    async def test_each_failed_initial_extension_recovers_on_ready(self):
        for index, name in enumerate(EXTENSIONS):
            with self.subTest(extension=name):
                bot = load_bot()
                bot.fail_load = name
                with self.assertRaises(OSError):
                    await bot.on_ready()
                self.assertEqual(list(bot.extensions), list(EXTENSIONS[:index]))
                installed = dict(bot.extensions)
                self.assertEqual(bot.syncs, 0)
                await bot.on_ready()
                self.assertEqual(list(bot.extensions), list(EXTENSIONS))
                self.assertEqual(bot.syncs, 1)
                for previous in installed:
                    self.assertIs(bot.extensions[previous], installed[previous])

    async def test_update_restores_cogs_missing_after_github_failure(self):
        bot = load_bot()
        bot.fail_load = 'cogs.NinjaGithub'
        with self.assertRaises(OSError):
            await bot.on_ready()
        ctx = SimpleNamespace(send=AsyncMock())
        await bot.reloadExtensions(ctx)
        self.assertEqual(list(bot.extensions), list(EXTENSIONS))
        self.assertEqual(bot.reloads, list(EXTENSIONS[:3]))
        self.assertEqual(bot.syncs, 1)
        ctx.send.assert_any_await('Successfully reloaded bot extensions')

    async def test_update_loads_missing_thread_manager(self):
        bot = load_bot()
        bot.fail_load = THREAD_MANAGER
        with self.assertRaises(OSError):
            await bot.on_ready()
        await bot.reloadExtensions(SimpleNamespace(send=AsyncMock()))
        self.assertIn(THREAD_MANAGER, bot.extensions)
        self.assertIn('cogs.NinjaServices', bot.extensions)
        self.assertNotIn(THREAD_MANAGER, bot.reloads)

    async def test_update_preserves_existing_thread_manager(self):
        bot = load_bot()
        await bot.on_ready()
        thread_manager = bot.extensions[THREAD_MANAGER]
        await bot.reloadExtensions(SimpleNamespace(send=AsyncMock()))
        self.assertIs(bot.extensions[THREAD_MANAGER], thread_manager)
        self.assertEqual(bot.reloads, [n for n in EXTENSIONS if n != THREAD_MANAGER])
        self.assertEqual(bot.syncs, 2)

    async def test_update_preserves_reload_of_existing_extra_extensions(self):
        bot = load_bot()
        await bot.on_ready()
        bot.extensions['cogs.Extra'] = object()
        await bot.reloadExtensions(SimpleNamespace(send=AsyncMock()))
        self.assertIn('cogs.Extra', bot.reloads)

    async def test_sync_failure_can_recover_without_reloading(self):
        bot = load_bot()
        bot.fail_sync = True
        with self.assertRaises(OSError):
            await bot.on_ready()
        installed = dict(bot.extensions)
        await bot.on_ready()
        self.assertEqual(bot.extensions, installed)
        self.assertEqual(bot.loads, list(EXTENSIONS))
        self.assertEqual(bot.syncs, 2)
        self.assertEqual(bot.tree.on_error, bot.on_app_command_error)

    async def test_update_sync_failure_does_not_report_success(self):
        bot = load_bot()
        await bot.on_ready()
        bot.fail_sync = True
        ctx = SimpleNamespace(send=AsyncMock())
        await bot.reloadExtensions(ctx)
        messages = [str(call.args[0]) for call in ctx.send.await_args_list]
        self.assertNotIn('Successfully reloaded bot extensions', messages)
        self.assertIn('There was an error while reloading bot extensions:', messages)
        await bot.on_ready()
        self.assertEqual(bot.syncs, 3)

    async def test_reload_failure_preserves_loaded_set_and_reports_error(self):
        bot = load_bot()
        await bot.on_ready()
        bot.fail_reload = 'cogs.NinjaGithub'
        ctx = SimpleNamespace(send=AsyncMock())
        await bot.reloadExtensions(ctx)
        self.assertEqual(list(bot.extensions), list(EXTENSIONS))
        messages = [str(call.args[0]) for call in ctx.send.await_args_list]
        self.assertNotIn('Successfully reloaded bot extensions', messages)
        await bot.reloadExtensions(ctx)
        self.assertEqual(bot.syncs, 2)

    async def test_concurrent_ready_events_do_not_overlap_extension_loads(self):
        bot = load_bot()
        await asyncio.gather(bot.on_ready(), bot.on_ready())
        self.assertEqual(bot.loads, list(EXTENSIONS))
        self.assertEqual(bot.max_active, 1)
        self.assertEqual(bot.syncs, 2)

    async def test_ready_and_update_are_serialized(self):
        bot = load_bot()
        bot.pause_name = 'cogs.NinjaGithub'
        ready = asyncio.create_task(bot.on_ready())
        await bot.entered.wait()
        update = asyncio.create_task(bot.reloadExtensions(SimpleNamespace(send=AsyncMock())))
        await asyncio.sleep(0)
        bot.release.set()
        await asyncio.gather(ready, update)
        self.assertEqual(bot.max_active, 1)
        self.assertEqual(bot.loads, list(EXTENSIONS))
        self.assertEqual(bot.reloads, [n for n in EXTENSIONS if n != THREAD_MANAGER])
        self.assertEqual(bot.syncs, 2)

    async def test_cancelled_initial_load_releases_lock_for_ready_retry(self):
        bot = load_bot()
        bot.pause_name = 'cogs.NinjaGithub'
        first = asyncio.create_task(bot.on_ready())
        await bot.entered.wait()
        first.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first
        bot.pause_name = None
        await bot.on_ready()
        self.assertEqual(list(bot.extensions), list(EXTENSIONS))
        self.assertEqual(bot.syncs, 1)

    async def test_persistent_failure_still_propagates_without_false_ready(self):
        bot = load_bot()
        for _ in range(2):
            bot.fail_load = 'cogs.NinjaGithub'
            with self.assertRaises(OSError):
                await bot.on_ready()
        self.assertEqual(list(bot.extensions), list(EXTENSIONS[:3]))
        self.assertEqual(bot.presence, [])
        self.assertEqual(bot.syncs, 0)


if __name__ == '__main__':
    unittest.main()
