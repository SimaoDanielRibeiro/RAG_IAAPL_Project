/**
 * Strip markdown formatting artefacts that the small chat model occasionally
 * leaks despite the "plain text" rule in the prompt.
 *
 * Removes:
 *   - `**bold**` / `***bold italic***` / `*****` clusters of two-plus asterisks
 *   - `__bold__` clusters of two-plus underscores
 *   - Leading `#`, `##`, `###` headings (the rest of the line is kept)
 *   - Standalone horizontal rules: `---`, `----` on their own line
 *
 * Single `*` (italic / bullet point) and single `_` are intentionally preserved
 * so we don't break list items like "* first" or filenames containing `_`.
 */
export function stripMarkdown(text: string): string {
  return text
    .replace(/\*{2,}/g, "")
    .replace(/_{2,}/g, "")
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/^-{3,}\s*$/gm, "");
}
