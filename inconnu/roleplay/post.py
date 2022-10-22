"""Tupperbox-style character posting."""

import discord

import inconnu

__HELP_URL = "https://docs.inconnu.app/"


class PostModal(discord.ui.Modal):
    """A modal for getting post details."""

    def __init__(self, character: inconnu.models.VChar, *args, **kwargs):
        self.character = character
        self.header_params = {
            param: kwargs.pop(param, None)
            for param in ["blush", "location", "merits", "flaws", "temp", "hunger"]
        }
        self.mention = kwargs.pop("mention")

        # Header parameters
        self.blush = kwargs.pop("blush", None)
        self.merits = kwargs.pop("merits", None)
        self.flaws = kwargs.pop("flaws", None)
        self.temp = kwargs.pop("temp", None)

        super().__init__(*args, **kwargs)
        self.add_item(
            discord.ui.InputText(
                label="Post details",
                placeholder="Your RP post",
                min_length=1,
                max_length=4000,
                style=discord.InputTextStyle.long,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        """Set the RP post content."""
        lines = self.children[0].value.split("\n")
        cleaned = [inconnu.utils.clean_text(line) for line in lines if line]
        content = "\n\n".join(cleaned)

        # We will use a basic RP header as the base for our embed
        rp_post = inconnu.header.create(self.character, **self.header_params)
        rp_post.description += "\n\n" + content

        if self.mention:
            await interaction.response.send_message(self.mention.mention, embed=rp_post)
        else:
            await interaction.response.send_message(embed=rp_post)


async def post(ctx: discord.ApplicationContext, character: str, **kwargs):
    """Send an RP post."""
    try:
        character = await inconnu.char_mgr.fetchone(ctx.guild, ctx.user, character)
        modal = PostModal(character, title=f"{character.name}'s Post", **kwargs)
        await ctx.send_modal(modal)

    except inconnu.errors.CharacterNotFoundError as err:
        await inconnu.utils.error(ctx, err, help_url=__HELP_URL)
