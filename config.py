import aiofile
import json

class Config:
    def __init__(self, file: str) -> None:
        self._configFile = file
        self.botToken = None

    async def parse(self):
        try:
            async with aiofile.async_open(self._configFile, mode="r") as f:
                data = await f.read()
            data = json.loads(data)
            for key in data:
                setattr(self, key, data[key])
        except Exception as E:
            raise E