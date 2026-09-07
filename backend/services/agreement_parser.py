"""
backend/services/agreement_parser.py

Dual-mode legal agreement parser: Gemini Multimodal PDF extraction and offline regex heuristics.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Union

from backend.core.schema_repair import repair_json_output
from backend.services.document_matcher_types import (
    AgreementParties,
    AgreementType,
    ExtractedAgreementMetadata,
)

logger = logging.getLogger("lienmark.services.agreement_parser")


def compute_file_hash(content: Union[str, bytes]) -> str:
    """Computes SHA-256 hex digest for document bytes or text."""
    data = content.encode("utf-8") if isinstance(content, str) else content
    return hashlib.sha256(data).hexdigest()


class AgreementParser:
    """
    Extracts structured agreement metadata from legal agreements.
    Supports live Gemini multimodal extraction and deterministic offline regex heuristics.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        use_fallback: bool = False,
        model_name: str = "gemini-2.5-flash",
    ) -> None:
        self.model_name = model_name
        raw_key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
        has_key = bool(
            raw_key and not any(raw_key.lower().startswith(p) for p in ("mock", "sandbox", "test"))
        )
        self.is_offline = use_fallback or not has_key
        self.client = None
        if not self.is_offline:
            try:
                from google import genai
                self.client = genai.Client(api_key=raw_key)
            except Exception as exc:
                logger.warning(f"google.genai init failed ({exc}); falling back to offline.")
                self.is_offline = True

    def parse_agreement(
        self,
        content: Union[str, bytes],
        file_path: str = "",
        file_hash: str = "",
    ) -> ExtractedAgreementMetadata:
        """Parses agreement document using Gemini when available or deterministic heuristic."""
        computed_hash = file_hash or compute_file_hash(content)
        if self.is_offline or self.client is None:
            text = content if isinstance(content, str) else content.decode("utf-8", errors="ignore")
            return self._extract_heuristic(text, computed_hash, file_path)
        return self._extract_multimodal(content, computed_hash, file_path)

    def parse_agreement_file(self, file_path: str) -> ExtractedAgreementMetadata:
        """Reads file from disk and parses agreement metadata."""
        with open(file_path, "rb") as f:
            content = f.read()
        return self.parse_agreement(content, file_path=file_path)

    def _extract_heuristic(
        self, text: str, file_hash: str, file_path: str = ""
    ) -> ExtractedAgreementMetadata:
        """Deterministic regex-based heuristic extractor for offline test/CI."""
        parties = self._extract_parties(text)
        asset_title = self._extract_asset_title(text, file_path)
        agreement_type = self._detect_agreement_type(text)
        date_val = self._extract_execution_date(text)
        territories = self._extract_territory(text)
        media = self._extract_media(text)
        term = self._extract_term(text)

        return ExtractedAgreementMetadata(
            file_hash=file_hash,
            parties=parties,
            asset_title=asset_title,
            agreement_type=agreement_type,
            execution_date=date_val,
            grant_territory=territories,
            grant_media=media,
            grant_term=term,
            extraction_confidence=0.92,
            extraction_source="heuristic_regex",
            raw_snippet=text[:400].strip(),
        )

    @staticmethod
    def _detect_agreement_type(text: str) -> str:
        """Infers agreement classification from keywords and title headers."""
        upper = text.upper()
        if "SYNCHRONIZATION" in upper or "SYNC LICENSE" in upper:
            return AgreementType.SYNC_LICENSE.value
        if "MASTER USE" in upper or "SOUND RECORDING LICENSE" in upper:
            return AgreementType.MASTER_USE.value
        if "TRADEMARK" in upper or "BRAND RELEASE" in upper or "PRODUCT PLACEMENT" in upper:
            return AgreementType.TRADEMARK_RELEASE.value
        if "VARA" in upper or "VISUAL ARTISTS RIGHTS" in upper or "ARTIST RELEASE" in upper:
            return AgreementType.VARA_WAIVER.value
        if "LOCATION" in upper:
            return AgreementType.LOCATION_RELEASE.value
        if "TALENT" in upper or "DEPICTION" in upper or "LIFE RIGHTS" in upper:
            return AgreementType.TALENT_RELEASE.value
        return AgreementType.CUSTOM_AGREEMENT.value

    @staticmethod
    def _extract_parties(text: str) -> AgreementParties:
        """Extracts licensor and licensee names from agreement header clauses."""
        btw = re.search(
            r"between\s+([A-Za-z0-9\s.,&'-]+?)(?:\s*\((?:the\s+)?Licensor\))?\s+and\s+([A-Za-z0-9\s.,&'-]+?)(?:\s*\((?:the\s+)?Licensee\))?[\n\r.,]",
            text,
            re.IGNORECASE,
        )
        if btw:
            lic = re.sub(r"\s*\((?:the\s+)?Licensor\)", "", btw.group(1), flags=re.IGNORECASE).strip().rstrip(",")
            lee = re.sub(r"\s*\((?:the\s+)?Licensee\)", "", btw.group(2), flags=re.IGNORECASE).strip().rstrip(",")
            return AgreementParties(licensor=lic, licensee=lee)

        lic_m = re.search(r"(?:Licensor|Grantor|Artist|Owner)\s*[:\-]\s*([^\r\n]+)", text, re.IGNORECASE)
        lee_m = re.search(r"(?:Licensee|Grantee|Producer)\s*[:\-]\s*([^\r\n]+)", text, re.IGNORECASE)
        lic = lic_m.group(1).strip() if lic_m else "Licensor Party"
        lee = lee_m.group(1).strip() if lee_m else "Production Company"
        return AgreementParties(licensor=lic, licensee=lee)

    @staticmethod
    def _extract_asset_title(text: str, file_path: str = "") -> str:
        """Extracts asset title, cue name, or composition title from text or filename."""
        match = re.search(
            r"(?:Asset|Work|Cue|Composition|Master|Trademark|Song|Track|Title)\s*(?:Title|Name)?\s*[:\-]\s*[\"']?([^\"'\r\n]+)[\"']?",
            text,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()
        quoted = re.findall(r"[\"']([^\"'\r\n]{3,60})[\"']", text)
        if quoted:
            return quoted[0].strip()
        if file_path:
            base = os.path.basename(file_path)
            clean = re.sub(r"\.(pdf|docx?|txt)$", "", base, flags=re.IGNORECASE)
            return clean.replace("_", " ").title()
        return "Unknown Asset"

    @staticmethod
    def _extract_execution_date(text: str) -> Optional[str]:
        """Detects date of execution or effective date."""
        iso_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
        if iso_match:
            return iso_match.group(1)
        date_match = re.search(
            r"(?:Dated?(?:\s+as\s+of)?|Execution\s+Date|Effective\s+Date)\s*[:\-]?\s*([A-Za-z0-9\s,/-]+)",
            text,
            re.IGNORECASE,
        )
        if date_match:
            return date_match.group(1).strip()
        return None

    @staticmethod
    def _extract_territory(text: str) -> List[str]:
        """Detects licensed territories from grant clauses."""
        upper = text.upper()
        territories: List[str] = []
        if any(w in upper for w in ("WORLDWIDE", "THE WORLD", "UNIVERSE")):
            territories.append("Worldwide")
        if any(w in upper for w in ("UNITED STATES", "U.S.A.", "NORTH AMERICA")):
            territories.append("United States")
        return territories or ["Worldwide"]

    @staticmethod
    def _extract_media(text: str) -> List[str]:
        """Detects licensed media channels."""
        upper = text.upper()
        media: List[str] = []
        if "ALL MEDIA" in upper or "ANY AND ALL MEDIA" in upper:
            media.append("All Media")
        if "THEATRICAL" in upper:
            media.append("Theatrical")
        if "STREAMING" in upper or "SVOD" in upper:
            media.append("SVOD")
        return media or ["All Media"]

    @staticmethod
    def _extract_term(text: str) -> Optional[str]:
        """Detects license duration / term."""
        upper = text.upper()
        if "PERPETUAL" in upper or "PERPETUITY" in upper:
            return "Perpetual"
        term_match = re.search(r"Term\s*[:\-]\s*([^\r\n;]+)", text, re.IGNORECASE)
        return term_match.group(1).strip() if term_match else "Perpetual"

    def _extract_multimodal(
        self, content: Union[str, bytes], file_hash: str, file_path: str = ""
    ) -> ExtractedAgreementMetadata:
        """Invokes Gemini Multimodal API with fallback to heuristic extraction."""
        try:
            from google.genai import types
            prompt = (
                "Extract structured legal agreement metadata as valid JSON with keys: "
                "licensor, licensee, asset_title, agreement_type, execution_date, "
                "grant_territory (list), grant_media (list), grant_term."
            )
            raw_bytes = content.encode("utf-8") if isinstance(content, str) else content
            part = types.Part.from_bytes(data=raw_bytes, mime_type="application/pdf")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt, part],
            )
            parsed = repair_json_output(response.text or "{}")
            return ExtractedAgreementMetadata(
                file_hash=file_hash,
                parties=AgreementParties(
                    licensor=parsed.get("licensor", "Licensor"),
                    licensee=parsed.get("licensee", "Licensee"),
                ),
                asset_title=parsed.get("asset_title", "Unknown Asset"),
                agreement_type=parsed.get("agreement_type", AgreementType.CUSTOM_AGREEMENT.value),
                execution_date=parsed.get("execution_date"),
                grant_territory=parsed.get("grant_territory", ["Worldwide"]),
                grant_media=parsed.get("grant_media", ["All Media"]),
                grant_term=parsed.get("grant_term", "Perpetual"),
                extraction_confidence=0.98,
                extraction_source="gemini_multimodal",
            )
        except Exception as exc:
            logger.warning(f"Multimodal parse failed ({exc}); falling back to heuristic.")
            text = content if isinstance(content, str) else content.decode("utf-8", errors="ignore")
            return self._extract_heuristic(text, file_hash, file_path)
