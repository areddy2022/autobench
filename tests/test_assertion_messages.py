"""Tests for enhanced assertion failure messages."""

import pytest
from autobench.vhdl_parser import VhdlEntity, VhdlPort
from autobench.config import TestbenchConfig, TestVector
from autobench.testbench_generator import TestbenchGenerator


def test_enhanced_assertion_messages():
    """Test that assertion messages include expected vs actual values."""
    
    entity = VhdlEntity(
        name="assertion_test",
        generics=[],
        ports=[
            VhdlPort("bit_signal", "in", "std_logic"),
            VhdlPort("vector_signal", "in", "std_logic_vector", "(7 downto 0)"),
            VhdlPort("int_signal", "in", "integer"),
            VhdlPort("bit_out", "out", "std_logic"),
            VhdlPort("vector_out", "out", "std_logic_vector", "(7 downto 0)"),
            VhdlPort("int_out", "out", "integer")
        ]
    )
    
    test_vector = TestVector(
        time_ns=100,
        inputs={
            "bit_signal": "1",
            "vector_signal": "10101010",
            "int_signal": "42"
        },
        expected_outputs={
            "bit_out": "1",
            "vector_out": "11110000", 
            "int_out": "123"
        }
    )
    
    config = TestbenchConfig(test_vectors=[test_vector])
    testbench_data = TestbenchGenerator.generate_testbench_data(entity, config)
    stimulus = testbench_data.stim_proc
    
    # Check STD_LOGIC assertion includes actual value
    assert 'report "Test 1: bit_out mismatch - expected \'1\', got " & std_logic\'image(tb_bit_out)' in stimulus
    
    # Check STD_LOGIC_VECTOR assertion includes expected value and waveform note
    assert 'report "Test 1: vector_out mismatch - expected "11110000" (check waveform for actual value)"' in stimulus
    
    # Check INTEGER assertion includes actual value
    assert 'report "Test 1: int_out mismatch - expected 123, got " & integer\'image(tb_int_out)' in stimulus


def test_assertion_message_generation():
    """Test the assertion message generation function directly."""
    
    # Test STD_LOGIC message
    bit_port = VhdlPort("enable", "out", "std_logic")
    msg = TestbenchGenerator._generate_assertion_message(1, "enable", "'1'", bit_port)
    expected = '"Test 1: enable mismatch - expected \'1\', got " & std_logic\'image(tb_enable)'
    assert msg == expected
    
    # Test STD_LOGIC_VECTOR message  
    vector_port = VhdlPort("data", "out", "std_logic_vector", "(7 downto 0)")
    msg = TestbenchGenerator._generate_assertion_message(2, "data", '"10101010"', vector_port)
    expected = '"Test 2: data mismatch - expected "10101010" (check waveform for actual value)"'
    assert msg == expected
    
    # Test INTEGER message
    int_port = VhdlPort("count", "out", "integer")
    msg = TestbenchGenerator._generate_assertion_message(3, "count", "42", int_port)
    expected = '"Test 3: count mismatch - expected 42, got " & integer\'image(tb_count)'
    assert msg == expected
    
    # Test unknown type message
    unknown_port = VhdlPort("custom", "out", "my_type")
    msg = TestbenchGenerator._generate_assertion_message(4, "custom", "value", unknown_port)
    expected = '"Test 4: custom mismatch - expected value"'
    assert msg == expected
    
    # Test with no port info
    msg = TestbenchGenerator._generate_assertion_message(5, "mystery", "X", None)
    expected = '"Test 5: mystery mismatch - expected X"'
    assert msg == expected


def test_assertion_in_generated_vhdl():
    """Test that assertions appear correctly in generated VHDL testbench."""
    
    entity = VhdlEntity(
        name="test_entity",
        generics=[],
        ports=[
            VhdlPort("clk", "in", "std_logic"),
            VhdlPort("enable", "out", "std_logic"),
            VhdlPort("count", "out", "integer")
        ]
    )
    
    test_vector = TestVector(
        time_ns=50,
        inputs={"clk": "0"},
        expected_outputs={
            "enable": "1",
            "count": "5"
        },
        description="Test assertion messages"
    )
    
    config = TestbenchConfig(test_vectors=[test_vector])
    testbench_data = TestbenchGenerator.generate_testbench_data(entity, config)
    
    # Apply to a simple template to see the full VHDL output
    template = """
begin
    process
    begin
{stim_proc}
    end process;
end;
"""
    
    vhdl_output = testbench_data.apply_to_template(template)
    
    # Should contain detailed assertion messages
    assert "assert tb_enable = '1'" in vhdl_output
    assert "enable mismatch - expected '1', got" in vhdl_output
    assert "std_logic'image(tb_enable)" in vhdl_output
    
    assert "assert tb_count = 5" in vhdl_output  
    assert "count mismatch - expected 5, got" in vhdl_output
    assert "integer'image(tb_count)" in vhdl_output


def test_multiple_signals_in_same_test():
    """Test assertion messages when multiple signals are checked in one test."""
    
    entity = VhdlEntity(
        name="multi_signal_test",
        generics=[],
        ports=[
            VhdlPort("ready", "out", "std_logic"),
            VhdlPort("valid", "out", "std_logic"), 
            VhdlPort("data", "out", "std_logic_vector", "(3 downto 0)")
        ]
    )
    
    test_vector = TestVector(
        time_ns=100,
        inputs={},  # No input changes
        expected_outputs={
            "ready": "1",
            "valid": "0", 
            "data": "1010"
        },
        description="Check multiple outputs"
    )
    
    config = TestbenchConfig(test_vectors=[test_vector])
    testbench_data = TestbenchGenerator.generate_testbench_data(entity, config)
    stimulus = testbench_data.stim_proc
    
    # Should have separate assertions for each signal
    assert 'assert tb_ready = \'1\'' in stimulus
    assert 'assert tb_valid = \'0\'' in stimulus
    assert 'assert tb_data = "1010"' in stimulus
    
    # Each should have its own detailed error message
    assert "ready mismatch - expected '1'" in stimulus
    assert "valid mismatch - expected '0'" in stimulus
    assert "data mismatch - expected \"1010\"" in stimulus
