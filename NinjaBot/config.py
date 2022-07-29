import logging
from jsonFile import fileHelper

logger = logging.getLogger("NinjaBot." + __name__)

class Config:
    """A helper class to handle the bot config file"""
    def __init__(self, file: str) -> None:
        self._fh = fileHelper(file)
        self._configOptions = None

    async def parse(self) -> None:
        """read config file"""
        self._configOptions = await self._fh.read()

    def get(self, key):
        """return a config option by the given key"""
        return self._configOptions[key]

    async def set(self, key, newVal) -> None:
        """set a config option to a new value + trigger flush"""
        self._configOptions[key] = newVal
        logger.debug(f"changed {key} to {newVal}")
        await self._flushToFile()
    
    async def _flushToFile(self) -> None:
        """Write config options from memory to file"""
        self._fh.write(self._configOptions)