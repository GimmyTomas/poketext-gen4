"""Base class for game-specific configurations."""

from __future__ import annotations

from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Optional


@dataclass
class TextboxConfig:
    """Configuration for textbox detection."""
    # Position of textbox in DS coordinates (256x192)
    x: int
    y: int
    width: int
    height: int

    # Position of text within textbox
    text_x: int
    text_y: int
    text_width: int
    text_height: int

    # Line spacing
    line_height: int = 16


class GameConfig(ABC):
    """Base configuration for a Pokemon game."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable game name."""
        pass

    @property
    @abstractmethod
    def standard_textbox(self) -> TextboxConfig:
        """Standard dialogue textbox configuration."""
        pass

    @property
    def has_large_text(self) -> bool:
        """Whether this game has large text mode (intro sequences)."""
        return False

    @property
    def large_textbox(self) -> Optional[TextboxConfig]:
        """Large text mode textbox configuration."""
        return None

    def get_textbox_config(self, is_large: bool = False) -> TextboxConfig:
        """Get the appropriate textbox configuration."""
        if is_large and self.has_large_text and self.large_textbox:
            return self.large_textbox
        return self.standard_textbox
