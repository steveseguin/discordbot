from discord import Embed

def createEmbed(name: str="\u200b", formatName: bool=False, text: str="") -> Embed:
    embed = Embed(description=text)
    if formatName:
        name = f"{name[0].upper()}{name[1:]}:"
    #embed.add_field(name=name, value=text)
    return embed