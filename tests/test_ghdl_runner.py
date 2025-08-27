"""Tests for GHDL runner module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from autobench.ghdl_runner import GHDLRunner, TestResult, SimulationResult, run_ghdl_simulation


def test_ghdl_check_available():
    """Test GHDL availability check."""
    runner = GHDLRunner()
    
    # Mock successful GHDL check
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        assert runner.check_ghdl_available() == True
        mock_run.assert_called_once_with(
            ["ghdl", "--version"], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
    
    # Mock GHDL not available
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = FileNotFoundError()
        assert runner.check_ghdl_available() == False


def test_parse_test_results():
    """Test parsing of GHDL assertion output."""
    runner = GHDLRunner()
    
    # Sample GHDL output with assertions
    ghdl_output = """
testbench.vhd:45:9:@100ns:(assertion): Test 1: counter mismatch
testbench.vhd:52:9:@200ns:(error): Test 2: overflow condition failed
some other output
testbench.vhd:60:9:@300ns:(note): Test 3: reset successful
    """
    
    results = runner._parse_test_results(ghdl_output)
    
    assert len(results) == 3
    
    # Check first result
    assert results[0].test_name == "Test 1"
    assert results[0].passed == False  # assertion typically means failure
    assert results[0].time == "100ns"
    assert "counter mismatch" in results[0].message
    
    # Check note result (should be passing)
    assert results[2].test_name == "Test 3" 
    assert results[2].passed == True  # note severity typically means info/pass
    assert results[2].severity == "note"


def test_extract_test_name():
    """Test extraction of test names from messages."""
    runner = GHDLRunner()
    
    # Test basic test name extraction
    result = runner._extract_test_name("Test 1: counter value incorrect")
    assert "Test 1" == result
    
    result = runner._extract_test_name("Testing overflow condition")
    assert "Test overflow" == result
    
    # Test fallback for unrecognized patterns
    result = runner._extract_test_name("Some random message")
    assert "Some random message" == result


def test_is_passing_assertion():
    """Test determination of passing vs failing assertions."""
    runner = GHDLRunner()
    
    # Passing cases
    assert runner._is_passing_assertion("Test passed successfully", "note") == True
    assert runner._is_passing_assertion("Operation completed OK", "info") == True
    assert runner._is_passing_assertion("Success: data matches", "error") == True
    
    # Failing cases  
    assert runner._is_passing_assertion("Counter mismatch", "error") == False
    assert runner._is_passing_assertion("Timeout occurred", "assertion") == False
    assert runner._is_passing_assertion("Data corruption detected", "failure") == False


@patch('subprocess.run')
def test_compile_and_simulate_success(mock_run):
    """Test successful compilation and simulation."""
    runner = GHDLRunner()
    
    # Mock successful subprocess calls
    mock_run.side_effect = [
        # ghdl --version check
        MagicMock(returncode=0),
        # ghdl -a entity.vhd
        MagicMock(returncode=0, stderr=""),
        # ghdl -a testbench.vhd  
        MagicMock(returncode=0, stderr=""),
        # ghdl -e testbench
        MagicMock(returncode=0, stderr=""),
        # ghdl -r testbench
        MagicMock(returncode=0, stdout="Simulation completed\n", stderr="")
    ]
    
    entity_file = Path("entity.vhd")
    testbench_file = Path("testbench.vhd")
    
    result = runner.compile_and_simulate(
        entity_file, testbench_file, "entity", "testbench"
    )
    
    assert result.success == True
    assert len(result.errors) == 0
    assert "Simulation completed" in result.simulation_output


@patch('subprocess.run')  
def test_compile_and_simulate_compilation_failure(mock_run):
    """Test compilation failure handling."""
    runner = GHDLRunner()
    
    # Mock GHDL available check + compilation failure
    mock_run.side_effect = [
        # ghdl --version check
        MagicMock(returncode=0),
        # ghdl -a entity.vhd fails
        MagicMock(returncode=1, stderr="entity.vhd:10:15: syntax error")
    ]
    
    entity_file = Path("entity.vhd")
    testbench_file = Path("testbench.vhd")
    
    result = runner.compile_and_simulate(
        entity_file, testbench_file, "entity", "testbench"
    )
    
    assert result.success == False
    assert len(result.errors) > 0
    assert "syntax error" in result.errors[0]


def test_cleanup_work_files():
    """Test cleanup of GHDL work files."""
    # Just test that the method can be called without error
    # Actual file operations are mocked at a lower level in integration tests
    runner = GHDLRunner()
    
    # This should not raise an exception
    runner.cleanup_work_files()
    
    # Test passes if no exception is raised
    assert True


@patch('autobench.ghdl_runner.GHDLRunner')
def test_run_ghdl_simulation_convenience_function(mock_runner_class):
    """Test the convenience function for running simulations."""
    # Mock runner instance and result
    mock_runner = Mock()
    mock_result = SimulationResult(
        success=True,
        compilation_output="",
        simulation_output="Test completed",
        test_results=[],
        waveform_file=Path("test.ghw")
    )
    mock_runner.compile_and_simulate.return_value = mock_result
    mock_runner_class.return_value = mock_runner
    
    entity_file = Path("entity.vhd")
    testbench_file = Path("testbench.vhd")
    
    result = run_ghdl_simulation(
        entity_file=entity_file,
        testbench_file=testbench_file,
        entity_name="entity",
        testbench_name="testbench"
    )
    
    assert result.success == True
    assert result.waveform_file == Path("test.ghw")
    mock_runner.cleanup_work_files.assert_called_once()
