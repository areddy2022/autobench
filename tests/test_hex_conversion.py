"""Tests for hex to binary conversion in VHDL literals."""

import pytest
from autobench.vhdl_parser import VhdlEntity, VhdlPort
from autobench.config import TestbenchConfig, TestVector
from autobench.testbench_generator import TestbenchGenerator


def test_ensure_binary_only():
    """Test conversion of hex characters to binary."""
    
    # Test basic hex conversion
    assert TestbenchGenerator._ensure_binary_only("A") == "1010"
    assert TestbenchGenerator._ensure_binary_only("B") == "1011" 
    assert TestbenchGenerator._ensure_binary_only("C") == "1100"
    assert TestbenchGenerator._ensure_binary_only("D") == "1101"
    assert TestbenchGenerator._ensure_binary_only("E") == "1110"
    assert TestbenchGenerator._ensure_binary_only("F") == "1111"
    
    # Test hex patterns
    assert TestbenchGenerator._ensure_binary_only("AA") == "10101010"
    assert TestbenchGenerator._ensure_binary_only("AAAAAAAA") == "10101010" * 4
    assert TestbenchGenerator._ensure_binary_only("FF") == "11111111"
    
    # Test mixed hex and binary
    assert TestbenchGenerator._ensure_binary_only("A0") == "10100000"
    assert TestbenchGenerator._ensure_binary_only("0F") == "00001111"
    
    # Test already binary values (should pass through)
    assert TestbenchGenerator._ensure_binary_only("10101010") == "10101010"
    assert TestbenchGenerator._ensure_binary_only("00000000") == "00000000"
    assert TestbenchGenerator._ensure_binary_only("1") == "1"
    assert TestbenchGenerator._ensure_binary_only("0") == "0"


def test_hex_conversion_in_testbench():
    """Test that hex values in config are converted to binary in VHDL."""
    
    entity = VhdlEntity(
        name="hex_test",
        generics=[],
        ports=[
            VhdlPort("data_in", "in", "std_logic_vector", "(7 downto 0)"),
            VhdlPort("data_out", "out", "std_logic_vector", "(7 downto 0)")
        ]
    )
    
    # Config with hex values (problematic)
    test_vectors = [
        TestVector(
            time_ns=100,
            inputs={
                "data_in": "AA"  # Hex value that should become binary
            },
            expected_outputs={
                "data_out": "FF"  # Hex value that should become binary
            }
        )
    ]
    
    config = TestbenchConfig(test_vectors=test_vectors)
    testbench_data = TestbenchGenerator.generate_testbench_data(entity, config)
    stimulus = testbench_data.stim_proc
    
    # Should convert hex to binary in generated VHDL
    assert 'tb_data_in <= "10101010";' in stimulus  # AA -> 10101010
    assert 'assert tb_data_out = "11111111"' in stimulus  # FF -> 11111111
    
    # Should NOT contain hex characters that would cause GHDL errors
    assert 'tb_data_in <= "AA";' not in stimulus
    assert 'assert tb_data_out = "FF"' not in stimulus


def test_mixed_hex_binary_conversion():
    """Test conversion of mixed hex/binary patterns."""
    
    entity = VhdlEntity(
        name="mixed_test",
        generics=[],
        ports=[
            VhdlPort("pattern", "in", "std_logic_vector", "(15 downto 0)")
        ]
    )
    
    test_vector = TestVector(
        time_ns=100,
        inputs={
            "pattern": "A0F1"  # Mixed hex pattern
        }
    )
    
    config = TestbenchConfig(test_vectors=[test_vector])
    testbench_data = TestbenchGenerator.generate_testbench_data(entity, config)
    stimulus = testbench_data.stim_proc
    
    # A0F1 is 16 bits but signal is only 16 bits, so should fit exactly
    expected_binary = "1010000011110001"  # hex A0F1 = binary 1010000011110001
    assert f'tb_pattern <= "{expected_binary}";' in stimulus


def test_preserve_valid_binary():
    """Test that valid binary values are preserved unchanged."""
    
    entity = VhdlEntity(
        name="binary_test",
        generics=[],
        ports=[
            VhdlPort("data", "in", "std_logic_vector", "(7 downto 0)")
        ]
    )
    
    test_vector = TestVector(
        time_ns=100,
        inputs={
            "data": "10101010"  # Already valid binary
        }
    )
    
    config = TestbenchConfig(test_vectors=[test_vector])
    testbench_data = TestbenchGenerator.generate_testbench_data(entity, config)
    stimulus = testbench_data.stim_proc
    
    # Should preserve valid binary unchanged
    assert 'tb_data <= "10101010";' in stimulus


def test_single_bit_hex_handling():
    """Test that single hex characters in single bit signals are handled."""
    
    entity = VhdlEntity(
        name="bit_test",
        generics=[],
        ports=[
            VhdlPort("enable", "in", "std_logic")
        ]
    )
    
    test_vector = TestVector(
        time_ns=100,
        inputs={
            "enable": "F"  # Hex F should become 1
        }
    )
    
    config = TestbenchConfig(test_vectors=[test_vector])
    testbench_data = TestbenchGenerator.generate_testbench_data(entity, config)
    stimulus = testbench_data.stim_proc
    
    # F should become 1 for single bit (take first bit of 1111)
    assert "tb_enable <= '1';" in stimulus
