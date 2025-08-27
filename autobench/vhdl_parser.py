"""VHDL parser for extracting entity information."""

import re
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path


@dataclass
class VhdlPort:
    """Represents a VHDL port."""
    name: str
    direction: str  # "in", "out", "inout"
    signal_type: str  # "STD_LOGIC", "STD_LOGIC_VECTOR", etc.
    range: Optional[str] = None  # e.g., "(DATA_WIDTH-1 downto 0)"


@dataclass
class VhdlGeneric:
    """Represents a VHDL generic parameter."""
    name: str
    generic_type: str
    default_value: Optional[str] = None


@dataclass
class VhdlEntity:
    """Represents a complete VHDL entity."""
    name: str
    generics: List[VhdlGeneric]
    ports: List[VhdlPort]


class VhdlParser:
    """Parser for VHDL files to extract entity information."""

    @staticmethod
    def parse_file(path: Path) -> VhdlEntity:
        """Parse a VHDL file and return entity information."""
        try:
            content = path.read_text(encoding='utf-8')
            return VhdlParser.parse_content(content)
        except FileNotFoundError:
            raise FileNotFoundError(f"Failed to read VHDL file '{path}': File not found")
        except Exception as e:
            raise RuntimeError(f"Failed to parse VHDL file '{path}': {e}")

    @staticmethod
    def parse_content(content: str) -> VhdlEntity:
        """Parse VHDL content and return entity information."""
        # Remove comments and normalize whitespace
        cleaned = VhdlParser._clean_content(content)
        
        # Extract entity name
        entity_name = VhdlParser._extract_entity_name(cleaned)
        
        # Extract generics
        generics = VhdlParser._extract_generics(cleaned)
        
        # Extract ports
        ports = VhdlParser._extract_ports(cleaned)
        
        return VhdlEntity(
            name=entity_name,
            generics=generics,
            ports=ports
        )

    @staticmethod
    def _clean_content(content: str) -> str:
        """Remove comments and normalize whitespace."""
        # Remove single-line comments
        comment_re = re.compile(r'--.*$', re.MULTILINE)
        lines = []
        
        for line in content.splitlines():
            cleaned_line = comment_re.sub('', line)
            lines.append(cleaned_line)
        
        # Join lines and normalize whitespace
        joined = ' '.join(lines)
        normalized = re.sub(r'\s+', ' ', joined)
        return normalized.lower()

    @staticmethod
    def _extract_entity_name(content: str) -> str:
        """Extract entity name from cleaned content."""
        entity_re = re.compile(r'entity\s+(\w+)\s+is')
        match = entity_re.search(content)
        if match:
            return match.group(1)
        else:
            raise ValueError("Could not find entity name")

    @staticmethod
    def _extract_generics(content: str) -> List[VhdlGeneric]:
        """Extract generic parameters from cleaned content."""
        generics = []
        
        # Look for generic section
        generic_re = re.compile(r'generic\s*\((.*?)\)\s*;')
        match = generic_re.search(content)
        
        if match:
            generic_content = match.group(1)
            
            # Parse individual generics
            generic_item_re = re.compile(r'(\w+)\s*:\s*(\w+)(?:\s*:=\s*([^;,)]+))?')
            for item_match in generic_item_re.finditer(generic_content):
                default_val = None
                if item_match.group(3):
                    default_val = item_match.group(3).strip()
                
                generics.append(VhdlGeneric(
                    name=item_match.group(1),
                    generic_type=item_match.group(2),
                    default_value=default_val
                ))
        
        return generics

    @staticmethod
    def _extract_ports(content: str) -> List[VhdlPort]:
        """Extract port declarations from cleaned content."""
        ports = []
        
        # Find the start of the port section
        port_start_re = re.compile(r'port\s*\(', re.IGNORECASE)
        start_match = port_start_re.search(content)
        
        if start_match:
            start_pos = start_match.end() - 1  # Position of the opening '('
            
            # Find the matching closing parenthesis
            paren_count = 0
            end_pos = None
            
            for i, ch in enumerate(content[start_pos:], start_pos):
                if ch == '(':
                    paren_count += 1
                elif ch == ')':
                    paren_count -= 1
                    if paren_count == 0:
                        end_pos = i
                        break
            
            if end_pos:
                # Extract the content between the balanced parentheses
                port_content = content[start_pos + 1:end_pos]
                
                # Split by semicolons, but be careful with parentheses in ranges
                port_declarations = VhdlParser._split_port_declarations(port_content)
                
                for decl in port_declarations:
                    port = VhdlParser._parse_port_declaration(decl)
                    if port:
                        ports.append(port)
        
        return ports

    @staticmethod
    def _split_port_declarations(content: str) -> List[str]:
        """Split port declarations by semicolons, respecting parentheses."""
        declarations = []
        current = ""
        paren_depth = 0
        
        for ch in content:
            if ch == '(':
                paren_depth += 1
                current += ch
            elif ch == ')':
                paren_depth -= 1
                current += ch
            elif ch == ';' and paren_depth == 0:
                if current.strip():
                    declarations.append(current.strip())
                    current = ""
            else:
                current += ch
        
        # Handle the last declaration if it doesn't end with semicolon
        if current.strip():
            declarations.append(current.strip())
        
        return declarations

    @staticmethod
    def _parse_port_declaration(decl: str) -> Optional[VhdlPort]:
        """Parse a single port declaration."""
        # Clean up the declaration
        cleaned = decl.strip().replace('\n', ' ').replace('\r', '')
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # More flexible regex that handles ranges better
        port_re = re.compile(
            r'(\w+)\s*:\s*(in|out|inout)\s+(\w+(?:_\w+)*)(?:\s*(\([^)]*\)))?',
            re.IGNORECASE
        )
        
        match = port_re.search(cleaned)
        if match:
            range_val = match.group(4) if match.group(4) else None
            
            return VhdlPort(
                name=match.group(1).lower(),
                direction=match.group(2).lower(),
                signal_type=match.group(3).lower(),
                range=range_val
            )
        
        return None
