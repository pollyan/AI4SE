# Artifact PDF Export Design

## Goal

Add a PDF option to the Artifact export menu so users can download the current artifact in Markdown, Word-compatible, or PDF format.

## Scope

- Frontend only.
- No new dependency.
- Generate a minimal valid text PDF from the current artifact content.
- Preserve the current Markdown and Word-compatible export behavior.

## Behavior

The export menu adds a `PDF` option. Clicking it downloads `<workflow>_artifact.pdf` with MIME type `application/pdf`. The generated content starts with a valid `%PDF-1.4` header and stores artifact text lines as UTF-16BE hex strings in a single-page PDF content stream.

This slice is a plain text PDF export. Rich markdown layout, tables, Mermaid rendering, pagination beyond the first page, and DOCX-grade formatting remain future work.

## Testing

Extend `ArtifactPane.test.tsx` to click `PDF` and assert the downloaded filename, MIME type, `%PDF-1.4` header, and presence of UTF-16BE encoded artifact text.
