"""AI integration for intelligent config generation using Google Vertex AI."""

import os
from pathlib import Path
from typing import Optional
import google.genai as genai

from .vhdl_parser import VhdlParser, VhdlEntity
from .config import save_config, TestbenchConfig


class AIConfigGenerator:
    """AI-powered configuration generator using Google Vertex AI."""

    def __init__(self, project_id: Optional[str] = None, location: Optional[str] = None):
        """Initialize AI config generator."""
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        
        if not self.project_id:
            raise ValueError(
                "Google Cloud project ID required. Set GOOGLE_CLOUD_PROJECT environment variable "
                "or pass project_id parameter."
            )
        
        # Initialize Vertex AI client
        self.client = genai.Client(
            vertexai=True,
            project=self.project_id,
            location=self.location
        )

    def generate_config(
        self, 
        vhdl_file: Path, 
        additional_prompt: Optional[str] = None,
        verbose: bool = False
    ) -> TestbenchConfig:
        """Generate intelligent configuration using AI."""
        
        # Parse VHDL file to understand the entity
        if verbose:
            print(f"Parsing VHDL file: {vhdl_file}")
        
        entity = VhdlParser.parse_file(vhdl_file)
        vhdl_content = vhdl_file.read_text(encoding='utf-8')
        
        # Read README for context
        readme_path = Path(__file__).parent.parent / "README.md"
        readme_content = ""
        if readme_path.exists():
            readme_content = readme_path.read_text(encoding='utf-8')
        
        # Construct the prompt
        prompt = self._build_prompt(entity, vhdl_content, readme_content, additional_prompt)
        
        if verbose:
            print("Generating AI-powered configuration...")
        
        # Generate response from Vertex AI
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-pro',
                contents=prompt
            )
            
            if verbose:
                print("AI response received, parsing configuration...")
            
            # Parse the AI response to extract configuration
            config = self._parse_ai_response(response.text, entity)
            
            return config
            
        except Exception as e:
            raise RuntimeError(f"Failed to generate AI configuration: {e}")

    def _build_prompt(
        self, 
        entity: VhdlEntity, 
        vhdl_content: str, 
        readme_content: str,
        additional_prompt: Optional[str] = None
    ) -> str:
        """Build the prompt for Gemini."""
        
        prompt = f"""You are an expert VHDL testbench designer. I need you to analyze a VHDL entity and generate an intelligent testbench configuration.

## Context - Tool Documentation:
{readme_content}

## VHDL Entity to Test:
```vhdl
{vhdl_content}
```

## Entity Analysis:
- Name: {entity.name}
- Generics: {len(entity.generics)} ({', '.join(g.name for g in entity.generics)})
- Ports: {len(entity.ports)} ({', '.join(f"{p.name}({p.direction})" for p in entity.ports)})

## Task:
Generate a comprehensive testbench configuration in TOML format that includes:

1. **Appropriate timing parameters** based on the entity type and complexity
2. **Smart generic values** that make sense for testing
3. **Comprehensive test vectors** that exercise all functionality:
   - Reset behavior
   - Normal operations
   - Edge cases
   - Corner cases specific to this entity type
4. **Expected outputs** for validation

## Guidelines:
- Analyze the entity name and port names to understand the component's purpose
- Generate realistic test scenarios based on the component type (e.g., counter, FIFO, ALU, etc.)
- Use appropriate data patterns and timing
- Include descriptive test case names
- Consider typical VHDL design patterns and common verification scenarios
- **ABSOLUTE TIMING**: time_ns values are absolute timestamps (100ns, 250ns, 300ns) not relative durations
- **OPTIMIZE TEST VECTORS**: Only include inputs that change from the previous test vector - signals maintain their values in VHDL until explicitly changed
- Group related signal changes into logical test steps
- Use meaningful time intervals between significant state changes
- **BINARY VALUES ONLY**: Use only binary patterns (0, 1, 00000000, 10101010) - do NOT use hex letters (A,B,C,D,E,F)

"""

        if additional_prompt:
            prompt += f"\n## Additional Requirements:\n{additional_prompt}\n"

        prompt += """
## Output Format:
ABSOLUTELY CRITICAL: You must respond with ONLY a TOML code block. No explanations, no introductions, no conclusions.

Your entire response must be EXACTLY this format (nothing else):

```toml
clock_period_ns = 10
reset_duration_ns = 100

[generics]
DATA_WIDTH = "8"

[[test_vectors]]
time_ns = 50
description = "Reset and initialize all inputs"

[test_vectors.inputs]
enable = "0"
data_in = "00000000"
write_enable = "0"

[[test_vectors]]
time_ns = 100
description = "Enable the component"

[test_vectors.inputs]
enable = "1"

[test_vectors.expected_outputs]
ready = "1"
```

CRITICAL INSTRUCTIONS:
- Your response must START IMMEDIATELY with ```toml (no introduction, no explanation)
- Include ONLY the TOML configuration content inside the code block
- Your response must END with ``` (no conclusion, no additional text)
- Do NOT provide any explanatory text before or after the code block
- ENSURE proper TOML structure: each test vector must have its own [[test_vectors]] section
- Use simple unquoted BINARY values: "1", "0", "10101010" (not "'1'", "\"10101010\"") 
- ONLY use 0s and 1s - do NOT use hex letters A,B,C,D,E,F
- Test vectors can have only inputs, only expected_outputs, or both (inputs are optional)

Example response format:
```toml
clock_period_ns = 10
[[test_vectors]]
time_ns = 100
[test_vectors.inputs]
signal = "value"
[test_vectors.expected_outputs]
output = "value"
```
"""
        
        return prompt

    def _parse_ai_response(self, response_text: str, entity: VhdlEntity) -> TestbenchConfig:
        """Parse AI response and convert to TestbenchConfig."""
        import tomllib
        
        # Extract TOML content from the response
        toml_content = self._extract_toml_from_response(response_text)
        
        try:
            # Parse the TOML content
            data = tomllib.loads(toml_content)
            
            # Convert to TestbenchConfig  
            config = TestbenchConfig.from_dict(data)
            
            return config
            
        except Exception as e:
            # If AI response parsing fails, fall back to baseline config
            print(f"Warning: Could not parse AI response ({e}), using baseline config")
            print(f"Full AI response (first 500 chars): {response_text[:500]}...")
            print(f"Extracted TOML content:")
            print("=" * 50)
            print(toml_content)
            print("=" * 50)
            from .config import generate_baseline_config
            return generate_baseline_config(entity)

    def _extract_toml_from_response(self, response_text: str) -> str:
        """Extract TOML content from AI response."""
        import re
        
        # Try multiple patterns to find TOML content in code blocks
        patterns = [
            r'```toml\n?(.*?)```',   # ```toml ... ``` (more flexible)
            r'```TOML\n?(.*?)```',   # ```TOML ... ``` 
            r'```\n(.*?)\n?```',     # ``` ... ``` (generic code block)
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, response_text, re.DOTALL | re.IGNORECASE)
            for match in matches:
                content = match.group(1).strip()
                # Validate that it looks like TOML
                if self._looks_like_toml(content):
                    return content
        
        # More aggressive TOML extraction - look for clear TOML sections
        lines = response_text.strip().split('\n')
        toml_lines = []
        in_toml_section = False
        found_toml_start = False
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip empty lines before TOML starts
            if not line_stripped and not found_toml_start:
                continue
                
            # Look for clear TOML indicators
            is_toml_line = (
                '=' in line_stripped or 
                line_stripped.startswith('[') or 
                line_stripped.startswith('[[') or
                line_stripped.startswith('#') or
                (found_toml_start and line_stripped)  # Continue if we've started
            )
            
            # Start collecting TOML content
            if is_toml_line and not found_toml_start:
                found_toml_start = True
                in_toml_section = True
                
            if in_toml_section:
                toml_lines.append(line)
                
                # Don't stop early - let _clean_trailing_text handle cleanup
        
        result = '\n'.join(toml_lines) if toml_lines else response_text
        
        # Final cleanup - remove trailing explanatory text
        result = self._clean_trailing_text(result)
        
        return result
    
    def _clean_trailing_text(self, toml_content: str) -> str:
        """Clean trailing explanatory text from TOML content."""
        lines = toml_content.split('\n')
        clean_lines = []
        
        # More aggressive approach: only keep lines that are clearly TOML
        for line in lines:
            line_stripped = line.strip()
            
            # Skip empty lines
            if not line_stripped:
                clean_lines.append(line)
                continue
                
            # Keep TOML structure elements
            if (line_stripped.startswith('#') or          # Comments
                '=' in line_stripped or                   # Key-value pairs
                line_stripped.startswith('[') or          # Sections
                line_stripped.startswith('description') or # Description fields
                line_stripped.startswith('time_ns')):     # Time fields
                clean_lines.append(line)
            else:
                # Check if this looks like TOML data within a section
                # Keep lines that look like TOML values even without =
                words = line_stripped.split()
                if (len(words) == 1 and 
                    (words[0].startswith('"') or 
                     words[0].replace('_', '').isalnum())):
                    clean_lines.append(line)
                # Otherwise skip explanatory text
        
        return '\n'.join(clean_lines)

    def _looks_like_toml(self, content: str) -> bool:
        """Check if content looks like valid TOML."""
        # Basic heuristics to validate TOML-like content
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        if not lines:
            return False
        
        # Should have at least some key-value pairs or sections
        has_keyvalue = any('=' in line and not line.startswith('#') for line in lines)
        has_sections = any(line.startswith('[') and line.endswith(']') for line in lines)
        
        return has_keyvalue or has_sections


def generate_ai_config(
    vhdl_file: Path, 
    output_path: Optional[Path] = None,
    additional_prompt: Optional[str] = None,
    project_id: Optional[str] = None,
    location: Optional[str] = None,
    verbose: bool = False
) -> Path:
    """Generate AI-powered configuration and save to file."""
    
    generator = AIConfigGenerator(project_id=project_id, location=location)
    config = generator.generate_config(vhdl_file, additional_prompt, verbose)
    
    # Determine output path
    if not output_path:
        entity = VhdlParser.parse_file(vhdl_file)
        output_path = Path(f"{entity.name}_ai_config.toml")
    
    # Save configuration
    save_config(config, output_path)
    
    return output_path
