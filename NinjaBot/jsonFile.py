import aiofile
import json
import logging

logger = logging.getLogger("NinjaBot." + __name__)

class fileHelper:
    """A simple helper class to read and save json from files"""
    def __init__(self, filename) -> None:
        self._filename = filename

    async def write(self, data: dict) -> None:
        """dump 'data' to the json file"""
        logger.debug("writing data to json file")
        try:
            async with aiofile.async_open(self._filename, mode="w") as f:
                await f.write(json.dumps(data, indent=4))
        except Exception as E:
            logger.exception(E)
            raise E

    async def read(self) -> dict:
        """try to read from json file and return it"""
        logger.debug("reading from json file")
        try:
            async with aiofile.async_open(self._filename, mode="r") as f:
                data = await f.read()
            return json.loads(data)
        except Exception as E:
            logger.exception(E)
            raise E