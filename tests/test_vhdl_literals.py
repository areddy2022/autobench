"""Tests for correct VHDL literal syntax."""

import pytest
from autobench.config import _get_default_value, generate_baseline_config
from autobench.testbench_generator import TestbenchGenerator
from autobench.vhdl_parser import VhdlEntity, VhdlPort, VhdlGeneric


def test_default_value_syntax():
    """Test that default values are unquoted (quoting added during VHDL generation)."""
    
    # All values should be unquoted raw values
    assert _get_default_value("std_logic", None) == "0"
    assert _get_default_value("STD_LOGIC", None) == "0"
    
    # Bit vectors return raw bit patterns
    assert _get_default_value("std_logic_vector", "(7 downto 0)") == "00000000"
    assert _get_default_value("STD_LOGIC_VECTOR", "(3 downto 0)") == "00000000"
    
    # Single bit vectors return simple value
    assert _get_default_value("std_logic_vector", None) == "0"
    
    # Integer values are unquoted
    assert _get_default_value("integer", None) == "0"
    assert _get_default_value("INTEGER", None) == "0"
    
    # Unknown types default to simple value
    assert _get_default_value("custom_type", None) == "0"


def test_baseline_config_syntax():
    """Test that baseline config generation creates simple unquoted values."""
    entity = VhdlEntity(
        name="test_entity",
        generics=[],
        ports=[
            VhdlPort("clk", "in", "std_logic"),
            VhdlPort("enable", "in", "std_logic"),
            VhdlPort("data_in", "in", "std_logic_vector", "(7 downto 0)"),
            VhdlPort("count", "in", "integer"),
            VhdlPort("ready", "out", "std_logic"),
            VhdlPort("data_out", "out", "std_logic_vector", "(7 downto 0)")
        ]
    )
    
    config = generate_baseline_config(entity)
    
    # Check input values are simple unquoted values
    test_vector = config.test_vectors[0]
    
    # All values should be unquoted in config
    assert test_vector.inputs["clk"] == "0"
    assert test_vector.inputs["enable"] == "0"
    assert test_vector.inputs["data_in"] == "00000000"
    assert test_vector.inputs["count"] == "0"
    
    # Output expectations should also be unquoted in config
    assert test_vector.expected_outputs["ready"] == "0"
    assert test_vector.expected_outputs["data_out"] == "00000000"


def test_testbench_signal_initialization():
    """Test that testbench signals are initialized with correct syntax."""
    entity = VhdlEntity(
        name="test_entity",
        generics=[],
        ports=[
            VhdlPort("clk", "in", "std_logic"),
            VhdlPort("data", "in", "std_logic_vector", "(7 downto 0)"),
            VhdlPort("count", "in", "integer"),
            VhdlPort("result", "out", "std_logic")
        ]
    )
    
    testbench_data = TestbenchGenerator.generate_testbench_data(entity)
    signals = testbench_data.internal_signals
    
    # STD_LOGIC signals should initialize with single quotes
    assert "tb_clk : STD_LOGIC := '0';" in signals
    assert "tb_result : STD_LOGIC := '0';" in signals
    
    # STD_LOGIC_VECTOR signals should initialize with (others => '0')
    assert "tb_data : STD_LOGIC_VECTOR" in signals
    assert "(others => '0')" in signals
    
    # INTEGER signals should initialize without quotes
    assert "tb_count : INTEGER := 0;" in signals


def test_basic_test_generation_syntax():
    """Test that basic test generation uses correct literal syntax."""
    entity = VhdlEntity(
        name="test_entity", 
        generics=[],
        ports=[
            VhdlPort("enable", "in", "std_logic"),
            VhdlPort("data", "in", "std_logic_vector", "(3 downto 0)")
        ]
    )
    
    testbench_data = TestbenchGenerator.generate_testbench_data(entity)
    stimulus = testbench_data.stim_proc
    
    # STD_LOGIC assignments should use single quotes
    assert "tb_enable <= '1';" in stimulus
    assert "tb_enable <= '0';" in stimulus
    
    # STD_LOGIC_VECTOR assignments should use (others => 'X') syntax
    assert "tb_data <= (others => '1');" in stimulus
    assert "tb_data <= (others => '0');" in stimulus


def test_mixed_signal_types():
    """Test handling of mixed signal types with unquoted config values."""
    entity = VhdlEntity(
        name="mixed_entity",
        generics=[],
        ports=[
            VhdlPort("std_bit", "in", "std_logic"),
            VhdlPort("bit_vector", "in", "std_logic_vector", "(15 downto 0)"),
            VhdlPort("number", "in", "integer"),
            VhdlPort("custom", "in", "my_custom_type"),
        ]
    )
    
    config = generate_baseline_config(entity)
    test_vector = config.test_vectors[0]
    
    # All config values should be unquoted (quoting happens during VHDL generation)
    assert test_vector.inputs["std_bit"] == "0"
    assert test_vector.inputs["bit_vector"] == "00000000"
    assert test_vector.inputs["number"] == "0" 
    assert test_vector.inputs["custom"] == "0"
