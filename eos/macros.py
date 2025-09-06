import logging
import time
from typing import Any, List

from eos.base import EosBase
from eos.types import EosException, EosTab, MacroProperties

logger = logging.getLogger(__name__)


class EosMacros(EosBase):
    def get_macro(self, macro: float) -> MacroProperties:
        macro_data_count = 0
        macro_props = None
        macro_text = None

        def handler(addr: str, *args: List[Any]) -> None:
            nonlocal macro_data_count
            macro_data_count += 1

            if "text" in addr:
                nonlocal macro_text
                macro_text = args[2:]
            else:
                nonlocal macro_props
                macro_props = args

        filter = self.dispatcher.map(f"/eos/out/get/macro/{macro:g}*", handler)
        self.write(f"/eos/get/macro/{macro:g}")
        self.handle_messages()

        if macro_data_count != 2:
            raise EosException(
                f"Didn't receive all data for macro ({macro_data_count})"
            )

        self.dispatcher.unmap(f"/eos/out/get/macro/{macro:g}*", filter)
        return MacroProperties.from_list(macro, macro_props, macro_text)

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
