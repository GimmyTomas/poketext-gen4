"""Configuration for Pokemon Diamond and Pearl."""

from .base import GameConfig, TextboxConfig


class DiamondPearlConfig(GameConfig):
    """Configuration for Pokemon Diamond and Pearl."""

    @property
    def name(self) -> str:
        return "Pokemon Diamond/Pearl"

    @property
    def standard_textbox(self) -> TextboxConfig:
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

    @property
    def has_large_text(self) -> bool:
        # Diamond/Pearl have large text in the intro sequence
        return True

    @property
    def large_textbox(self) -> TextboxConfig:
        # Large text appears during Professor Rowan's intro
        # Different dimensions - needs verification
        return TextboxConfig(
            x=8,
            y=144,
            width=240,
            height=48,
            text_x=13,
            text_y=152,
            text_width=220,
            text_height=33,
            line_height=20  # Larger line height for big text
        )


# Singleton instance
config = DiamondPearlConfig()
