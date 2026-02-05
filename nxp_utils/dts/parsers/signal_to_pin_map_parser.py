from ..utils import print_xml
from logging import Logger
import xml.etree.ElementTree as ET
from typing import Dict, Any, List
from pprint import pprint


def parse_signal_to_pin_map(root=ET.Element,
                            peripheral_types: Dict[str, Any] = {},
                            peripherals: Dict[str, Any] = {},
                            log=Logger) -> Dict[str, Any]:

    """
    Parses the <pins> section to create a mapping of:
    Peripheral -> Signal -> Pin Options (Mux, Coords, Properties)
    """
    log.debug("Parsing hardware pin-to-signal mapping table")
    mapping = {}

    # Locate the container node
    node_key = "pins"
    pins_node = root.find(node_key)
    if pins_node is None:
        log.warning("No %s found in XML for building hardware pin-to-signal mapping table", node_key)
        return mapping

    for pin in pins_node.findall("pin"):
        # print_xml(pin)
        entry = {}
        # The 'name' attribute looks like: "ADC1_SE4a/PTE0/SPI1_PCS1/UART1_TX/..."
        labels = [l.strip() for l in pin.get("name", "").split("/") if l.strip()]
        descriptions = [d.strip() for d in pin.get("description", "").split(";") if d.strip()]

        coords = pin.get("coords")
        if not coords:
            raise Exception(f"The coords key is empty for {labels}")

        # Create a lookup for Label -> Description
        label_meta = dict(zip(labels, descriptions))
        for k in label_meta:
            if k != "" and label_meta[k] != "":
                continue
            raise Exception(f"Malformed name {pin.get("name", "")} or {pin.get("description", "")}")

        # Identify the Base GPIO name (e.g., PTA1). If None, it's non-routable.
        base_pin = next((l for l in labels if l.startswith("PT")), None)

        # A pin is "routable" only if it has a Port Control Register (starts with PT)
        is_routable = base_pin is not None

        for connections in pin.findall("connections"):
            name_part = connections.get("name_part")
            alt_mode = connections.get("package_function")
            
            for conn in connections.findall("connection"):
                sig_ref = conn.find("peripheral_signal_ref")
                if sig_ref is None:
                    continue

                peri_id = sig_ref.get("peripheral")
                sig_id = sig_ref.get("signal")

                # Extract Mux Value
                mux_value = None
                config = conn.find("configuration")
                if config is not None:
                    for assign in config.findall("assign"):
                        if assign.get("bit_field") == "MUX":
                            mux_value = assign.get("bit_field_value")

                # Initialize Mapping
                if peri_id not in mapping:
                    mapping[peri_id] = {}
                if sig_id not in mapping[peri_id]:
                    mapping[peri_id][sig_id] = []

                # Build entry with routing awareness
                entry = {
                    "base_pin": base_pin if is_routable else labels[0],
                    "is_routable": is_routable,
                    "mux_value": mux_value if is_routable else "FIXED",
                    "alt_mode": alt_mode if is_routable else "ANALOG",
                    "coords": coords,
                    "func_label": name_part,
                    "description": label_meta.get(name_part, ""),
                }
                mapping[peri_id][sig_id].append(entry)
    
    log.debug("Mapped signals for %d peripherals", len(mapping))
    # pprint(mapping)

    # Get only pins that actually need a MUX configuration for UART1
    # routable_uart_tx = [p for p in mapping["UART1"]["TX"] if p["is_routable"]]

    # pprint(routable_uart_tx)
    return mapping
