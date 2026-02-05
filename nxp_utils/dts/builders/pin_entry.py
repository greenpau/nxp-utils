from typing import Optional, Any, TypedDict
from dataclasses import dataclass


@dataclass(frozen=True)
class PinEntry:
    base_pin: str    # e.g., "PTB16"
    mux_value: str    # e.g., "0x3"
    func_label: str    # e.g., "UART0_RX"
    user_label: Optional[str] = None    # e.g., "DEBUG_UART_RX"
    # Electrical (pinctrl)
    pull: Optional[str] = None    # "up", "down", or None
    drive_strength: Optional[str] = None    # "low", "high"
    slew_rate: Optional[str] = None    # "fast", "slow"
    open_drain: Any = None    # bool or "enable"/"disable"
    passive_filter: Any = None    # bool or "enable"/"disable"
    digital_filter: Any = None
    # Logic (GPIO controller)
    gpio_init_state: Optional[bool] = None
    gpio_interrupt: Optional[str] = None

    def __repr__(self) -> str:
        return f"PinEntry({self.base_pin} -> {self.user_label or self.func_label})"

    def get_config_sig(self) -> tuple:
        """Only include hardware/electrical properties in the pinctrl signature."""
        return (self.pull, self.drive_strength, self.slew_rate, self.open_drain, self.passive_filter, self.digital_filter)
