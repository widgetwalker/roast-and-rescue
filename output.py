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


def bento_layout(sections: Dict[str, str], width: int = 76) -> str:
    """Format output using a clean, readable Neo-Brutalist Bento terminal frame.

    Args:
        sections: Dictionary of section_name -> content_string
        width: Maximum width for box borders

    Returns:
        Formatted string ready for terminal output
    """
    lines = []
    inner_w = width - 4

    titles = {
        "recruiter_glance": ("⏱️  RECRUITER SCAN", "─"),
        "roast": ("🔥  THE ROAST", "─"),
        "rescue": ("🛟  THE RESCUE PLAN", "─"),
    }

    for name, content in sections.items():
        title_text, fill_char = titles.get(name, (f"📌  {name.upper()}", "─"))
        
        # Brutalist block header
        header_line = f"┌── {title_text} "
        if len(header_line) < width:
            header_line += fill_char * (width - len(header_line) - 1) + "┐"
        else:
            header_line = header_line[:width-1] + "┐"
        
        lines.append("")
        lines.append(header_line)

        # Content lines
        for raw_line in content.split("\n"):
            if not raw_line.strip():
                lines.append(f"│  ")
                continue

            words = raw_line.split(" ")
            curr = ""
            for w in words:
                if len(curr) + len(w) + 1 <= inner_w:
                    curr += (" " if curr else "") + w
                else:
                    lines.append(f"│  {curr.ljust(inner_w)} │")
                    curr = w
            if curr:
                lines.append(f"│  {curr.ljust(inner_w)} │")

        lines.append("└──" + "─" * (width - 4) + "┘")

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
    width = 76
    output = bento_layout(sections, width=width)

    # Brutalist Title Card
    inner_title_len = width - 36
    clean_user = username.upper()[:inner_title_len].ljust(inner_title_len)
    title_box = [
        f"┌{'─' * (width - 2)}┐",
        f"│  🔥 GITHUB ROAST & RESCUE  ::  @{clean_user} │",
        f"└{'─' * (width - 2)}┘",
    ]

    print("\n" + "\n".join(title_box))
    print(output)
    print(f"\n⚡ Built with Claude + OpenCode + Antigravity\n")


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