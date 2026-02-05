import re

# The K64F Port Base Addresses
PORT_BASES = {
    'A': 0x40049000,
    'B': 0x4004A000,
    'C': 0x4004B000,
    'D': 0x4004C000,
    'E': 0x4004D000
}

def calculate_pcr_address(base_pin: str) -> int:
    """
    Converts 'PTE1' to 0x4004D004
    """
    # Regex to pull 'E' and '1' from 'PTE1'
    match = re.match(r"PT([A-E])(\d+)", base_pin)
    if not match:
        return None
    
    port_letter = match.group(1)  # 'E'
    pin_index = int(match.group(2))  # 1
    
    base_addr = PORT_BASES.get(port_letter)
    # Each PCR register is 4 bytes (32-bit)
    pcr_address = base_addr + (pin_index * 4)
    
    return pcr_address