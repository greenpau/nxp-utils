import xml.etree.ElementTree as ET
import io
from logging import Logger
from pathlib import Path
from typing import Optional, Union

# Update PathType to include file path and bytes/BinaryIO for archived data
PathOrData = Union[str, Path, bytes, io.BytesIO]


class MicrocontrollerExportConfiguration:
    """
    Convenience methods used to get board and processor data from NXP configuration files.
    MEX refers to a Microcontrollers Export Configuration file (.mex), which is generated
    by the NXP Config Tools. This file stores comprehensive settings for pin multiplexing,
    peripherals, and clock configurations, which are used to generate corresponding device
    tree source.
    """

    def __init__(self, input_data: PathOrData, logger: Logger, source_name: str = "Unknown"):
        """
        Initialize the MEX parser.
        :param input_data: Path to .mex file OR raw bytes/stream from an archive.
        :param logger: Logger instance.
        :param source_name: Helpful name for logging (e.g., filename inside zip).
        """
        self.log = logger
        self.source_name = source_name
        self.namespaces = {'mex': 'http://mcuxpresso.nxp.com/XSD/mex_configuration_14'}

        # Determine if we have a path or raw data to check for legacy support
        check_str = str(input_data) if isinstance(input_data, (str, Path)) else source_name

        if 'K64F' in check_str:
            self.namespaces['mex'] = 'http://mcuxpresso.nxp.com/XSD/mex_configuration_1.8'
            self.log.debug("Using legacy 1.8 namespace for K64F support", extra={"source": self.source_name})

        self._tree: Optional[ET.ElementTree] = self._parse_input(input_data)

    def _parse_input(self, input_data: PathOrData) -> Optional[ET.ElementTree]:
        """Handles parsing regardless of whether input is a path or binary data."""
        try:
            if isinstance(input_data, (str, Path)):
                return ET.parse(str(input_data))

            # If it's bytes or a binary stream (like zipfile.open returns)
            if isinstance(input_data, bytes):
                return ET.ElementTree(ET.fromstring(input_data))

            # Handle file-like objects (io.BytesIO or ZipExtFile)
            content = input_data.read()
            return ET.ElementTree(ET.fromstring(content))

        except ET.ParseError:
            self.log.error("Malformed XML tree in input", extra={"source": self.source_name})
        except Exception as e:
            self.log.error(f"Failed to parse MEX data: {str(e)}", extra={"source": self.source_name})
        return None

    def get_pins_version(self) -> float:
        """Gets version of pins tool from the configuration file."""
        if self._tree is None:
            return 0.0

        pins_node = self._tree.getroot().find('mex:tools/mex:pins', self.namespaces)
        if pins_node is None:
            return 0.0

        version = pins_node.get('version')
        try:
            return float(version) if version else 0.0
        except ValueError:
            return 0.0

    def get_board_name(self) -> Optional[str]:
        """Extracts board name; falls back to processor name if board tag is missing."""
        if self._tree is None:
            return None

        board_node = self._tree.getroot().find('mex:common/mex:board', self.namespaces)
        if board_node is not None and board_node.text:
            return board_node.text

        proc_name = self.get_processor_name()
        return f"{proc_name}-board" if proc_name else "unknown-board"

    def get_processor_name(self) -> Optional[str]:
        """Extracts processor name from the configuration file."""
        if self._tree is None:
            return None

        node = self._tree.getroot().find('mex:common/mex:processor', self.namespaces)
        if node is None or not node.text:
            self.log.error("Cannot locate processor name in configuration", extra={"path": self.input_file})
            return None
        return node.text

    def get_package_name(self) -> Optional[str]:
        """Extracts package name from the configuration file."""
        if self._tree is None:
            return None

        node = self._tree.getroot().find('mex:common/mex:package', self.namespaces)
        if node is None or not node.text:
            self.log.error("Cannot locate package name in configuration", extra={"path": self.input_file})
            return None
        return node.text

    def get_controller_type(self) -> Optional[str]:
        processor_name = self.get_processor_name()
        # Select family of pin controller based on SOC type
        if "IMXRT1" in processor_name:
            # Use IMX config tools
            return 'IOMUX'
        if "IMXRT6" in processor_name:
            # LPC config tools
            return 'IOCON'
        if "IMXRT5" in processor_name:
            # LPC config tools
            return 'IOCON'
        if "LPC55" in processor_name:
            # LPC config tools
            return 'IOCON'
        if "MK" in processor_name:
            # Kinetis config tools
            return 'PORT'
        if "MCX" in processor_name:
            # Kinetis config tools
            return 'PORT'
        # Unknown processor family
        raise Exception(f"Unsupported processor name: {processor_name}")