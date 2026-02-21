"""Configuration for Pokemon HeartGold and SoulSilver."""

from .base import GameConfig, TextboxConfig


class HGSSConfig(GameConfig):
    """Configuration for Pokemon HeartGold and SoulSilver."""

    @property
    def name(self) -> str:
        return "Pokemon HeartGold/SoulSilver"

    @property
    def standard_textbox(self) -> TextboxConfig:
        # HG/SS has a slightly different textbox style
        # These values need verification from actual game
        return TextboxConfig(
            x=8,
            y=144,
            width=240,
            height=48,
            text_x=13,
            text_y=152,
            text_width=220,
            text_height=33,
            line_height=16
        )

    # HG/SS may have different textbox frames/styles
    # TODO: Verify exact coordinates from game


# Singleton instance
config = HGSSConfig()
