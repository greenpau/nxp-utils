import os
import re
import zipfile
import json
import yaml
from typing import Optional, Dict, Any
from logging import Logger
import traceback
from .mex_config import MicrocontrollerExportConfiguration
from .signal_config import SignalConfiguration


class ConfigToolsDataLoader:
    """Handles the extraction and indexing of NXP Config Tools data archives."""

    def __init__(self, logger: Logger, user_board_config_file: str, data_file: str, mex_file: Optional[str] = None, mode: str = "build_dts"):
        self.log: Logger = logger
        self.data_file = data_file
        self.mex_file = mex_file
        self.user_board_config_file = user_board_config_file
        self.mode = mode

        self.archive: zipfile.ZipFile = None
        self.mex_config: MicrocontrollerExportConfiguration = None
        self.user_board_config: dict = None
        self.data_version: str = "unknown"
        self.processor_data_path: str = ""
        self.is_mex_file_archived: bool = not bool(mex_file)

    def load_all(self) -> bool:
        """Sequential execution of the loading pipeline."""
        if self.mode not in ["query_dts"]:
            if not self._load_user_board_config(): return False
        if not self._load_config_tools_data_archive(): return False
        if not self._load_mex_config(): return False
        if not self._load_processor_data_files(): return False
        return True

    def parse_user_board_config(self, file_path: str) -> Dict[str, Any]:
        """
        Parses a file path and returns a dictionary.
        Supports .json, .yaml, and .yml extensions.
        """
        _, ext = os.path.splitext(file_path.lower())
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                if ext == '.json':
                    data = json.load(file)
                elif ext in ['.yaml', '.yml']:
                    data = yaml.safe_load(file)
                else:
                    # Attempt to guess format if extension is non-standard
                    content = file.read()
                    try:
                        data = json.loads(content)
                    except json.JSONDecodeError:
                        data = yaml.safe_load(content)
                
                # Ensure the output is actually a dictionary
                if isinstance(data, dict):
                    return data
                else:
                    raise ValueError(f"File content is {type(data)}, expected dict.")

        except (FileNotFoundError, yaml.YAMLError, json.JSONDecodeError) as e:
            print(f"Parsing error: {e}")
            return {}
            
    def _load_user_board_config(self) -> bool:
        """
        Loads the user selection for board configuration. 
        """
        if not self.user_board_config_file:
            self.log.error("No input user-selected board configuration file found")
            return False

        if not os.path.exists(self.user_board_config_file):
            self.log.error("User-selected board configuration file does not exist: %s", self.user_board_config_file)
            return False

        try:
            self.user_board_config = self.parse_user_board_config(self.user_board_config_file).get("board_config", {})
            if self.user_board_config:
                self.log.info("User-selected board configuration loaded successfully", extra={"count": len(self.user_board_config)})

                # Debugging print to see what we got
                self.log.debug("Loaded mappings: %s", self.user_board_config)

                # Validate for electrical/logical overlaps
                if not self.validate_user_board_config():
                    self.log.error("Generation aborted due to pin conflicts.")
                    return False
                return True
            self.log.warning("Board configuration file was loaded but appeared empty.")
            return False
        except json.JSONDecodeError as e:
            self.log.error("Failed to parse JSON in %s: %s", self.user_board_config_file, e)
            return False
        except Exception as e:
            self.log.error("Failed to load user-selected board configuration data: %s", e, exc_info=True)
            return False

    def _load_config_tools_data_archive(self) -> bool:
        """
        Loads the config tools data zip file and lists its contents.
        Returns True if successful, False otherwise.
        """
        if not self.data_file:
            self.log.error("No config tools data file specified")
            return False

        if not os.path.exists(self.data_file):
            self.log.error("Data file does not exist", extra={"path": self.data_file})
            return False

        try:
            # Load the archive
            self._archive = zipfile.ZipFile(self.data_file, 'r')

            # List the files
            all_files = self._archive.namelist()

            # Filter for .mex files
            mex_files = [f for f in all_files if f.lower().endswith('.mex')]

            self.log.debug("Data file loaded and indexed",
                           extra={
                               "path": self.data_file,
                               "total_files": len(all_files),
                               "mex_files_found": mex_files
                           })

            if self.is_mex_file_archived:
                if len(mex_files) < 0:
                    raise Exception(f"no .mex file found in {self.data_file}")
                elif len(mex_files) > 1:
                    raise Exception(f"too many .mex files found in {self.data_file}")
                self.mex_file = mex_files[0]

            if 'npidata.mf' in all_files:
                with self._archive.open('npidata.mf', 'r') as stream:
                    content = stream.read().decode('utf-8')
                    match = re.search(r'data_version=([\d\.]+)', content)
                    if match:
                        self.config_tools_data_version = match.group(1)
                        self.log.debug("Discovered config tools data version", extra={"version": self.config_tools_data_version})
            else:
                self.log.warning("npidata.mf not found in archive root; version defaults to 0.0")
            return True
        except zipfile.BadZipFile:
            self.log.error("The provided data file is not a valid zip archive", extra={"path": self.data_file})
            return False
        except Exception as e:
            self.log.error(f"Failed to load data file: {str(e)}", exc_info=True)
            return False

    def _load_mex_config(self) -> bool:
        """
        Loads the MEX configuration. 
        If an archive is open, it searches the archive for the input_file.
        If no archive is used, it attempts to load input_file from the local path.
        """
        if not self.mex_file:
            self.log.error("No input MEX configuration file found")
            return False

        try:
            if self.is_mex_file_archived:
                with self._archive.open(self.mex_file) as stream:
                    self.mex_config = MicrocontrollerExportConfiguration(input_data=stream, logger=self.log, source_name=self.mex_file)
            else:
                if not os.path.exists(self.mex_file):
                    self.log.error("Local MEX file does not exist", extra={"path": self.mex_file})
                    return False
                self.mex_config = MicrocontrollerExportConfiguration(input_data=self.mex_file,
                                                                     logger=self.log,
                                                                     source_name=os.path.basename(self.mex_file))

            if self.mex_config and self.mex_config._tree is not None:
                self.log.info("MEX configuration loaded successfully",
                              extra={
                                  "board_name": self.mex_config.get_board_name(),
                                  "package_name": self.mex_config.get_package_name(),
                                  "processor_name": self.mex_config.get_processor_name(),
                                  "pins_version": self.mex_config.get_pins_version(),
                              })
                return True

            return False

        except Exception as e:
            self.log.error(f"Failed to load MEX data: {str(e)}", exc_info=True)
            return False

    def _load_processor_data_files(self) -> bool:
        """
        Locates the processor-specific data directory within the zip archive.
        Path structure: processors/<processor_name>/ksdk2_0/<package_name>
        """
        if not self.mex_config:
            self.log.error("MEX configuration was not loaded. Cannot determine processor path.")
            return False

        if not self._archive:
            self.log.error("Config tools data archive not loaded")
            return False

        processor_name = self.mex_config.get_processor_name()
        package_name = self.mex_config.get_package_name()

        if not processor_name or not package_name:
            self.log.error("Could not extract processor or package name from MEX data")
            return False

        # Using forward slashes as required by the ZIP standard
        self.processor_data_path = f"processors/{processor_name}/ksdk2_0/{package_name}"

        # 3. Verify the path exists in the archive
        # Zip archives don't always have explicit directory entries,
        # so we check if any file starts with this path.
        all_files = self._archive.namelist()
        path_exists = any(f.startswith(self.processor_data_path) for f in all_files)

        if not path_exists:
            self.log.error("Processor data path not found in archive",
                           extra={
                               "expected_path": self.processor_data_path,
                               "processor": processor_name,
                               "package": package_name
                           })
            return False

        self.log.info("Processor data path verified", extra={"processor_path": self.processor_data_path})
        return True

    def validate_user_board_config(self) -> bool:
        """
        Ensures no physical pin is assigned to multiple signals in board.json.
        """
        # Track usage: { "PTB16": "UART0_RX", ... }
        pin_usage = {}
        conflicts = []

        mapping_list = self.user_board_config.get('board_config', {}).get('mapping', [])
        for entry in mapping_list:
            # Extract from the new list structure
            signal_key = entry.get('signal') # e.g., "UART0_RX"
            chosen_pin = entry.get('pin')    # e.g., "PTB16"
            if chosen_pin in pin_usage:
                conflicts.append(
                    f"CONFLICT: Pin {chosen_pin} is assigned to both "
                    f"'{pin_usage[chosen_pin]}' and '{signal_key}'"
                )
            else:
                pin_usage[chosen_pin] = signal_key

        if conflicts:
            for error in conflicts:
                self.log.error(error)
            return False
        
        self.log.info("Board configuration validation passed: No pin conflicts detected.")
        return True
        
    def load_signal_config(self) -> Optional[SignalConfiguration]:
        """
        Reads signal_configuration.xml from the internal processor path.
        """
        log: Logger = self.log
        if not self._archive or not self.processor_data_path:
            log.error("Archive not ready or processor path unknown")
            return None

        # Construct path: processors/<proc>/ksdk2_0/<pkg>/signal_configuration.xml
        target_path = f"{self.processor_data_path}/signal_configuration.xml"

        try:
            if target_path not in self._archive.namelist():
                log.error("signal_configuration.xml missing from archive", extra={"path": target_path})
                return None

            with self._archive.open(target_path) as stream:
                # Read binary data and pass to the dedicated parser
                return SignalConfiguration(stream.read(), self.log)

        except Exception as e:
            traceback.print_exc()
            log.error(f"Error reading signal_configuration.xml: %s", e, exc_info=True)
            return None
