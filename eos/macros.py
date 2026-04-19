"""Macro-related functionality."""

import logging
import time
from abc import ABC
from decimal import Decimal

from eos.base import EosBase
from eos.helpers import EosException, EosTab
from eos.iterator import EosMacroIterator

logger = logging.getLogger(__name__)


class EosMacros(ABC, EosBase):
    """Mixin for macro-related actions."""

    def __init__(self) -> None:
        self.macro = EosMacroIterator(self)

        super().__init__()

    def record_macro(self, macro: Decimal, commands: list[str]) -> None:
        """Record a macro with a given command sequence."""
        # TODO not working lol
        self.open_tab(EosTab.MACROS)
        try:
            self.macro.get(macro)
        except EosException:
            logger.info("Recording new macro %f", macro)
            self.send_command(str(macro) + "#")
            self.press_key("softkey_6")
            time.sleep(0.1)
            for i in commands:
                self.press_key(i)
            self.press_key("Select")
        else:
            raise EosException(f"Macro {macro} already exists!")
