"""LaTeX conversion service for equation images."""
import base64
import subprocess
import shutil
from typing import Dict, Any, Optional
from pathlib import Path
import httpx
import logging

logger = logging.getLogger(__name__)


class LatexifyService:
    """Convert equation images to LaTeX."""

    def __init__(self, gemini_api_key: str = "", models_dir: Optional[Path] = None):
        self.gemini_api_key = gemini_api_key
        self.models_dir = models_dir
        self._pix2tex_available: Optional[bool] = None

    def is_pix2tex_available(self) -> bool:
        """Check if pix2tex is installed and available."""
        if self._pix2tex_available is None:
            self._pix2tex_available = shutil.which("pix2tex") is not None
            if not self._pix2tex_available:
                # Also try as Python module
                try:
                    import pix2tex
                    self._pix2tex_available = True
                except ImportError:
                    pass
        return self._pix2tex_available

    async def convert_to_latex(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Convert an equation image to LaTeX.

        Tries pix2tex first, then falls back to Gemini API.
        """
        # Try pix2tex first
        if self.is_pix2tex_available():
            try:
                result = await self._convert_with_pix2tex(image_bytes)
                if result.get("success"):
                    return result
            except Exception as e:
                logger.warning(f"pix2tex failed: {e}")

        # Fall back to Gemini
        if self.gemini_api_key:
            try:
                return await self._convert_with_gemini(image_bytes)
            except Exception as e:
                logger.error(f"Gemini API failed: {e}")
                return {
                    "success": False,
                    "error": f"Gemini API error: {str(e)}",
                    "latex": None
                }

        # No methods available
        return {
            "success": False,
            "error": self._get_setup_instructions(),
            "latex": None
        }

    async def _convert_with_pix2tex(self, image_bytes: bytes) -> Dict[str, Any]:
        """Convert using local pix2tex model."""
        import tempfile
        import os

        # Save image to temp file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(image_bytes)
            temp_path = f.name

        try:
            # Try using pix2tex as CLI
            result = subprocess.run(
                ["pix2tex", temp_path],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                latex = result.stdout.strip()
                return {
                    "success": True,
                    "latex": latex,
                    "method": "pix2tex",
                    "confidence": 0.9  # pix2tex doesn't provide confidence
                }
            else:
                raise RuntimeError(f"pix2tex error: {result.stderr}")

        finally:
            os.unlink(temp_path)

    async def _convert_with_gemini(self, image_bytes: bytes) -> Dict[str, Any]:
        """Convert using Gemini API."""
        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        prompt = """Convert this mathematical equation or formula image to LaTeX.
Return ONLY the LaTeX code, without any explanation or surrounding text.
Do not include dollar signs ($) around the expression.
If there are multiple equations, separate them with newlines."""

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": base64_image
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 1024
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_api_key}",
                json=payload,
                timeout=30.0
            )

            if response.status_code != 200:
                raise RuntimeError(f"Gemini API returned {response.status_code}: {response.text}")

            data = response.json()

            # Extract text from response
            try:
                latex = data["candidates"][0]["content"]["parts"][0]["text"].strip()

                # Clean up common issues
                latex = latex.strip('`')
                if latex.startswith("latex"):
                    latex = latex[5:].strip()

                return {
                    "success": True,
                    "latex": latex,
                    "method": "gemini",
                    "confidence": 0.85
                }
            except (KeyError, IndexError) as e:
                raise RuntimeError(f"Unexpected Gemini response format: {e}")

    def _get_setup_instructions(self) -> str:
        """Return instructions for setting up LaTeX conversion."""
        return """No LaTeX conversion method available.

To enable LaTeX conversion, do one of the following:

Option 1: Install pix2tex (local, free, works offline)
  pip install pix2tex
  # Or from source: https://github.com/lukas-blecher/LaTeX-OCR

Option 2: Configure Gemini API (cloud-based)
  1. Get an API key from https://makersuite.google.com/app/apikey
  2. Add your key to Scriptor Local settings
"""

    def get_status(self) -> Dict[str, Any]:
        """Get current LaTeXify service status."""
        return {
            "pix2tex_available": self.is_pix2tex_available(),
            "gemini_configured": bool(self.gemini_api_key),
            "ready": self.is_pix2tex_available() or bool(self.gemini_api_key)
        }
