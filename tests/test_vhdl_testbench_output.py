"""Tests for correct VHDL syntax in generated testbench code."""

import pytest
from autobench.vhdl_parser import VhdlEntity, VhdlPort
from autobench.config import TestbenchConfig, TestVector
from autobench.testbench_generator import TestbenchGenerator


def test_vhdl_signal_assignments_from_config():
    """Test that config values are correctly converted to VHDL signal assignments."""
    
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
    
    # Create test vectors with properly quoted values
    test_vectors = [
        TestVector(
            time_ns=100,
            inputs={
                "clk": "'0'",           # Single bit should stay as '0'
                "enable": "'1'",        # Single bit should stay as '1'  
                "data_in": '"10101010"', # Bit vector should stay as "10101010"
                "count": "42"           # Integer should stay as 42
            },
            expected_outputs={
                "ready": "'1'",         # Single bit output
                "data_out": '"01010101"' # Bit vector output
            },
            description="Test proper VHDL syntax"
        ),
        TestVector(
            time_ns=200,
            inputs={
                "enable": "'0'",        # Only enable changes
            },
            description="Test optimized vectors"
        )
    ]
    
    config = TestbenchConfig(
        clock_period_ns=10,
        reset_duration_ns=100,
        test_vectors=test_vectors
    )
    
    testbench_data = TestbenchGenerator.generate_testbench_data(entity, config)
    stimulus = testbench_data.stim_proc
    
    # Check that single bit assignments use single quotes (no extra quotes)
    assert "tb_clk <= '0';" in stimulus
    assert "tb_enable <= '1';" in stimulus
    assert "tb_enable <= '0';" in stimulus  # From second test vector
    
    # Check that bit vector assignments use double quotes (no extra quotes)
    assert 'tb_data_in <= "10101010";' in stimulus
    
    # Check that integer assignments have no quotes
    assert "tb_count <= 42;" in stimulus
    
    # Check assertions use correct syntax
    assert "assert tb_ready = '1'" in stimulus
    assert 'assert tb_data_out = "01010101"' in stimulus
    
    # Verify no double-quoting issues (like "'0'" becoming "''0''")
    assert "''0''" not in stimulus
    assert '""10101010""' not in stimulus


def test_config_string_handling():
    """Test that configuration strings are properly handled in VHDL generation."""
    
    entity = VhdlEntity(
        name="simple",
        generics=[],
        ports=[
            VhdlPort("bit_signal", "in", "std_logic"),
            VhdlPort("vector_signal", "in", "std_logic_vector", "(3 downto 0)")
        ]
    )
    
    # Test with different quoting styles in config
    test_vectors = [
        TestVector(
            time_ns=50,
            inputs={
                "bit_signal": "'0'",         # Correct single bit
                "vector_signal": '"1010"'    # Correct bit vector
            }
        ),
        TestVector(
            time_ns=100,
            inputs={
                "bit_signal": "'1'",         # Changed single bit
                "vector_signal": '"0101"'    # Changed bit vector
            }
        )
    ]
    
    config = TestbenchConfig(test_vectors=test_vectors)
    testbench_data = TestbenchGenerator.generate_testbench_data(entity, config)
    stimulus = testbench_data.stim_proc
    
    # Verify the actual VHDL assignments are clean
    lines = stimulus.split('\n')
    
    # Find signal assignment lines
    bit_assignments = [line.strip() for line in lines if 'tb_bit_signal <=' in line]
    vector_assignments = [line.strip() for line in lines if 'tb_vector_signal <=' in line]
    
    # Check bit signal assignments
    assert "tb_bit_signal <= '0';" in bit_assignments
    assert "tb_bit_signal <= '1';" in bit_assignments
    
    # Check vector signal assignments  
    assert 'tb_vector_signal <= "1010";' in vector_assignments
    assert 'tb_vector_signal <= "0101";' in vector_assignments


def test_mixed_signal_types_in_vhdl():
    """Test various signal types are handled correctly in generated VHDL."""
    
    entity = VhdlEntity(
        name="mixed",
        generics=[],
        ports=[
            VhdlPort("std_bit", "in", "std_logic"),
            VhdlPort("bit_vector", "in", "std_logic_vector", "(7 downto 0)"),
            VhdlPort("number", "in", "integer"),
            VhdlPort("result_bit", "out", "std_logic"),
            VhdlPort("result_vector", "out", "std_logic_vector", "(3 downto 0)")
        ]
    )
    
    test_vector = TestVector(
        time_ns=100,
        inputs={
            "std_bit": "'1'",
            "bit_vector": '"11110000"',
            "number": "255"
        },
        expected_outputs={
            "result_bit": "'0'",
            "result_vector": '"1111"'
        }
    )
    
    config = TestbenchConfig(test_vectors=[test_vector])
    testbench_data = TestbenchGenerator.generate_testbench_data(entity, config)
    stimulus = testbench_data.stim_proc
    
    # Check input assignments
    assert "tb_std_bit <= '1';" in stimulus
    assert 'tb_bit_vector <= "11110000";' in stimulus  
    assert "tb_number <= 255;" in stimulus
    
    # Check output assertions
    assert "assert tb_result_bit = '0'" in stimulus
    assert 'assert tb_result_vector = "1111"' in stimulus


def test_reset_sequence_syntax():
    """Test that reset sequence uses correct VHDL syntax."""
    
    entity = VhdlEntity(
        name="simple",
        generics=[],
        ports=[VhdlPort("rst", "in", "std_logic")]
    )
    
    config = TestbenchConfig(reset_duration_ns=50)
    testbench_data = TestbenchGenerator.generate_testbench_data(entity, config)
    stimulus = testbench_data.stim_proc
    
    # Reset sequence should use single quotes for std_logic
    assert "tb_rst <= '1';" in stimulus
    assert "tb_rst <= '0';" in stimulus
    assert "wait for 50 ns;" in stimulus
