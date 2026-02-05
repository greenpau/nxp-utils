from typing import Dict, Any, List
from logging import Logger
from .pin_entry import PinEntry

def find_pin_entry(signal_to_pin_map, peri_id, sig_id, chosen_pin):
    """
    Search helper. Tries specific lookup, then searches the whole peripheral.
    """
    # Try exact signal name (e.g., UART0 -> RX)
    options = signal_to_pin_map.get(peri_id, {}).get(sig_id, [])
    match = next((opt for opt in options if opt['base_pin'] == chosen_pin), None)
    if match:
        return match

    # Fallback: Search all signals in that peripheral (e.g., GPIOB -> GPIO)
    all_signals = signal_to_pin_map.get(peri_id, {})
    for _, options_list in all_signals.items():
        match = next((opt for opt in options_list if opt['base_pin'] == chosen_pin), None)
        if match:
            return match
    return None


def parse_peripheral_groups(board_config: dict, signal_to_pin_map: Dict[str, Any], log=Logger) -> Dict[str, List[PinEntry]]:
    """
    Bridges board.json with the parsed XML map to generate final DTS.
    """
    # We group by peripheral to create clean DTS nodes (e.g., all UART0 pins in one node)
    # Grouping logic: { "UART0": [pin_entry1, pin_entry2], "GPIO": [...] }
    peripheral_groups: Dict[str, List[PinEntry]] = {}

    mapping_list: List[Dict] = board_config.get('mapping', [])

    for entry in mapping_list:
        signal_key = entry.get('signal')    # e.g., "UART0_RX"
        chosen_pin = entry.get('pin')    # e.g., "PTB16"

        if not signal_key or not chosen_pin:
            continue

        # signal_key is "UART0_RX", chosen_pin is "PTB16"
        # Split key to get Peripheral and Signal name
        # We split from the right once to handle cases like "ENET0_1588_TMR0"
        # This results in peri_id="I2S0", sig_id="TX_BCLK" (Correct!)

        parts = signal_key.split('_')
        match = None
        peri_id = ""
        sig_id = ""

        # Try every possible split point
        # e.g., (ENET0, 1588_TMR0), then (ENET0_1588, TMR0)
        for i in range(1, len(parts)):
            temp_peri = "_".join(parts[:i])
            temp_sig = "_".join(parts[i:])    
            match = find_pin_entry(signal_to_pin_map, temp_peri, temp_sig, chosen_pin)
            if match:
                peri_id, sig_id = temp_peri, temp_sig
                break

        if match:
            pin_obj = PinEntry(
                base_pin=chosen_pin,
                mux_value=match['mux_value'],
                func_label=signal_key,
                user_label=entry.get('label'),
                pull=entry.get('pull'),
                drive_strength=entry.get('drive_strength'),
                slew_rate=entry.get('slew_rate'),
                open_drain=entry.get('open_drain'),
                passive_filter=entry.get('passive_filter'),
                digital_filter=entry.get('digital_filter'),
                gpio_init_state=entry.get('gpio_init_state'),
                gpio_interrupt=entry.get('gpio_interrupt')
            )
            if peri_id not in peripheral_groups:
                peripheral_groups[peri_id] = []
            peripheral_groups[peri_id].append(pin_obj)
        else:
            print(f"WARNING: No hardware match for {signal_key} on {chosen_pin}")

    return peripheral_groups
