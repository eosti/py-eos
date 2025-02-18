import logging
import sys
import time
from abc import ABC, abstractmethod
from typing import Any, List, Optional

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_message_builder import ArgValue, build_msg
from pythonosc.osc_packet import OscPacket
from pythonosc.osc_tcp_server import MODE_1_1
from pythonosc.tcp_client import SimpleTCPClient
from pythonosc.udp_client import SimpleUDPClient

from eos_types import (
    Cue,
    CueProperties,
    EosState,
    EosTab,
    EosTargets,
    GroupProperties,
    MacroProperties,
)

logger = logging.getLogger(__name__)


class EosException(Exception):
    pass


class EosTimeout(EosException):
    pass


class Eos(ABC):
    previousCue: Cue
    currentCue: Cue
    pendingCue: Cue

    def __init__(self):
        self.write(f"/eos/sc/Connected from {sys.argv[0]}")

        self.dispatcher.map("/eos/out/user", self._updateUserHandler)
        self.dispatcher.map("/eos/out/previous/cue*", self._updatePreviousCueHandler)
        self.dispatcher.map("/eos/out/active/cue*", self._updateActiveCueHandler)
        self.dispatcher.map("/eos/out/pending/cue*", self._updatePendingCueHandler)
        self.dispatcher.map("/eos/out/show/name", self._updateShowNameHandler)
        self.dispatcher.map("/eos/out/state", self._updateStateHandler)
        self.dispatcher.map("/eos/out/locked", self._updateLockedHandler)
        # self.dispatcher.map("/eos/out/cmd", self._updateCmdHandler)
        self.dispatcher.set_default_handler(self._unhandledMessageHandler)

        logger.info("Connected to Eos v%s", self.get_version())

    @abstractmethod
    def write(self, path: str, args: Optional[List[str]]) -> None:
        pass

    @abstractmethod
    def read_next(self, timeout: int) -> OscPacket:
        pass

    @abstractmethod
    def handle_messages(self, timeout: int) -> None:
        pass

    def ping(self, message: str = ""):
        ping_flag = False

        def handler(addr: str, *args: List[Any]) -> None:
            nonlocal ping_flag
            logger.info("Pong!")
            if args[0] != message:
                logger.debug(args)
                raise EosException("Ping doesn't match pong")
            ping_flag = True

        self.write("/eos/ping", message)
        filter = self.dispatcher.map("/eos/out/ping", handler)
        self.handle_messages()
        if ping_flag is False:
            raise EosException("No ping response received")

        self.dispatcher.unmap("/eos/out/ping", filter)

    def get_version(self) -> str:
        version = None

        def handler(addr: str, *args: List[any]) -> None:
            nonlocal version
            version = args[0]

        self.write("/eos/get/version")
        filter = self.dispatcher.map("/eos/out/get/version", handler)
        self.handle_messages()
        if version is None:
            raise EosException("Did not receive version data")

        self.dispatcher.unmap("/eos/out/get/version", filter)
        return version

    def press_key(self, key: str) -> None:
        self.write(f"/eos/key/{key}")

    def send_command(self, commandline: str) -> None:
        self.write("/eos/newcmd", [commandline])

    @classmethod
    def _unhandledMessageHandler(addr: str, *args: List[any]) -> None:
        logger.debug(f"Unhandled message: {addr} {args}")

    def _updateUserHandler(self, addr: str, *args: List[Any]) -> None:
        self.user_id = int(args[0])

    def _updatePreviousCueHandler(self, addr: str, *args: List[Any]) -> None:
        if "text" in addr:
            self.previousCue = Cue.fromText(args[0])
        else:
            # Redundant info, skip it
            pass

    def _updateActiveCueHandler(self, addr: str, *args: List[Any]) -> None:
        if "text" in addr:
            self.activeCue = Cue.fromText(args[0])
        else:
            # Redundant info, skip it
            pass

    def _updatePendingCueHandler(self, addr: str, *args: List[Any]) -> None:
        if "text" in addr:
            self.pendingCue = Cue.fromText(args[0])
        else:
            # Redundant info, skip it
            pass

    def _updateShowNameHandler(self, addr: str, *args: List[Any]) -> None:
        self.show_name = args[0]

    def _updateStateHandler(self, addr: str, *args: List[Any]) -> None:
        self.eos_state = int(args[0])

    def _updateLockedHandler(self, addr: str, *args: List[Any]) -> None:
        self.is_locked = bool(args[0])

    def _updateCmdHandler(self, addr: str, *args: List[Any]) -> None:
        pass

    def _cueInfoParser(self, addr: str, args: List[Any]) -> CueProperties:
        cuelist = addr.split("/")[5]
        cue = addr.split("/")[6]
        cuepart = addr.split("/")[7]
        try:
            return CueProperties.from_list(cuelist, cue, cuepart, args)
        except IndexError:
            raise EosException(f"Cue {cuelist}/{cue} does not exist!")

    def _cueFXParser(self, addr: str, args: List[Any]):
        if len(args) <= 2:
            # No links
            return None

        logger.warning("No logic to parse FX")

    def _cueLinksParser(self, addr: str, args: List[Any]):
        if len(args) <= 2:
            # No links
            return None

        logger.warning("No logic to parse Links")

    def _cueActionsParser(self, addr: str, args: List[Any]):
        if len(args) <= 2:
            # No links
            return None

        logger.warning("No logic to parse actions")

    def get_target_count(self, target: str, **kwargs: List[str]) -> int:
        assert target in EosTargets
        if target == "cue":
            query_str = f"get/cue/{kwargs.get("cuelist", 1)}/count"
        else:
            query_str = f"get/{target}/count"

        target_count = None

        def handler(addr: str, *args: List[Any]) -> None:
            nonlocal target_count
            target_count = args[0]

        filter = self.dispatcher.map(f"/eos/out/{query_str}", handler)
        self.write("/eos/{query_str}")
        self.handle_messages()

        if target_count is None:
            raise EosException(f"Unable to get number of targets for {target}")

        self.dispatcher.unmap(f"/eos/out/{query_str}", filter)
        return target_count

    def get_cue(self, cue: Cue) -> CueProperties:
        query_str = f"get/cue/{cue.cuelist}/{cue.cue:g}/{cue.part}"
        return self._getCueQuery(query_str)

    def get_cue_by_uid(self, uid: str) -> CueProperties:
        query_str = f"get/cue/uid/{uid}"
        return self._getCueQuery(query_str)

    def get_cue_by_index(self, index: int, cuelist: int = 1) -> CueProperties:
        query_str = f"get/cue/{cuelist}/index/{index}"
        return self._getCueQuery(query_str)

    def _getCueQuery(self, query_str: str) -> CueProperties:
        cue_data_count = 0
        output_cue = None

        def handler(addr: str, *args: List[Any]) -> None:
            nonlocal cue_data_count
            nonlocal output_cue
            cue_data_count += 1

            if "fx" in addr:
                output_cue.fx = self._cueFXParser(addr, list(args))
            elif "links" in addr:
                output_cue.links2 = self._cueLinksParser(addr, list(args))
            elif "actions" in addr:
                output_cue.actions = self._cueActionsParser(addr, list(args))
            else:
                # Assume this one comes in first
                output_cue = self._cueInfoParser(addr, list(args))

        filter = self.dispatcher.map(f"/eos/out/{query_str}*", handler)
        self.write(f"/eos/{query_str}")
        self.handle_messages()
        if cue_data_count != 4:
            raise EosException(f"Didn't receive all data for cue ({cue_data_count})")
        self.dispatcher.unmap(f"/eos/out/{query_str}*", filter)
        return output_cue

    def get_group(self, group: float) -> GroupProperties:
        group_data_count = 0
        group_chans = None
        group_props = None

        def handler(addr: str, *args: List[Any]) -> None:
            nonlocal group_data_count
            group_data_count += 1

            if "channels" in addr:
                nonlocal group_chans
                group_chans = args[2:]
            else:
                nonlocal group_props
                group_props = args

        filter = self.dispatcher.map(f"/eos/out/get/group/{group:g}*", handler)
        self.write(f"/eos/get/group/{group:g}")
        self.handle_messages()

        if group_data_count != 2:
            raise EosException(
                f"Didn't receive all data for group ({group_data_count})"
            )

        self.dispatcher.unmap(f"/eos/out/get/group/{group:g}*", filter)
        return GroupProperties.from_list(group, group_props, group_chans)

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

    def record_blank_cue(self, cue: Cue) -> None:
        self.blind()
        try:
            self.get_cue(cue)
        except EosException:
            self.send_command(f"Cue {cue.cue_format()} # #")
        # Otherwise, cue already exists!

    def intensity_block_cue(self, cue: Cue) -> None:
        props = self.get_cue(cue)
        if "I" in props.blockstr:
            return
        self.send_command(f"Cue {cue.cue_format()} Intensity Block #")

    def block_cue(self, cue: Cue) -> None:
        props = self.get_cue(cue)
        if "B" in props.blockstr:
            return
        self.send_command(f"Cue {cue.cue_format()} Block #")

    def assert_cue(self, cue: Cue) -> None:
        props = self.get_cue(cue)
        if "A" in props.assertstr:
            return
        self.send_command(f"Cue {cue.cue_format()} Assert #")

    def set_time(self, cue: Cue, cuetime: float) -> None:
        if cue.part != 0:
            self.send_command(
                f"Cue {cue.cue_format()} Part {cue.part} Time {cuetime} #"
            )
        else:
            self.send_command(f"Cue {cue.cue_format()} Time {cuetime} #")

    def add_scene(self, cue: Cue, scene: str) -> None:
        props = self.get_cue(cue)
        if props.scene != "" and props.scene != scene:
            logging.warning(f"Renaming scene on {cue.cue_format()} ({props.scene})")
        self.send_command(f"Cue {cue.cue_format()} Scene {scene} #")

    def record_group(self, group: GroupProperties, overwrite: bool = False) -> None:
        self.open_tab(EosTab.GROUPS)
        try:
            grp = self.get_group(group.number)
        except EosException:
            logging.info(f"Creating new group {group.number}")
            self.send_command(f"Group {group.number} #")
            self.send_command(f"Group {group.number} Label {group.label} #")
            self.send_command(group.chanCommand())
        else:
            if overwrite:
                if grp.label != group.label:
                    logging.info(
                        f"Updating group {group.number} label to {group.label}"
                    )
                    self.send_command(f"Group {group.number} Label {group.label} #")
                if grp.channels != group.channels:
                    logging.info(
                        f"Updating group {group.number} channels to {group.channels} (was {grp.channels})"
                    )
                    self.send_command(f"Group {group.number} #")
                    self.send_command(group.chanCommand() + "#")
            else:
                raise EosException("Existing group differs from desired group!")

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

    def blind(self) -> None:
        self.press_key("Blind")

    def live(self) -> None:
        self.press_key("Live")

    def open_tab(self, tab: EosTab) -> None:
        self.write("/eos/key/Tab", [1.0])
        time.sleep(0.1)
        for i in str(int(tab)):
            self.write(f"/eos/key/{i}")
        self.write("/eos/key/Tab", [0.0])


class EosUDP(Eos):
    def __init__(self, ip: str, rx_port: int, tx_port: int):
        self.ip_address = ip
        self.rx_port = rx_port
        self.tx_port = tx_port
        self.dispatcher = Dispatcher()

        # self.server = BlockingOSCUDPServer((self.ip, self.tx_port), self.dispatcher)
        self.client = client = SimpleUDPClient(self.ip, self.rx_port)

        logger.info(
            f"Connected to {self.ip_address} (TX:{self.tx_port}, RX:{self.rx_port})"
        )
        # Confusion, client only takes one port?

        super().__init__()

    def write(self, path: str, args: Optional[List[str]] = None) -> None:
        self.client.send_message(path)


class EosTCP(Eos):
    client = None

    def __init__(self, ip: str, port: int):
        self.ip_address = ip
        self.port = port
        self.dispatcher = Dispatcher()

        if self.client is None:
            # TODO
            raise NotImplementedError("Mode detection TBD")

        super().__init__()

    def write(self, path: str, args: Optional[List[str]] = None) -> None:
        if args is None:
            self.client.send_message(path)
        else:
            self.client.send_message(path, args)

    def read_next(self, timeout: int = 30):
        msg = self.client.receive(timeout)
        return OscPacket(msg)

    def handle_messages(self, timeout: float = 0.1):
        msg = self.client.receive(timeout)
        while msg:
            for i in msg:
                self.dispatcher.call_handlers_for_packet(
                    i, (self.ip_address, self.port)
                )
            msg = self.client.receive(timeout)


class EosPacketLength(EosTCP):
    def __init__(self, ip: str, port: int):
        self.client = SimpleTCPClient(ip, port)
        logger.info(
            f"Connected to {self.ip_address}:{self.port} (TCP v1.0 Packet Length)"
        )

        super().__init__(ip, port)


class EosSLIP(EosTCP):
    def __init__(self, ip: str, port: int):
        self.client = SimpleTCPClient(ip, port, mode=MODE_1_1)
        logger.info(f"Connected to {ip}:{port} (TCP v1.1 SLIP)")

        super().__init__(ip, port)
