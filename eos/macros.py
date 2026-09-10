"""Macro-related functionality."""

import logging
import time
from decimal import Decimal
from typing import TYPE_CHECKING

from eos.helpers import EosError, EosTab
from eos.iterator import EosMacroIterator

if TYPE_CHECKING:
    from eos.eos import Eos

logger = logging.getLogger(__name__)


class EosMacros:
    """Mixin for macro-related actions."""

    def __init__(self, eos: "Eos") -> None:
        self.eos = eos
        self.iterator = EosMacroIterator(eos)

        super().__init__()

    def record_macro(self, macro: Decimal, commands: list[str]) -> None:
        """Record a macro with a given command sequence."""
        # TODO not working lol
        self.eos.keys.open_tab(EosTab.MACROS)
        try:
            self.iterator.get(macro)
        except EosError:
            logger.info("Recording new macro %f", macro)
            self.eos.send_command(str(macro) + "#")
            self.eos.keys.press_key("softkey_6")
            time.sleep(0.1)
            for i in commands:
                self.eos.keys.press_key(i)
            self.eos.keys.press_key("Select")
        else:
            raise EosError(f"Macro {macro} already exists!")
