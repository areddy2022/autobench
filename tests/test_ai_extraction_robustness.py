"""Tests for robust AI response extraction."""

import pytest
from autobench.ai_integration import AIConfigGenerator
from autobench.vhdl_parser import VhdlEntity, VhdlPort


def test_extract_toml_with_explanatory_text():
    """Test extraction of TOML from AI response with explanatory text."""
    generator = AIConfigGenerator(project_id='test-project')
    
    # Simulate problematic AI response with explanation before TOML
    ai_response = """# AI-generated testbench configuration for a LIFO (Last-In, First-Out) stack.
# The test plan covers reset, push/pop operations, full and empty boundary 
# conditions, and overflow/underflow scenarios.

```toml
clock_period_ns = 10
reset_duration_ns = 100

[generics]
DATA_WIDTH = "8"
DEPTH = "16"

[[test_vectors]]
time_ns = 100
description = "Test reset behavior"

[test_vectors.inputs]
rst = "1"
push = "0"
pop = "0"

[test_vectors.expected_outputs]
empty = "1"
full = "0"
```

This configuration provides comprehensive testing for the LIFO stack implementation."""
    
    toml_content = generator._extract_toml_from_response(ai_response)
    
    # Should extract the TOML content correctly
    assert "clock_period_ns = 10" in toml_content
    assert "[generics]" in toml_content
    assert "[[test_vectors]]" in toml_content
    assert "DATA_WIDTH" in toml_content
    
    # Should NOT include the explanatory text
    assert "AI-generated testbench configuration" not in toml_content
    assert "This configuration provides" not in toml_content


def test_extract_toml_without_code_blocks():
    """Test extraction when AI doesn't use code blocks properly."""
    generator = AIConfigGenerator(project_id='test-project')
    
    # AI response without proper code blocks
    ai_response = """Here's the configuration you requested:

clock_period_ns = 20
reset_duration_ns = 150

[generics]
WIDTH = "16"

[[test_vectors]]
time_ns = 50
description = "Basic test"

[test_vectors.inputs]
enable = "1"
data = "11110000"

This should work for your testbench."""
    
    toml_content = generator._extract_toml_from_response(ai_response)
    
    # Should extract the TOML-like content
    assert "clock_period_ns = 20" in toml_content
    assert "[generics]" in toml_content
    assert "[[test_vectors]]" in toml_content
    
    # Should NOT include the introduction or conclusion
    assert "Here's the configuration" not in toml_content
    assert "This should work" not in toml_content


def test_clean_trailing_text():
    """Test removal of trailing explanatory text."""
    generator = AIConfigGenerator(project_id='test-project')
    
    toml_with_explanation = """clock_period_ns = 10

[[test_vectors]]
time_ns = 100

[test_vectors.inputs]
enable = "1"

This configuration is designed to test the main functionality of your component.
The test vectors cover basic operations and should provide good coverage.
You can modify these values as needed for your specific requirements."""
    
    cleaned = generator._clean_trailing_text(toml_with_explanation)
    
    # Should keep TOML content
    assert "clock_period_ns = 10" in cleaned
    assert "[[test_vectors]]" in cleaned
    assert '[test_vectors.inputs]' in cleaned
    assert 'enable = "1"' in cleaned
    
    # Should remove explanatory paragraphs
    assert "This configuration is designed" not in cleaned
    assert "You can modify these values" not in cleaned


def test_looks_like_toml_validation():
    """Test enhanced TOML validation."""
    generator = AIConfigGenerator(project_id='test-project')
    
    # Valid TOML snippets
    valid_toml = """
    clock_period_ns = 10
    
    [[test_vectors]]
    time_ns = 100
    """
    assert generator._looks_like_toml(valid_toml) == True
    
    # Just explanatory text
    just_text = """
    This is a configuration file that will help you test your VHDL design.
    It includes comprehensive test cases for various scenarios.
    """
    assert generator._looks_like_toml(just_text) == False
    
    # Mixed content (should still be valid if has TOML elements)
    mixed_content = """
    # Some explanation
    clock_period_ns = 10
    More explanation here.
    """
    assert generator._looks_like_toml(mixed_content) == True
