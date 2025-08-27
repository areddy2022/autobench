"""Tests for automatic VHDL literal quoting based on signal types."""

import pytest
from autobench.vhdl_parser import VhdlEntity, VhdlPort
from autobench.config import TestbenchConfig, TestVector
from autobench.testbench_generator import TestbenchGenerator


def test_automatic_quoting_conversion():
    """Test that config values are automatically converted to correct VHDL syntax."""
    
    entity = VhdlEntity(
        name="uart_rx",
        generics=[],
        ports=[
            VhdlPort("clk", "in", "std_logic"),
            VhdlPort("rst", "in", "std_logic"),
            VhdlPort("rx", "in", "std_logic"),
            VhdlPort("parallel_out", "out", "std_logic_vector", "(7 downto 0)"),
            VhdlPort("rx_done", "out", "std_logic"),
            VhdlPort("count", "in", "integer")
        ]
    )
    
    # Config with simple unquoted values (like user would naturally write)
    test_vectors = [
        TestVector(
            time_ns=100,
            inputs={
                "rst": "1",          # Should become '1'
                "rx": "0",           # Should become '0'  
                "count": "42"        # Should stay 42
            },
            expected_outputs={
                "parallel_out": "00000000",  # Should become "00000000"
                "rx_done": "0"               # Should become '0'
            }
        ),
        TestVector(
            time_ns=200,
            inputs={
                "rst": "0",          # Should become '0'
                "rx": "1"            # Should become '1'
            },
            expected_outputs={
                "parallel_out": "10101010",  # Should become "10101010"
                "rx_done": "1"               # Should become '1'
            }
        )
    ]
    
    config = TestbenchConfig(test_vectors=test_vectors)
    testbench_data = TestbenchGenerator.generate_testbench_data(entity, config)
    stimulus = testbench_data.stim_proc
    
    # Check that single bit signals get single quotes
    assert "tb_rst <= '1';" in stimulus
    assert "tb_rst <= '0';" in stimulus
    assert "tb_rx <= '0';" in stimulus
    assert "tb_rx <= '1';" in stimulus
    
    # Check that bit vector signals get double quotes
    assert 'tb_parallel_out = "00000000"' in stimulus  # In assertion
    assert 'tb_parallel_out = "10101010"' in stimulus  # In assertion
    
    # Check that single bit output signals get single quotes
    assert "tb_rx_done = '0'" in stimulus
    assert "tb_rx_done = '1'" in stimulus
    
    # Check that integer signals get no quotes
    assert "tb_count <= 42;" in stimulus


def test_already_quoted_values_preserved():
    """Test that already properly quoted values are preserved."""
    
    entity = VhdlEntity(
        name="test",
        generics=[],
        ports=[
            VhdlPort("bit_sig", "in", "std_logic"),
            VhdlPort("vector_sig", "in", "std_logic_vector", "(3 downto 0)"),
            VhdlPort("int_sig", "in", "integer")
        ]
    )
    
    # Mix of properly quoted and unquoted values
    test_vector = TestVector(
        time_ns=100,
        inputs={
            "bit_sig": "'1'",       # Already properly quoted - should preserve
            "vector_sig": "1010",   # Unquoted - should add double quotes
            "int_sig": "123"        # Integer - should stay unquoted
        }
    )
    
    config = TestbenchConfig(test_vectors=[test_vector])
    testbench_data = TestbenchGenerator.generate_testbench_data(entity, config)
    stimulus = testbench_data.stim_proc
    
    # Already quoted should be preserved
    assert "tb_bit_sig <= '1';" in stimulus
    
    # Unquoted should get proper quotes added
    assert 'tb_vector_sig <= "1010";' in stimulus
    
    # Integer should stay unquoted
    assert "tb_int_sig <= 123;" in stimulus


def test_convert_to_vhdl_literal():
    """Test the conversion function directly."""
    ports = [
        VhdlPort("enable", "in", "std_logic"),
        VhdlPort("data", "in", "std_logic_vector", "(7 downto 0)"),
        VhdlPort("count", "in", "integer"),
        VhdlPort("unknown", "in", "custom_type")
    ]
    
    # Test STD_LOGIC conversion
    assert TestbenchGenerator._convert_to_vhdl_literal("1", "enable", ports) == "'1'"
    assert TestbenchGenerator._convert_to_vhdl_literal("0", "enable", ports) == "'0'"
    
    # Test STD_LOGIC_VECTOR conversion  
    assert TestbenchGenerator._convert_to_vhdl_literal("10101010", "data", ports) == '"10101010"'
    assert TestbenchGenerator._convert_to_vhdl_literal("00000000", "data", ports) == '"00000000"'
    
    # Test INTEGER conversion (no quotes)
    assert TestbenchGenerator._convert_to_vhdl_literal("42", "count", ports) == "42"
    assert TestbenchGenerator._convert_to_vhdl_literal("123", "count", ports) == "123"
    
    # Test unknown type (defaults to single bit)
    assert TestbenchGenerator._convert_to_vhdl_literal("1", "unknown", ports) == "'1'"
    
    # Test already properly quoted values are preserved
    assert TestbenchGenerator._convert_to_vhdl_literal("'1'", "enable", ports) == "'1'"
    assert TestbenchGenerator._convert_to_vhdl_literal('"1010"', "data", ports) == '"1010"'


def test_is_properly_quoted_vhdl():
    """Test detection of properly quoted VHDL values."""
    
    # Properly quoted single bits
    assert TestbenchGenerator._is_properly_quoted_vhdl("'0'") == True
    assert TestbenchGenerator._is_properly_quoted_vhdl("'1'") == True
    
    # Properly quoted bit vectors
    assert TestbenchGenerator._is_properly_quoted_vhdl('"0000"') == True
    assert TestbenchGenerator._is_properly_quoted_vhdl('"10101010"') == True
    
    # Unquoted integers
    assert TestbenchGenerator._is_properly_quoted_vhdl("42") == True
    assert TestbenchGenerator._is_properly_quoted_vhdl("123") == True
    assert TestbenchGenerator._is_properly_quoted_vhdl("-5") == True
    
    # Improperly quoted or unquoted (need signal type context)
    assert TestbenchGenerator._is_properly_quoted_vhdl("0") == False  # Unquoted single bit
    assert TestbenchGenerator._is_properly_quoted_vhdl("1010") == False  # Unquoted binary pattern


def test_looks_like_bit_vector():
    """Test detection of bit vector patterns."""
    
    # Should be detected as bit vectors
    assert TestbenchGenerator._looks_like_bit_vector("00000000") == True
    assert TestbenchGenerator._looks_like_bit_vector("10101010") == True
    assert TestbenchGenerator._looks_like_bit_vector("111100001111") == True
    
    # Should NOT be detected as bit vectors
    assert TestbenchGenerator._looks_like_bit_vector("0") == False  # Single bit
    assert TestbenchGenerator._looks_like_bit_vector("1") == False  # Single bit
    assert TestbenchGenerator._looks_like_bit_vector("123") == False  # Contains non-binary
    assert TestbenchGenerator._looks_like_bit_vector("abc") == False  # Not binary at all


def test_user_friendly_config_format():
    """Test that users can write natural config values."""
    
    entity = VhdlEntity(
        name="simple_uart",
        generics=[],
        ports=[
            VhdlPort("rst", "in", "std_logic"),
            VhdlPort("rx", "in", "std_logic"),  
            VhdlPort("data_out", "out", "std_logic_vector", "(7 downto 0)"),
            VhdlPort("ready", "out", "std_logic")
        ]
    )
    
    # Natural user config (no quotes needed!)
    test_vector = TestVector(
        time_ns=100,
        inputs={
            "rst": "1",        # User types simple "1"
            "rx": "0"          # User types simple "0"
        },
        expected_outputs={
            "data_out": "11110000",  # User types bit pattern directly
            "ready": "1"             # User types simple "1"
        }
    )
    
    config = TestbenchConfig(test_vectors=[test_vector])
    testbench_data = TestbenchGenerator.generate_testbench_data(entity, config)
    stimulus = testbench_data.stim_proc
    
    # Tool should automatically generate correct VHDL
    assert "tb_rst <= '1';" in stimulus          # Single bit gets single quotes
    assert "tb_rx <= '0';" in stimulus           # Single bit gets single quotes  
    assert 'tb_data_out = "11110000"' in stimulus # Vector gets double quotes
    assert "tb_ready = '1'" in stimulus          # Single bit gets single quotes
