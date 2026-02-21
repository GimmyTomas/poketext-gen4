"""Configuration for Pokemon Platinum."""

from .base import GameConfig, TextboxConfig


class PlatinumConfig(GameConfig):
    """Configuration for Pokemon Platinum."""

    @property
    def name(self) -> str:
        return "Pokemon Platinum"

    @property
    def standard_textbox(self) -> TextboxConfig:
        # Platinum uses similar textbox to Diamond/Pearl
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

    # Note: Platinum has one section where bottom screen matters
    # This will need special handling


# Singleton instance
config = PlatinumConfig()
