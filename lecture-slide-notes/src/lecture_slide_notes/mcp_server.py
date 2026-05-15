from __future__ import annotations

from pathlib import Path

from .doctor import run_checks
from .models import ProcessingOptions
from .pipeline import process_url, process_video


def create_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception as exc:
        raise RuntimeError("Install the mcp extra to run the MCP server: uv sync --extra mcp") from exc

    mcp = FastMCP("lecture-slide-notes")

    @mcp.tool()
    def doctor() -> dict:
        """Check local dependencies needed for lecture slide processing."""
        return {check.name: {"ok": check.ok, "detail": check.detail} for check in run_checks()}

    @mcp.tool()
    def process_local_video(video_path: str, output_dir: str, title: str | None = None, no_ocr: bool = False) -> dict:
        """Extract slide PNGs, Markdown, and PDF from a local video."""
        options = ProcessingOptions(no_ocr=no_ocr)
        result = process_video(Path(video_path), Path(output_dir), options=options, title=title)
        return {
            "title": result.title,
            "output_dir": str(result.output_dir),
            "slide_count": len(result.slides),
            "markdown": str(result.markdown_path),
            "pdf": str(result.pdf_path) if result.pdf_path else None,
            "manifest": str(result.manifest_path),
        }

    @mcp.tool()
    def process_remote_url(
        url: str,
        output_root: str,
        referer: str | None = None,
        title: str | None = None,
        cookies_from_browser: str | None = None,
        no_ocr: bool = False,
    ) -> dict:
        """Download a Vimeo, YouTube, or course URL and create slide notes."""
        options = ProcessingOptions(no_ocr=no_ocr)
        result = process_url(
            url,
            Path(output_root),
            referer=referer,
            title=title,
            cookies_from_browser=cookies_from_browser,
            options=options,
        )
        return {
            "title": result.title,
            "output_dir": str(result.output_dir),
            "slide_count": len(result.slides),
            "markdown": str(result.markdown_path),
            "pdf": str(result.pdf_path) if result.pdf_path else None,
            "manifest": str(result.manifest_path),
        }

    return mcp


def main() -> None:
    create_server().run()


if __name__ == "__main__":
    main()
