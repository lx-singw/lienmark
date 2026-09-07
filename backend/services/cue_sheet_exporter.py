"""
cue_sheet_exporter.py

ASCAP/BMI/SESAC Music Cue Sheet Exporter.
Sprint 6.3: Studio Deliverables.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import csv
import io
from typing import Any, Dict, List, Optional
from backend.api.routes.underwriting_schemas import (
    CueComposer,
    CuePublisher,
    CueSheetEntry,
    CueSheetResponse,
    CueUsageType,
)


class CueSheetExporter:
    """Extracts and formats musical claims into industry-standard cue sheets."""

    @staticmethod
    def _parse_composers(metadata: Dict[str, Any]) -> List[CueComposer]:
        """Extracts composer list with normalized splits summing to 100%."""
        raw_comp = metadata.get("composer") or metadata.get("composers") or "Undisclosed Composer"
        pro = metadata.get("composer_pro") or "ASCAP"
        return [CueComposer(name=str(raw_comp), pro=str(pro), split_percentage=100.0)]

    @staticmethod
    def _parse_publishers(metadata: Dict[str, Any]) -> List[CuePublisher]:
        """Extracts publisher list with normalized splits summing to 100%."""
        raw_pub = metadata.get("publisher") or metadata.get("publishers") or "Undisclosed Publisher"
        pro = metadata.get("publisher_pro") or "BMI"
        return [CuePublisher(name=str(raw_pub), pro=str(pro), split_percentage=100.0)]

    @classmethod
    def _claim_to_cue(cls, claim: Dict[str, Any], idx: int) -> CueSheetEntry:
        """Converts an individual atomic music claim dictionary to a CueSheetEntry."""
        meta = claim.get("metadata") or {}
        time_in = meta.get("timecode_in") or meta.get("timecode") or "00:00:00:00"
        time_out = meta.get("timecode_out") or "00:01:30:00"
        duration = int(meta.get("duration_seconds") or 90)
        usage_str = str(meta.get("usage") or "BI").upper()
        usage = CueUsageType[usage_str] if usage_str in CueUsageType.__members__ else CueUsageType.BI

        return CueSheetEntry(
            cue_number=idx,
            title=claim.get("title") or claim.get("name") or f"Cue #{idx}",
            usage=usage,
            timecode_in=time_in,
            timecode_out=time_out,
            duration_seconds=duration,
            scene=meta.get("scene"),
            composers=cls._parse_composers(meta),
            publishers=cls._parse_publishers(meta),
            record_label=meta.get("record_label"),
            pro_work_id=meta.get("pro_work_id") or meta.get("ascap_work_id"),
            status=claim.get("status") or "CLEARED",
            lineage_key=claim.get("stable_lineage_key") or claim.get("lineage_key") or f"cue_{idx}",
        )

    @classmethod
    def generate_cue_sheet(
        cls,
        production_id: str,
        production_title: str,
        claims: List[Dict[str, Any]],
    ) -> CueSheetResponse:
        """Generates a structured CueSheetResponse from rights claims."""
        music_claims = [
            c for c in claims
            if str(c.get("right_category") or c.get("category") or "").lower() == "music"
        ]

        cues: List[CueSheetEntry] = []
        total_duration = 0
        for i, c in enumerate(music_claims, start=1):
            entry = cls._claim_to_cue(c, i)
            cues.append(entry)
            total_duration += entry.duration_seconds

        return CueSheetResponse(
            production_id=production_id,
            production_title=production_title,
            total_cues=len(cues),
            total_duration_seconds=total_duration,
            cues=cues,
        )

    @staticmethod
    def _format_cue_row(c: CueSheetEntry) -> List[Any]:
        """Formats a single CueSheetEntry into CSV row fields."""
        comp = "; ".join(f"{cp.name} ({cp.pro} {cp.split_percentage:.1f}%)" for cp in c.composers)
        pub = "; ".join(f"{pb.name} ({pb.pro} {pb.split_percentage:.1f}%)" for pb in c.publishers)
        return [
            c.cue_number, c.title, c.usage.value, c.timecode_in, c.timecode_out,
            c.duration_seconds, c.scene or "", comp, pub, c.pro_work_id or "",
            c.record_label or "", c.status, c.lineage_key,
        ]

    @classmethod
    def export_csv(cls, cue_sheet: CueSheetResponse) -> str:
        """Serializes CueSheetResponse to RFC 4180 standard CSV text."""
        buf = io.StringIO()
        writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)
        writer.writerow([
            "CUE_NUMBER", "TITLE_OF_WORK", "USAGE", "TIMECODE_IN", "TIMECODE_OUT",
            "DURATION_SECONDS", "SCENE", "COMPOSERS", "PUBLISHERS", "PRO_WORK_ID",
            "RECORD_LABEL", "STATUS", "LINEAGE_KEY",
        ])
        for c in cue_sheet.cues:
            writer.writerow(cls._format_cue_row(c))
        return buf.getvalue()
