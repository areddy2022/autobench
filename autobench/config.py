"""Configuration handling for testbench generation."""

import tomllib
import tomli_w
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from pathlib import Path

from .vhdl_parser import VhdlEntity


@dataclass
class TestVector:
    """Represents a test vector for testbench."""
    time_ns: int
    inputs: Dict[str, str]
    expected_outputs: Optional[Dict[str, str]] = None
    description: Optional[str] = None


@dataclass
class TestbenchConfig:
    """Configuration for testbench generation."""
    clock_period_ns: Optional[int] = None
    reset_duration_ns: Optional[int] = None
    test_vectors: Optional[List[TestVector]] = None
    generics: Optional[Dict[str, str]] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for TOML serialization."""
        result = {}
        
        if self.clock_period_ns is not None:
            result['clock_period_ns'] = self.clock_period_ns
        if self.reset_duration_ns is not None:
            result['reset_duration_ns'] = self.reset_duration_ns
        if self.generics is not None:
            result['generics'] = self.generics
        
        if self.test_vectors:
            result['test_vectors'] = []
            for vector in self.test_vectors:
                vector_dict = {
                    'time_ns': vector.time_ns,
                    'inputs': vector.inputs
                }
                if vector.expected_outputs:
                    vector_dict['expected_outputs'] = vector.expected_outputs
                if vector.description:
                    vector_dict['description'] = vector.description
                result['test_vectors'].append(vector_dict)
        
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'TestbenchConfig':
        """Create from dictionary loaded from TOML."""
        test_vectors = None
        if 'test_vectors' in data:
            test_vectors = []
            for vector_data in data['test_vectors']:
                test_vectors.append(TestVector(
                    time_ns=vector_data['time_ns'],
                    inputs=vector_data.get('inputs', {}),  # Default to empty dict if no inputs
                    expected_outputs=vector_data.get('expected_outputs'),
                    description=vector_data.get('description')
                ))
        
        return cls(
            clock_period_ns=data.get('clock_period_ns'),
            reset_duration_ns=data.get('reset_duration_ns'),
            test_vectors=test_vectors,
            generics=data.get('generics')
        )


def load_config(path: Path) -> TestbenchConfig:
    """Load configuration from TOML file."""
    try:
        with open(path, 'rb') as f:
            data = tomllib.load(f)
        return TestbenchConfig.from_dict(data)
    except FileNotFoundError:
        raise FileNotFoundError(f"Failed to read config file '{path}': File not found")
    except Exception as e:
        raise RuntimeError(f"Failed to parse TOML config '{path}': {e}")


def save_config(config: TestbenchConfig, path: Path) -> None:
    """Save configuration to TOML file."""
    try:
        with open(path, 'wb') as f:
            tomli_w.dump(config.to_dict(), f)
    except Exception as e:
        raise RuntimeError(f"Failed to write config file '{path}': {e}")


def generate_baseline_config(entity: VhdlEntity) -> TestbenchConfig:
    """Generate a baseline configuration from VHDL entity."""
    # Create sample test vector
    sample_inputs = {}
    expected_outputs = {}
    
    # Add sample values for input ports
    for port in entity.ports:
        if port.direction == "in":
            sample_value = _get_default_value(port.signal_type, port.range)
            sample_inputs[port.name] = sample_value
        elif port.direction == "out":
            expected_value = _get_default_value(port.signal_type, port.range)
            expected_outputs[port.name] = expected_value
    
    sample_test_vector = TestVector(
        time_ns=100,
        inputs=sample_inputs,
        expected_outputs=expected_outputs if expected_outputs else None,
        description="Sample test case - modify as needed"
    )
    
    # Create generic mappings from entity generics
    generics_map = {}
    for generic in entity.generics:
        if generic.default_value:
            generics_map[generic.name] = generic.default_value
    
    return TestbenchConfig(
        clock_period_ns=10,  # 10ns = 100MHz
        reset_duration_ns=100,
        test_vectors=[sample_test_vector],
        generics=generics_map if generics_map else None
    )


def _get_default_value(signal_type: str, range_val: Optional[str]) -> str:
    """Get default value for a signal type (unquoted - quoting handled at VHDL generation)."""
    signal_type = signal_type.lower()
    
    if signal_type == "std_logic":
        return "0"  # Single bit value (quotes added during VHDL generation)
    elif signal_type == "std_logic_vector":
        if range_val:
            return "00000000"  # Bit vector value (quotes added during VHDL generation)
        else:
            return "0"  # Single bit vector
    elif signal_type == "integer":
        return "0"  # Integer value
    else:
        return "0"  # Default value
