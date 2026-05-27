"""Backward-compat shim. The bot originally talked to Marzban; now it talks to
3X-UI. Handler files still import ``MarzbanClient`` and inject it as a DI key
called ``marzban`` — keeping the alias avoids touching every handler.
"""
from .xui import XuiClient as MarzbanClient

__all__ = ["MarzbanClient"]
