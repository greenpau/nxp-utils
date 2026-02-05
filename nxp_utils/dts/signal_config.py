import xml.etree.ElementTree as ET
from logging import Logger
from typing import Optional, List, Dict, Any
from .utils import print_xml
from pprint import pprint
from .parsers import parse_functional_properties, parse_peripheral_types, parse_peripherals, parse_signal_to_pin_map


class SignalConfiguration:
    """
    Parses signal_configuration.xml to provide mappings between 
    peripherals, signals, and physical pins.
    """

    def __init__(self, data: bytes, logger: Logger):
        self.log = logger
        self._root: Optional[ET.Element] = None
        self.part_num: str = None
        self.peripherals: Dict[str, Dict[str, Any]] = {}
        self.peripheral_types: Dict[str, Dict[str, Any]] = {}
        self.functional_properties: Dict[str, Dict[str, Any]] = {}
        self.signal_to_pin_map: Dict[str, Dict[str, Any]] = {}

        try:
            # Parse from bytes directly from the zip stream
            self._root = ET.fromstring(data)
            self.log.debug("Signal configuration XML parsed successfully")
        except ET.ParseError as e:
            self.log.error(f"Failed to parse signal configuration XML: {e}")

        self._parse_xml()

    def _parse_xml(self):
        log: Logger = self.log
        self.part_num = self._root.find("./part_information/part_number").get('id')
        log.debug("Discovert part number: %s", self.part_num)
        self.peripheral_types = parse_peripheral_types(self._root, self.log)
        self.peripherals = parse_peripherals(self._root, self.peripheral_types, self.log)
        self.functional_properties = parse_functional_properties(self._root, self.log)
        self.signal_to_pin_map = parse_signal_to_pin_map(self._root, self.peripheral_types, self.peripherals, self.log)

    def get_peripheral_info(self, peripheral_id: str) -> Optional[Dict[str, Any]]:
        """Returns the full data tree for a given peripheral type (e.g., 'ADC')."""
        return self.peripherals.get(peripheral_id)

    def get_pins_by_peripheral(self, peripheral_name: str) -> List[Dict[str, str]]:
        """
        Retrieves all pin entries associated with a specific peripheral.
        """
        if self._root is None:
            return []

        results = []
        # NXP XMLs often use 'pins/pin' or 'connections/connection'
        # structure depending on the Config Tools version.
        for pin_node in self._root.findall(f".//pin[@peripheral='{peripheral_name}']"):
            results.append({"id": pin_node.get("id"), "signal": pin_node.get("signal"), "pin_num": pin_node.get("pin_num")})
        return results
