import aiofile
import json
import logging

class Config:
    def __init__(self, file: str) -> None:
        self._configFile = file
        self._configOptions = None

    async def parse(self):
        try:
            async with aiofile.async_open(self._configFile, mode="r") as f:
                data = await f.read()
            self._configOptions = json.loads(data)
        except Exception as E:
            raise E

    def get(self, key):
        """return a config option by the given key"""
        return self._configOptions[key]

    async def set(self, key, newVal):
        """set a config option to a new value + trigger flush"""
        self._configOptions[key] = newVal
        logging.debug(f"changed {key} to {newVal}")
        await self._flushToFile()
    
    async def _flushToFile(self):
        """Write config options from memory to file"""
        try:
            async with aiofile.async_open(self._configFile, mode="w") as f:
                await f.write(json.dumps(self._configOptions, indent=4))
        except Exception as E:
            raise E