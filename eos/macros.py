import logging
import time
from typing import Any, List

from eos.base import EosBase
from eos.types import EosException, EosTab, MacroProperties

logger = logging.getLogger(__name__)


class EosMacros(EosBase):
    def record_macro(self, macro: float, commands: List[str]):
        self.open_tab(EosTab.MACROS)
        try:
            self.get_macro(macro)
        except EosException:
            logging.info(f"Recording new macro {macro}")
            self.send_command(str(macro) + "#")
            self.press_key("softkey_6")
            time.sleep(0.1)
            # NOT WORKING
            for i in commands:
                self.press_key(i)
            self.press_key("Select")
        else:
            raise EosException(f"Macro {macro} already exists!")
