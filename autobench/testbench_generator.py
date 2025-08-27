"""Testbench generation logic."""

from dataclasses import dataclass
from typing import List, Optional, Dict

from .vhdl_parser import VhdlEntity, VhdlPort, VhdlGeneric
from .config import TestbenchConfig


@dataclass
class TestbenchData:
    """Data structure for testbench template substitution."""
    component_name: str
    ports: str
    internal_signals: str
    port_connections: str
    clk_gen: str
    stim_proc: str
    generics: str = ""
    generic_map: str = ""

    def apply_to_template(self, template: str) -> str:
        """Apply this data to a template string."""
        return template.format(
            component_name=self.component_name,
            ports=self.ports,
            internal_signals=self.internal_signals,
            port_connections=self.port_connections,
            clk_gen=self.clk_gen,
            stim_proc=self.stim_proc,
            generics=self.generics,
            generic_map=self.generic_map
        )


class TestbenchGenerator:
    """Generator for VHDL testbenches."""

    @staticmethod
    def generate_testbench_data(entity: VhdlEntity, config: Optional[TestbenchConfig] = None) -> TestbenchData:
        """Generate testbench data from entity and config."""
        component_name = entity.name
        ports = TestbenchGenerator._generate_ports_string(entity.ports, entity.generics, config)
        internal_signals = TestbenchGenerator._generate_internal_signals(entity.ports, entity.generics, config)
        port_connections = TestbenchGenerator._generate_port_connections(entity.ports)
        clk_gen = TestbenchGenerator._generate_clock_generation(config)
        stim_proc = TestbenchGenerator._generate_stimulus_process(entity.ports, config)

        generics = TestbenchGenerator._generate_generics_string(entity.generics, config)
        generic_map = TestbenchGenerator._generate_generic_map(entity.generics, config)
        
        return TestbenchData(
            component_name=component_name,
            ports=ports,
            internal_signals=internal_signals,
            port_connections=port_connections,
            clk_gen=clk_gen,
            stim_proc=stim_proc,
            generics=generics,
            generic_map=generic_map
        )

    @staticmethod
    def _generate_ports_string(ports: List[VhdlPort], generics: List[VhdlGeneric], config: Optional[TestbenchConfig]) -> str:
        """Generate ports string for component declaration."""
        result = []
        
        for i, port in enumerate(ports):
            port_line = f"        {port.name} : {port.direction.upper()} {port.signal_type.upper()}"
            
            if port.range:
                # Resolve generic parameters in ranges
                resolved_range = TestbenchGenerator._resolve_generic_range(port.range, generics, config)
                port_line += resolved_range
            
            if i < len(ports) - 1:
                port_line += ";"
            
            result.append(port_line)
        
        return "\n".join(result)

    @staticmethod
    def _resolve_generic_range(range_val: str, generics: List[VhdlGeneric], config: Optional[TestbenchConfig]) -> str:
        """Resolve generic parameters in port ranges."""
        resolved = range_val
        default_value = "32"
        
        # Replace generic parameters with their values
        for generic in generics:
            generic_name = generic.name.upper()
            
            # Check if config overrides this generic
            if config and config.generics:
                # First try to get from config
                value = config.generics.get(generic.name) or config.generics.get(generic_name)
                if value:
                    pass  # Use config value
                elif generic.default_value:
                    value = generic.default_value
                else:
                    value = default_value
            else:
                value = generic.default_value or default_value
            
            # Replace both uppercase and original case
            resolved = resolved.replace(generic_name, value)
            resolved = resolved.replace(generic.name, value)
        
        return resolved

    @staticmethod
    def _generate_generics_string(generics: List[VhdlGeneric], config: Optional[TestbenchConfig]) -> str:
        """Generate generics string for component declaration."""
        if not generics:
            return ""
        
        result = []
        
        for i, generic in enumerate(generics):
            # Get the value for this generic
            value = None
            
            # First check if config overrides this generic
            if config and config.generics:
                value = (config.generics.get(generic.name) or 
                        config.generics.get(generic.name.upper()) or
                        config.generics.get(generic.name.lower()))
            
            # If no config override, use default value from entity
            if value is None:
                value = generic.default_value
            
            # If still no value, use a sensible default
            if value is None:
                if generic.generic_type.upper() == "INTEGER":
                    value = "32"
                else:
                    value = "8"
            
            # Format the generic declaration
            generic_line = f"        {generic.name} : {generic.generic_type.upper()}"
            if value:
                generic_line += f" := {value}"
            
            # Add semicolon for all but the last generic
            if i < len(generics) - 1:
                generic_line += ";"
            
            result.append(generic_line)
        
        # Wrap in Generic clause if we have generics
        if result:
            return f"\n    Generic (\n" + "\n".join(result) + "\n    );"
        else:
            return ""

    @staticmethod
    def _generate_generic_map(generics: List[VhdlGeneric], config: Optional[TestbenchConfig]) -> str:
        """Generate generic map for component instantiation."""
        if not generics:
            return ""
        
        result = []
        
        for i, generic in enumerate(generics):
            # Get the value for this generic (same logic as component declaration)
            value = None
            
            # First check if config overrides this generic
            if config and config.generics:
                value = (config.generics.get(generic.name) or 
                        config.generics.get(generic.name.upper()) or
                        config.generics.get(generic.name.lower()))
            
            # If no config override, use default value from entity
            if value is None:
                value = generic.default_value
            
            # If still no value, use a sensible default
            if value is None:
                if generic.generic_type.upper() == "INTEGER":
                    value = "32"
                else:
                    value = "8"
            
            # Format the generic mapping
            map_line = f"		{generic.name} => {value}"
            
            # Add comma for all but the last generic
            if i < len(generics) - 1:
                map_line += ","
            
            result.append(map_line)
        
        # Wrap in generic map clause if we have generics
        if result:
            return f"\n\tgeneric map(\n" + "\n".join(result) + "\n\t)"
        else:
            return ""

    @staticmethod
    def _generate_internal_signals(ports: List[VhdlPort], generics: List[VhdlGeneric], config: Optional[TestbenchConfig]) -> str:
        """Generate internal signals for testbench."""
        signals = []
        
        for port in ports:
            signal_name = f"tb_{port.name}"
            signal_decl = f"signal {signal_name} : {port.signal_type.upper()}"
            
            if port.range:
                # Resolve generic parameters in ranges
                resolved_range = TestbenchGenerator._resolve_generic_range(port.range, generics, config)
                signal_decl += resolved_range
            
            # Add default values for testbench signals
            signal_type = port.signal_type.upper()
            if signal_type == "STD_LOGIC":
                signal_decl += " := '0'"  # Single bit: use single quotes
            elif signal_type == "STD_LOGIC_VECTOR":
                signal_decl += " := (others => '0')"  # Vector initialization
            elif signal_type == "INTEGER":
                signal_decl += " := 0"  # Integer literals don't need quotes
            else:
                signal_decl += " := '0'"  # Default to single bit
            
            signal_decl += ";"
            signals.append(signal_decl)
        
        # Add clock signal if not present
        has_clk = any(p.name.lower() in ["clk", "clock"] for p in ports)
        if not has_clk:
            signals.append("signal tb_clk : STD_LOGIC := '0';")
        
        return "\n".join(signals)

    @staticmethod
    def _generate_port_connections(ports: List[VhdlPort]) -> str:
        """Generate port map connections."""
        connections = []
        
        for i, port in enumerate(ports):
            connection = f"        {port.name} => tb_{port.name}"
            if i < len(ports) - 1:
                connection += ","
            connections.append(connection)
        
        return "\n".join(connections)

    @staticmethod
    def _generate_clock_generation(config: Optional[TestbenchConfig]) -> str:
        """Generate clock generation process."""
        period = 10  # Default 10ns period (100MHz)
        if config and config.clock_period_ns:
            period = config.clock_period_ns
        
        half_period = period // 2
        
        return f"    tb_clk <= '0';\n    wait for {half_period} ns;\n    tb_clk <= '1';\n    wait for {half_period} ns;"

    @staticmethod
    def _generate_stimulus_process(ports: List[VhdlPort], config: Optional[TestbenchConfig]) -> str:
        """Generate stimulus process."""
        stimulus = []
        
        # Reset sequence
        reset_duration = 100
        if config and config.reset_duration_ns is not None:
            reset_duration = config.reset_duration_ns
        
        if reset_duration > 0:
            stimulus.append(f"    -- Reset sequence")
            stimulus.append(f"    tb_rst <= '1';")
            stimulus.append(f"    wait for {reset_duration} ns;")
            stimulus.append(f"    tb_rst <= '0';")
            stimulus.append(f"    wait for 20 ns;")
            stimulus.append("")
        
        # Generate test vectors if provided in config
        if config and config.test_vectors:
            stimulus.append("    -- Test vectors")
            
            # Sort test vectors by time to ensure chronological order
            sorted_vectors = sorted(config.test_vectors, key=lambda v: v.time_ns)
            
            current_time = reset_duration + (20 if reset_duration > 0 else 0)  # Account for reset sequence
            
            for i, vector in enumerate(sorted_vectors):
                if vector.description:
                    stimulus.append(f"    -- Test {i + 1}: {vector.description} @{vector.time_ns}ns")
                else:
                    stimulus.append(f"    -- Test vector {i + 1} @{vector.time_ns}ns")
                
                # Calculate wait time (difference from current time to target time)
                wait_time = vector.time_ns - current_time
                if wait_time > 0:
                    stimulus.append(f"    wait for {wait_time} ns;")
                elif wait_time < 0:
                    # Negative wait time - test vector is in the past, skip waiting
                    stimulus.append(f"    -- Warning: Test vector time {vector.time_ns}ns is before current time {current_time}ns")
                
                # Apply inputs
                for signal, value in vector.inputs.items():
                    # Convert to proper VHDL syntax based on signal type
                    corrected_value = TestbenchGenerator._convert_to_vhdl_literal(value, signal, ports)
                    stimulus.append(f"    tb_{signal} <= {corrected_value};")
                
                # Add small settling time after signal changes
                stimulus.append("    wait for 1 ns;")
                current_time = vector.time_ns + 1
                
                # Add assertions if expected outputs are provided
                if vector.expected_outputs:
                    for signal, expected in vector.expected_outputs.items():
                        # Convert to proper VHDL syntax based on signal type
                        corrected_expected = TestbenchGenerator._convert_to_vhdl_literal(expected, signal, ports)
                        
                        # Generate detailed assertion with actual vs expected values
                        signal_port = next((p for p in ports if p.name == signal), None)
                        error_msg = TestbenchGenerator._generate_assertion_message(
                            i + 1, signal, corrected_expected, signal_port
                        )
                        
                        stimulus.append(f"    assert tb_{signal} = {corrected_expected}")
                        stimulus.append(f"        report {error_msg}")
                        stimulus.append(f"        severity error;")
                
                stimulus.append("")
        else:
            # Generate basic test stimulus
            stimulus.extend(TestbenchGenerator._generate_basic_test(ports))
        
        return "\n".join(stimulus)

    @staticmethod
    def _generate_basic_test(ports: List[VhdlPort]) -> List[str]:
        """Generate basic test stimulus when no config is provided."""
        test = ["    -- Basic stimulus"]
        
        for port in ports:
            if port.direction == "in" and port.name not in ["clk", "rst", "clock", "reset"]:
                signal_type = port.signal_type.upper()
                if signal_type == "STD_LOGIC":
                    test.extend([
                        f"    tb_{port.name} <= '1';",  # Single bit: single quotes
                        "    wait for 20 ns;",
                        f"    tb_{port.name} <= '0';",  # Single bit: single quotes
                        "    wait for 20 ns;"
                    ])
                elif signal_type == "STD_LOGIC_VECTOR":
                    test.extend([
                        f"    tb_{port.name} <= (others => '1');",  # Vector initialization
                        "    wait for 20 ns;",
                        f"    tb_{port.name} <= (others => '0');",  # Vector initialization
                        "    wait for 20 ns;"
                    ])
        
        test.append("")
        return test

    @staticmethod
    def _convert_to_vhdl_literal(value: str, signal_name: str, ports: List[VhdlPort]) -> str:
        """Convert config value to proper VHDL literal syntax based on signal type."""
        
        # Remove any existing quotes first to get the raw value
        raw_value = value.strip().strip("'\"")
        
        # If already properly quoted, return as-is
        if TestbenchGenerator._is_properly_quoted_vhdl(value):
            return value
        
        # Find the signal's port definition to determine type
        signal_port = None
        for port in ports:
            if port.name == signal_name:
                signal_port = port
                break
        
        if not signal_port:
            # Signal not found, make educated guess based on value
            if TestbenchGenerator._looks_like_bit_vector(raw_value):
                # Validate and convert bit vector
                clean_value = TestbenchGenerator._ensure_binary_only(raw_value)
                return f'"{clean_value}"'  # Bit vector
            else:
                return f"'{raw_value}'"  # Single bit
        
        # Convert based on actual signal type
        signal_type = signal_port.signal_type.upper()
        
        if signal_type == "STD_LOGIC":
            # Single bit: ensure it's a valid binary digit
            clean_value = TestbenchGenerator._ensure_binary_only(raw_value)
            # For single bit, take only the first character (or use '0' if empty)
            single_bit = clean_value[0] if clean_value and clean_value[0] in '01' else '0'
            return f"'{single_bit}'"
        elif signal_type == "STD_LOGIC_VECTOR":
            # Bit vector: validate and use double quotes
            clean_value = TestbenchGenerator._ensure_binary_only(raw_value)
            # Adjust length to match signal width if possible
            sized_value = TestbenchGenerator._size_to_signal(clean_value, signal_port)
            return f'"{sized_value}"'
        elif signal_type == "INTEGER":
            # Integer: no quotes
            return raw_value
        else:
            # Unknown type: default to single bit
            return f"'{raw_value}'"

    @staticmethod
    def _ensure_binary_only(value: str) -> str:
        """Ensure value contains only binary digits (0,1), convert hex if needed."""
        clean_value = value.upper().strip()
        
        # Check if this looks like a hex string (contains A-F)
        if any(c in clean_value for c in 'ABCDEF'):
            # Check if it's a valid hex string (all chars are hex digits)
            if all(c in '0123456789ABCDEF' for c in clean_value):
                try:
                    # Convert entire hex string to binary
                    hex_val = int(clean_value, 16)
                    binary_str = bin(hex_val)[2:]  # Remove '0b' prefix
                    
                    # Ensure we have proper bit width (multiple of 4 for hex conversion)
                    target_bits = len(clean_value) * 4
                    binary_str = binary_str.zfill(target_bits)
                    
                    return binary_str
                except ValueError:
                    # If hex conversion fails, fall back to character replacement
                    pass
            
            # Fallback: replace individual hex characters
            hex_replacements = {
                'A': '1010', 'B': '1011', 'C': '1100', 'D': '1101',
                'E': '1110', 'F': '1111'
            }
            
            result = clean_value
            for hex_char, binary_equiv in hex_replacements.items():
                result = result.replace(hex_char, binary_equiv)
            
            return result
        
        # If it's already binary or numeric, return as-is
        return clean_value

    @staticmethod
    def _generate_assertion_message(test_num: int, signal_name: str, expected_value: str, signal_port: Optional[VhdlPort]) -> str:
        """Generate detailed assertion failure message with actual vs expected values."""
        
        if not signal_port:
            # Unknown signal type, use basic message
            return f'"Test {test_num}: {signal_name} mismatch - expected {expected_value}"'
        
        signal_type = signal_port.signal_type.upper()
        
        if signal_type == "STD_LOGIC":
            # For STD_LOGIC, show the actual value
            return (f'"Test {test_num}: {signal_name} mismatch - expected {expected_value}, got " & '
                   f"std_logic'image(tb_{signal_name})")
        
        elif signal_type == "STD_LOGIC_VECTOR":
            # For STD_LOGIC_VECTOR, provide clear expected value and note to check waveform
            return f'"Test {test_num}: {signal_name} mismatch - expected {expected_value} (check waveform for actual value)"'
        
        elif signal_type == "INTEGER":
            # For INTEGER, convert to string
            return (f'"Test {test_num}: {signal_name} mismatch - expected {expected_value}, got " & '
                   f"integer'image(tb_{signal_name})")
        
        else:
            # Unknown type, use basic message with expected value
            return f'"Test {test_num}: {signal_name} mismatch - expected {expected_value}"'

    @staticmethod
    def _size_to_signal(binary_value: str, port: VhdlPort) -> str:
        """Size the binary value to match the signal width."""
        if not port.range:
            # No range specified, return as-is
            return binary_value
        
        # Try to extract bit width from range like "(7 downto 0)" or "(15 downto 0)"
        import re
        range_match = re.search(r'\((\d+)\s+downto\s+(\d+)\)', port.range)
        if range_match:
            high_bit = int(range_match.group(1))
            low_bit = int(range_match.group(2))
            target_width = high_bit - low_bit + 1
            
            if len(binary_value) > target_width:
                # Truncate to fit (take least significant bits)
                return binary_value[-target_width:]
            elif len(binary_value) < target_width:
                # Pad with leading zeros
                return binary_value.zfill(target_width)
        
        # If we can't parse the range, return as-is
        return binary_value

    @staticmethod
    def _is_properly_quoted_vhdl(value: str) -> bool:
        """Check if value is already properly quoted for VHDL."""
        value = value.strip()
        
        # Check for single-quoted single character (single bit)
        if value.startswith("'") and value.endswith("'") and len(value) == 3:
            return True
        
        # Check for double-quoted string (bit vector)  
        if value.startswith('"') and value.endswith('"') and len(value) >= 3:
            return True
        
        # Only treat clearly unambiguous integers as properly formatted
        # Be conservative: only negative numbers and numbers with non-binary digits
        if value.startswith('-') and value[1:].isdigit():
            return True  # Negative numbers are clearly integers
        if value.isdigit() and any(c not in '01' for c in value):
            return True  # Numbers with digits other than 0,1 are clearly integers (e.g., "42", "123")
        
        return False

    @staticmethod
    def _looks_like_bit_vector(value: str) -> bool:
        """Check if value looks like a bit vector (multiple 0s and 1s)."""
        # Remove any whitespace
        clean_value = value.replace(' ', '')
        
        # If it's more than one character and all 0s/1s, it's probably a bit vector
        if len(clean_value) > 1 and all(c in '01' for c in clean_value):
            return True
        
        return False
