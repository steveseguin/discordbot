from discord import Embed

class ninjaEmbed(Embed):
    def __init__(self, description: str="", title: str=None):
        # for now this doesn't do much
        # but we can configure a color or unified look here
        super().__init__(description=description, title=title)