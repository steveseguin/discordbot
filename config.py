import aiofiles
import json

class Config:
    def __init__(self, file: str) -> None:
        self._configFile = file
        self.botToken = None

    async def parse(self):
        try:
            async with aiofiles.open(self._configFile, mode="r") as f:
                data = await f.read()
            data = json.loads(data)
            self.botToken = data["botToken"]
        except Exception as E:
            raise E