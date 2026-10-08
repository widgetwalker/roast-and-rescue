"""Output formatting for GitHub Roast and Rescue.

Uses Bento Style design principles - a grid-based dashboard layout that
organizes content into clear, partitionable sections. Inspired by:
- Clean partitioning of roast/rescue sections
- Readable typography and spacing
- Terminal-friendly formatting

Design: Bento Style adapted for terminal/CLI output
"""

import sys
from typing import Dict, Any


# Bento Style layout constants
LAYOUT = {
    "width": 80,  # Terminal width
    "padding": 1,
    "section_gap": 1,
    "header_height": 3,
    "footer_height": 1,
}


def bento_layout(sections: Dict[str, str], width: int = 80) -> str:
    """Format output using Bento Style grid layout.

    Bento Style organizes content into a grid of cells, like a bento box.
    Each section gets its own cell with clear partitioning.

    Args:
        sections: Dictionary of section_name -> content_string
        width: Maximum width for each cell

    Returns:
        Formatted string ready for terminal output
    """
    lines = []

    # Header
    lines.append("=" * width)
    lines.append("  GITHUB ROAST & RESCUE")
    lines.append("  Honest feedback with actionable improvement advice")
    lines.append("=" * width)
    lines.append("")

    # Layout sections in a grid
    # Bento Style: typically 2-column or asymmetric grid
    # Here we stack vertically with clear separators
    section_names = list(sections.keys())

    for i, (name, content) in enumerate(sections.items()):
        # Section header
        lines.append("-" * width)
        # Pad section name
        padded_name = f"  {name.upper()}  "
        lines.append(padded_name.center(width, "─"))

        # Section content - wrap at width-4 for padding
        content_lines = content.split("\n")
        for line in content_lines:
            # Wrap long lines
            if len(line) > width - 4:
                words = line.split(" ")
                current_line = ""
                for word in words:
                    if len(current_line + word) <= width - 4:
                        current_line += word + " "
                    else:
                        lines.append(f"  {current_line.strip()}")
                        current_line = word + " "
                if current_line.strip():
                    lines.append(f"  {current_line.strip()}")
            else:
                lines.append(f"  {line}")

        # Add a small gap between sections (except last)
        if i < len(section_names) - 1:
            lines.append("")

    # Footer
    lines.append("=" * width)
    lines.append("  Roast for entertainment only - focus on the rescue for real improvement")
    lines.append("=" * width)
    lines.append("")

    return "\n".join(lines)


def format_recruiter_glance(glance_text: str, width: int = 80) -> str:
    """Format the recruiter glance section in Bento Style.

    Args:
        glance_text: The recruiter glance content
        width: Terminal width

    Returns:
        Formatted section string
    """
    lines = []
    lines.append("┌" + "─" * (width - 2) + "┐")
    lines.append(f"  RECRUITER GLANCE (30 seconds)")
    lines.append("├" + "─" * (width - 2) + "┤")

    # Format content - split into lines and ensure they fit
    for line in glance_text.split("\n"):
        if len(line) > width - 4:
            # Word wrap
            words = line.split(" ")
            wrapped = []
            current = ""
            for word in words:
                if len(current) + len(word) + 1 <= width - 4:
                    current += word + " "
                else:
                    wrapped.append(current.strip())
                    current = word + " "
            if current:
                wrapped.append(current.strip())

            for w in wrapped:
                lines.append(f"  {w}")
        else:
            lines.append(f"  {line}")

    lines.append("└" + "─" * (width - 2) + "┘")
    lines.append("")

    return "\n".join(lines)


def format_roast(roast_text: str, width: int = 80) -> str:
    """Format the roast section in Bento Style.

    Args:
        roast_text: The roast content
        width: Terminal width

    Returns:
        Formatted section string
    """
    lines = []
    lines.append("┌" + "─" * (width - 2) + "┐")
    lines.append(f"  THE ROAST  (for entertainment)")
    lines.append("├" + "─" * (width - 2) + "┤")

    for line in roast_text.split("\n"):
        if len(line) > width - 4:
            words = line.split(" ")
            wrapped = []
            current = ""
            for word in words:
                if len(current) + len(word) + 1 <= width - 4:
                    current += word + " "
                else:
                    wrapped.append(current.strip())
                    current = word + " "
            if current:
                wrapped.append(current.strip())

            for w in wrapped:
                lines.append(f"  {w}")
        else:
            lines.append(f"  {line}")

    lines.append("└" + "─" * (width - 2) + "┘")
    lines.append("")

    return "\n".join(lines)


def format_rescue(rescue_text: str, width: int = 80) -> str:
    """Format the rescue/advice section in Bento Style.

    Args:
        rescue_text: The rescue/advice content
        width: Terminal width

    Returns:
        Formatted section string
    """
    lines = []
    lines.append("┌" + "─" * (width - 2) + "┐")
    lines.append(f"  THE RESCUE  (actionable improvement)")
    lines.append("├" + "─" * (width - 2) + "┤")

    for line in rescue_text.split("\n"):
        if len(line) > width - 4:
            words = line.split(" ")
            wrapped = []
            current = ""
            for word in words:
                if len(current) + len(word) + 1 <= width - 4:
                    current += word + " "
                else:
                    wrapped.append(current.strip())
                    current = word + " "
            if current:
                wrapped.append(current.strip())

            for w in wrapped:
                lines.append(f"  {w}")
        else:
            lines.append(f"  {line}")

    lines.append("└" + "─" * (width - 2) + "┘")
    lines.append("")

    return "\n".join(lines)


def format_output(analysis: Dict[str, Any]) -> None:
    """Format and display the full analysis output using Bento Style layout.

    Takes the analysis dictionary from analyzer.py and presents it in a
    nicely formatted Bento Style grid layout.

    Args:
        analysis: Dictionary with recruiter_glance, roast, rescue, username
    """
    username = analysis.get("username", "Unknown")

    # Build sections for Bento layout
    sections = {
        "recruiter_glance": analysis.get("recruiter_glance", ""),
        "roast": analysis.get("roast", ""),
        "rescue": analysis.get("rescue", ""),
    }

    # Print the full Bento Style layout
    output = bento_layout(sections, width=80)

    # Print with username header
    print(f"\n🔍 Roasting GitHub profile: @{username}")
    print("=" * 80)
    print(output)


def main():
    """CLI entry point for testing output formatting."""
    sample_analysis = {
        "username": "testuser",
        "recruiter_glance": "Test user is a developer working primarily with Python, JavaScript",
        "roast": "Test roast line 1. Test roast line 2. Test roast line 3.",
        "rescue": "Quick win: Add a bio. Medium: Add READMEs. Long-term: Contribute to OSS.",
    }

    format_output(sample_analysis)


if __name__ == "__main__":
    main()