export function brutalistLayout(sections: Record<string, string>, width: number = 80): string {
  const center = (str: string, len: number, padChar: string = "█") => {
    const padLen = Math.max(0, len - str.length);
    const left = Math.floor(padLen / 2);
    const right = padLen - left;
    return padChar.repeat(left) + str + padChar.repeat(right);
  };
  const lines: string[] = [
    "█".repeat(width),
    center("  GITHUB ROAST & RESCUE  ", width, "█"),
    center("  Honest feedback with actionable improvement advice  ", width, "█"),
    "█".repeat(width),
    "",
  ];
  for (const [name, content] of Object.entries(sections)) {
    lines.push("▀".repeat(width));
    lines.push(center(`  ${name.toUpperCase()}  `, width, "█"));
    lines.push("▄".repeat(width));
    for (const line of (content || "").split("\n")) {
      lines.push(` █  ${line}`);
    }
    lines.push("");
  }
  lines.push("≡".repeat(width));
  return lines.join("\n");
}
