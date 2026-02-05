from logging import Logger
from .mex_config import MicrocontrollerExportConfiguration
from .loader import ConfigToolsDataLoader
from .builders import generate_board_dtsi
import traceback
from pathlib import Path
import yaml
from typing import List


class DeviceTreeSourceBuilder:

    def __init__(self, logger: Logger, **kwargs):
        """
        Initializes the DTS Builder with specific NXP configuration parameters.
        """
        self.log = logger

        # Extract parameters from kwargs with defaults
        self.controller_type: str = kwargs.get("controller_type")
        self.output_path: str = kwargs.get("output_dts_path")
        self.mex_config: MicrocontrollerExportConfiguration = None
        self.query_type: str = kwargs.get("query_type")
        self.query_args: List[str] = kwargs.get("query_args")

        self.loader = ConfigToolsDataLoader(logger=logger,
                                            user_board_config_file=kwargs.get("user_board_config_file_path"),
                                            data_file=kwargs.get("config_tools_data_file_path"),
                                            mex_file=kwargs.get("mex_file_path"),
                                            mode=kwargs.get("action"))

        if not self.loader.load_all():
            raise RuntimeError("ConfigToolsDataLoader failed to synchronize data sources.")

        self.mex_config = self.loader.mex_config

        if not self.controller_type:
            self.controller_type = self.mex_config.get_controller_type()

        if not self.output_path:
            self.output_path = f"{self.mex_config.get_board_name().lower().replace('-', '_')}-pinctrl.dtsi"

        self.log.debug("DeviceTreeSourceBuilder initialized",
                       extra={
                           "controller": self.controller_type,
                           "data_source": self.loader.data_file,
                           "mex_source": self.loader.mex_file,
                           "output_path": self.output_path,
                           "is_mex_file_archived": self.loader.is_mex_file_archived
                       })

    def build(self) -> bool:
        """Executes the DTS generation process."""
        log: Logger = self.log
        log.info(f"Starting DTS build process for {self.controller_type}")

        try:
            signal_data = self.loader.load_signal_config()
            if not signal_data:
                self.log.error("Could not obtain signal configuration data. Aborting.")
                return False

            # uart_pins = signal_data.get_pins_by_peripheral("UART0")
            # log.debug(f"Found {len(uart_pins)} pins for UART0")

            dts_content = generate_board_dtsi(self.loader.user_board_config, signal_data.signal_to_pin_map, log)

            with open(self.output_path, "w") as f:
                f.write(dts_content)
                log.info("Wrote DTS to %s", self.output_path)

            with open(Path.joinpath(Path(self.output_path).parent, "signal_to_pin_map.yaml"), 'w') as file:
                yaml.dump({"signal_to_pin_map": signal_data.signal_to_pin_map}, file, default_flow_style=False, sort_keys=False)

            with open(Path.joinpath(Path(self.output_path).parent, "board_mapping_config.yaml"), 'w') as file:
                yaml.dump(self.loader.user_board_config, file, default_flow_style=False, sort_keys=False)

            with open(Path.joinpath(Path(self.output_path).parent, "peripherals.yaml"), 'w') as file:
                yaml.dump({"peripherals": signal_data.peripherals}, file, default_flow_style=False, sort_keys=False)

            with open(Path.joinpath(Path(self.output_path).parent, "peripheral_types.yaml"), 'w') as file:
                yaml.dump({"peripheral_types": signal_data.peripheral_types}, file, default_flow_style=False, sort_keys=False)

            with open(Path.joinpath(Path(self.output_path).parent, "functional_properties.yaml"), 'w') as file:
                yaml.dump({"functional_properties": signal_data.functional_properties}, file, default_flow_style=False, sort_keys=False)



            log.info("DTS build successful")
            return True

        except Exception as e:
            traceback.print_exc()
            log.error(f"Build failed: {str(e)}", exc_info=True)
            return False




    def query(self) -> bool:
        """Executes the DTS query."""
        log: Logger = self.log
        log.info(f"Starting DTS query for {self.controller_type}")

        if self.query_type == "find_base_pin":
            if len(self.query_args) != 1:
                log.error("The base_pin query argument not found", extra={"query_type": self.query_type, "query_args": self.query_args})
                return False
        else:
            log.error("Unsupported query", extra={"query_type": self.query_type})
            return False

        try:
            signal_data = self.loader.load_signal_config()
            if not signal_data:
                self.log.error("Could not obtain signal configuration data. Aborting.")
                return False

            if self.query_type == "find_base_pin":
                pass

            log.debug("DTS query successful")
            return True
        except Exception as e:
            traceback.print_exc()
            log.error(f"Query failed: {str(e)}", exc_info=True)
            return False
