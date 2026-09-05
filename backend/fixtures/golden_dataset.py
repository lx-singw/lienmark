"""
Lienmark Golden Dataset & Fixtures
Represents the fictional film production 'Shadows Over Broadway' across Version 7 and Version 8.
Contains 12 canonical rights-bearing uses:
- 10 Unchanged uses (carried forward fail-closed)
- 1 Creative drift use (Scene 42: poster brought into focal dialogue)
- 1 External evidence drift use (Scene 18: jazz cue copyright ownership transfer)
- Mathematical Conservation Law: 12 = 10 + 1 + 1 (10 carried forward + 1 re-attested + 1 unresolved exception)
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from typing import Any, Dict, List, Tuple
from backend.domain.models import (
    CreativeUse,
    CounselDecision,
    DecisionStatus,
    EvidenceStance,
    ProductionVersion,
    PublicEvidenceSnapshot,
)
from backend.core.invalidation_engine import InvalidationEngine
from backend.core.semantic_delta import DeltaAnalysisResult


def get_v7_version() -> ProductionVersion:
    return ProductionVersion(
        version_id="v7",
        project_id="proj_blockbuster_cinema",
        label="Shadows Over Broadway - Locked Script v7",
        content_hash="a1b2c3d4e5f60718293a4b5c6d7e8f90",
        parent_version_id=None,
        source_type="screenplay",
    )


def get_v8_version() -> ProductionVersion:
    return ProductionVersion(
        version_id="v8",
        project_id="proj_blockbuster_cinema",
        label="Shadows Over Broadway - Production Revision v8",
        content_hash="f9e8d7c6b5a43210fedcba9876543210",
        parent_version_id="v7",
        source_type="screenplay",
    )


def get_golden_fixtures() -> Tuple[
    List[CreativeUse],
    List[CreativeUse],
    List[CounselDecision],
    Dict[str, PublicEvidenceSnapshot],
]:
    """
    Returns (v7_uses, v8_uses, v7_decisions, v8_evidence_snapshots)
    """

    # 10 Unchanged items (carried forward)
    unchanged_specs = [
        (
            "prop_vintage_telephone",
            "prop",
            "Scene 04 - Detective Office",
            "1950s Western Electric Rotary Phone prop on mahogany desk.",
            "Incidental background set dressing, 4s",
            "Office establishing shot, protagonist enters holding trench coat.",
        ),
        (
            "poster_paris_expo_1937",
            "artwork",
            "Scene 08 - Hotel Corridor",
            "Framed vintage reproduction poster of 1937 Paris Exposition.",
            "Background hallway blur, 3s",
            "Camera tracks alongside characters walking down dimly lit corridor.",
        ),
        (
            "car_ford_sedan_1949",
            "prop",
            "Scene 12 - Street Exterior",
            "1949 Ford Custom Tudor Sedan parked curbside under streetlamp.",
            "Exterior street background, 6s",
            "Rain-slicked pavement reflecting neon signs as car sits parked.",
        ),
        (
            "trademark_acme_coffee",
            "trademark",
            "Scene 15 - Diner Booth",
            "Fictional Acme Coffee enamel sign painted on wall above booth.",
            "Set dressing background, 5s",
            "Two detectives conversing over diner counter.",
        ),
        (
            "artwork_abstract_expressionist",
            "artwork",
            "Scene 21 - Penthouse Loft",
            "Abstract expressionist oil canvas hanging behind executive desk.",
            "Medium shot background, 8s",
            "Antagonist signs ledger document while standing in front of painting.",
        ),
        (
            "likeness_mayor_cameo",
            "likeness",
            "Scene 26 - Courtroom Gallery",
            "Background courtroom gallery extra resembling former city mayor.",
            "Crowd scene background, 2s",
            "Gavel bangs as crowd murmurs in gallery benches.",
        ),
        (
            "architecture_tribunal_facade",
            "location",
            "Scene 30 - Civic Center",
            "Exterior historic facade of county courthouse.",
            "Establishing wide exterior, 3s",
            "Daylight establishing shot of courthouse stone steps.",
        ),
        (
            "text_headline_gazette",
            "text",
            "Scene 34 - Newsstand",
            "Prop newspaper headline reading 'MYSTERY WITNESS DISAPPEARS'.",
            "Inserts prop, 2s",
            "Protagonist glances at newspaper stack on corner stand.",
        ),
        (
            "wardrobe_fedora_brand",
            "trademark",
            "Scene 38 - Subway Platform",
            "Vintage Borsalino fedora hat worn by secondary character.",
            "Character wardrobe, 10s",
            "Subway train arrives as steam rises from subway grate.",
        ),
        (
            "music_incidental_radio_static",
            "music",
            "Scene 40 - Safehouse",
            "Foley ambient vintage radio broadcast static and low hum.",
            "Incidental background audio, 12s",
            "Safehouse interior late at night with rain tapping on glass.",
        ),
    ]

    v7_uses: List[CreativeUse] = []
    v8_uses: List[CreativeUse] = []
    v7_decisions: List[CounselDecision] = []
    v8_evidence: Dict[str, PublicEvidenceSnapshot] = {}

    for (
        key,
        asset_type,
        scene,
        description,
        prominence,
        context,
    ) in unchanged_specs:
        v7_hash = InvalidationEngine.compute_context_hash(context, prominence)
        v7_u = CreativeUse(
            use_id=f"use_v7_{key}",
            version_id="v7",
            scene_or_timecode=scene,
            asset_type=asset_type,
            description=description,
            duration_or_prominence=prominence,
            context=context,
            stable_lineage_key=key,
            context_hash=v7_hash,
        )
        v7_uses.append(v7_u)

        # In V8, identical
        v8_u = CreativeUse(
            use_id=f"use_v8_{key}",
            version_id="v8",
            scene_or_timecode=scene,
            asset_type=asset_type,
            description=description,
            duration_or_prominence=prominence,
            context=context,
            stable_lineage_key=key,
            context_hash=v7_hash,
        )
        v8_uses.append(v8_u)

        # V7 Counsel decision
        v7_decisions.append(
            CounselDecision(
                decision_id=f"dec_v7_{key}",
                use_id=v7_u.use_id,
                stable_lineage_key=key,
                applicable_version_id="v7",
                status=DecisionStatus.APPROVED,
                rationale="Approved as standard incidental background set dressing / de minimis clearance.",
                reviewer_display_name="Sarah Jenkins, Esq. (Clearance Counsel)",
            )
        )

        # Evidence snapshot supporting
        v8_evidence[key] = PublicEvidenceSnapshot(
            snapshot_id=f"ev_{key}",
            use_id=v8_u.use_id,
            stable_lineage_key=key,
            query=f"clearance search {key}",
            source_url=f"https://records.publicdomain.org/{key}",
            source_title=f"Public Registry Archive: {key}",
            excerpt="No active copyright or trademark conflicts registered.",
            stance=EvidenceStance.SUPPORTING,
        )

    # -------------------------------------------------------------
    # ITEM 11: Creative Drift (Scene 42 - Noir Detective Poster)
    # -------------------------------------------------------------
    poster_key = "poster_noir_detective_magazine"
    v7_poster_prominence = "Out-of-focus background blur, 2s"
    v7_poster_context = "Poster hangs on far wall behind detective desk, soft focus."
    v7_poster_hash = InvalidationEngine.compute_context_hash(
        v7_poster_context, v7_poster_prominence
    )

    v7_poster = CreativeUse(
        use_id="use_v7_poster_noir",
        version_id="v7",
        scene_or_timecode="Scene 42 - 00:44:12",
        asset_type="artwork",
        description="1946 Crime Detective Magazine cover poster 'Shadows Over Broadway'.",
        duration_or_prominence=v7_poster_prominence,
        context=v7_poster_context,
        stable_lineage_key=poster_key,
        context_hash=v7_poster_hash,
    )
    v7_uses.append(v7_poster)

    # V8 Creative Drift: Director zooms in, character reads headline aloud
    v8_poster_prominence = "Featured close-up focal shot with dialogue, 14s"
    v8_poster_context = (
        "Detective grabs poster off wall, examines the cover art closely and reads: "
        "'Look at this headline: Shadows Over Broadway! They knew everything back in 1946.'"
    )
    v8_poster_hash = InvalidationEngine.compute_context_hash(
        v8_poster_context, v8_poster_prominence
    )

    v8_poster = CreativeUse(
        use_id="use_v8_poster_noir",
        version_id="v8",
        scene_or_timecode="Scene 42 - 00:44:12",
        asset_type="artwork",
        description="1946 Crime Detective Magazine cover poster 'Shadows Over Broadway'.",
        duration_or_prominence=v8_poster_prominence,
        context=v8_poster_context,
        stable_lineage_key=poster_key,
        context_hash=v8_poster_hash,
    )
    v8_uses.append(v8_poster)

    v7_decisions.append(
        CounselDecision(
            decision_id="dec_v7_poster_noir",
            use_id=v7_poster.use_id,
            stable_lineage_key=poster_key,
            applicable_version_id="v7",
            status=DecisionStatus.APPROVED,
            rationale="Approved as de minimis background set dressing (2s blur, non-focal).",
            reviewer_display_name="Sarah Jenkins, Esq. (Clearance Counsel)",
        )
    )

    # Parallel search snapshot for poster (reveals original publication info)
    v8_evidence[poster_key] = PublicEvidenceSnapshot(
        snapshot_id="ev_poster_noir_parallel",
        use_id=v8_poster.use_id,
        stable_lineage_key=poster_key,
        query="Crime Detective Magazine 1946 Shadows Over Broadway copyright renewal",
        source_url="https://cocatalog.loc.gov/cgi-bin/Pwebrecon.cgi?v1=1946-crime-detective",
        source_title="US Copyright Office Historical Catalog - Renewal Records",
        excerpt="Registration #B-1946-8821 expired 1974 without timely renewal. Cover artwork in public domain in the United States.",
        stance=EvidenceStance.SUPPORTING,
        provider="Parallel",
        provider_call_id="prl_call_882910_poster",
        retrieval_latency_ms=142.5,
    )

    # -------------------------------------------------------------
    # ITEM 12: External Evidence Drift (Scene 18 - Midnight Serenade)
    # -------------------------------------------------------------
    music_key = "music_cue_midnight_serenade"
    v7_music_prominence = "Background jazz trio performance in speakeasy, 20s"
    v7_music_context = "Atmospheric jazz trumpet playing in background while characters talk."
    v7_music_hash = InvalidationEngine.compute_context_hash(
        v7_music_context, v7_music_prominence
    )

    v7_music = CreativeUse(
        use_id="use_v7_music_midnight",
        version_id="v7",
        scene_or_timecode="Scene 18 - 00:19:40",
        asset_type="music",
        description="'Midnight Serenade' jazz composition melody.",
        duration_or_prominence=v7_music_prominence,
        context=v7_music_context,
        stable_lineage_key=music_key,
        context_hash=v7_music_hash,
    )
    v7_uses.append(v7_music)

    # In V8, the script and audio placement are identical
    v8_music = CreativeUse(
        use_id="use_v8_music_midnight",
        version_id="v8",
        scene_or_timecode="Scene 18 - 00:19:40",
        asset_type="music",
        description="'Midnight Serenade' jazz composition melody.",
        duration_or_prominence=v7_music_prominence,
        context=v7_music_context,
        stable_lineage_key=music_key,
        context_hash=v7_music_hash,
    )
    v8_uses.append(v8_music)

    v7_decisions.append(
        CounselDecision(
            decision_id="dec_v7_music_midnight",
            use_id=v7_music.use_id,
            stable_lineage_key=music_key,
            applicable_version_id="v7",
            status=DecisionStatus.APPROVED,
            rationale="Approved based on initial public domain notation in music cue sheet.",
            reviewer_display_name="Sarah Jenkins, Esq. (Clearance Counsel)",
        )
    )

    # But in V8, live Parallel search discovers a recent copyright assignment notice!
    v8_evidence[music_key] = PublicEvidenceSnapshot(
        snapshot_id="ev_music_midnight_parallel",
        use_id=v8_music.use_id,
        stable_lineage_key=music_key,
        query="Midnight Serenade jazz sync rights copyright owner 2026",
        source_url="https://ascap.com/ace-title-search/midnight-serenade-9921",
        source_title="ASCAP ACE Repertory & Billboard Rights Bulletin",
        excerpt="Worldwide exclusive synchronization and master rights assigned August 2026 to Vanguard Media Holdings LLC (Administered by Kobalt Music). Prior public domain assertions disputed under European term extension.",
        stance=EvidenceStance.CONTRADICTORY,
        provider="Parallel",
        provider_call_id="prl_call_993012_music",
        retrieval_latency_ms=178.2,
    )

    return v7_uses, v8_uses, v7_decisions, v8_evidence


class ExpectedDeltaDict(dict):
    """
    Dictionary mapping stable_lineage_key -> DeltaAnalysisResult for golden expected deltas.
    Supports integer index access (e.g. deltas[10] for Item 11) as well as key-based access.
    """
    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


def get_golden_expected_deltas() -> ExpectedDeltaDict:
    """
    Returns explicit golden expected semantic delta analysis results for all 12 items.
    Asserts that:
    - Item 11 (Scene 42 poster: poster_noir_detective_magazine) has material delta (is_material=True).
    - Item 12 (Scene 18 jazz cue: music_cue_midnight_serenade) and Items 1-10 have is_material=False for creative context.
    """
    deltas = ExpectedDeltaDict({

        # 10 Unchanged Creative Uses (is_material=False, low risk, action=carry)
        "prop_vintage_telephone": DeltaAnalysisResult(
            is_material=False,
            prominence_shift="Identical incidental background set dressing, 4s.",
            narrative_impact="No creative delta detected in detective office establishing shot.",
            clearance_risk_level="low",
            statutory_fair_use_impact="Prior de minimis attestation carries forward.",
            recommended_action="carry",
            model_version="gemini-2.5-flash",
        ),
        "poster_paris_expo_1937": DeltaAnalysisResult(
            is_material=False,
            prominence_shift="Identical background hallway blur, 3s.",
            narrative_impact="Incidental tracking shot background remains unchanged.",
            clearance_risk_level="low",
            statutory_fair_use_impact="De minimis fair use defense under 17 U.S.C. § 107 intact.",
            recommended_action="carry",
            model_version="gemini-2.5-flash",
        ),
        "car_ford_sedan_1949": DeltaAnalysisResult(
            is_material=False,
            prominence_shift="Identical exterior street background, 6s.",
            narrative_impact="Parked curbside under streetlamp; visual framing unchanged.",
            clearance_risk_level="low",
            statutory_fair_use_impact="Prior attestation remains valid.",
            recommended_action="carry",
            model_version="gemini-2.5-flash",
        ),
        "trademark_acme_coffee": DeltaAnalysisResult(
            is_material=False,
            prominence_shift="Identical diner booth set dressing, 5s.",
            narrative_impact="Painted enamel sign remains out of focal focus.",
            clearance_risk_level="low",
            statutory_fair_use_impact="Prior attestation remains valid.",
            recommended_action="carry",
            model_version="gemini-2.5-flash",
        ),
        "artwork_abstract_expressionist": DeltaAnalysisResult(
            is_material=False,
            prominence_shift="Identical medium shot background, 8s.",
            narrative_impact="Oil canvas hanging behind executive desk unchanged.",
            clearance_risk_level="low",
            statutory_fair_use_impact="Prior attestation remains valid.",
            recommended_action="carry",
            model_version="gemini-2.5-flash",
        ),
        "likeness_mayor_cameo": DeltaAnalysisResult(
            is_material=False,
            prominence_shift="Identical crowd scene background, 2s.",
            narrative_impact="Courtroom gallery background murmur unchanged.",
            clearance_risk_level="low",
            statutory_fair_use_impact="Prior attestation remains valid.",
            recommended_action="carry",
            model_version="gemini-2.5-flash",
        ),
        "architecture_tribunal_facade": DeltaAnalysisResult(
            is_material=False,
            prominence_shift="Identical establishing wide exterior, 3s.",
            narrative_impact="Historic courthouse stone steps establishing shot unchanged.",
            clearance_risk_level="low",
            statutory_fair_use_impact="Prior attestation remains valid.",
            recommended_action="carry",
            model_version="gemini-2.5-flash",
        ),
        "text_headline_gazette": DeltaAnalysisResult(
            is_material=False,
            prominence_shift="Identical inserts prop, 2s.",
            narrative_impact="Glance at newsstand prop headline unchanged.",
            clearance_risk_level="low",
            statutory_fair_use_impact="Prior attestation remains valid.",
            recommended_action="carry",
            model_version="gemini-2.5-flash",
        ),
        "wardrobe_fedora_brand": DeltaAnalysisResult(
            is_material=False,
            prominence_shift="Identical character wardrobe, 10s.",
            narrative_impact="Vintage fedora worn on subway platform unchanged.",
            clearance_risk_level="low",
            statutory_fair_use_impact="Prior attestation remains valid.",
            recommended_action="carry",
            model_version="gemini-2.5-flash",
        ),
        "music_incidental_radio_static": DeltaAnalysisResult(
            is_material=False,
            prominence_shift="Identical incidental background audio, 12s.",
            narrative_impact="Foley radio hum in safehouse unchanged.",
            clearance_risk_level="low",
            statutory_fair_use_impact="Prior attestation remains valid.",
            recommended_action="carry",
            model_version="gemini-2.5-flash",
        ),
        # Item 11: Creative Drift (Scene 42 Poster) -> MATERIAL DELTA
        "poster_noir_detective_magazine": DeltaAnalysisResult(
            is_material=True,
            prominence_shift="Escalated from 2s out-of-focus background blur to 14s close-up focal dialogue.",
            narrative_impact="The character actively interacts with the artwork and quotes text aloud, eliminating incidental background defense.",
            clearance_risk_level="high",
            statutory_fair_use_impact="De minimis doctrine under 17 U.S.C. § 107 no longer applies; requires public domain verification or license.",
            recommended_action="revalidate",
            model_version="gemini-2.5-flash",
        ),
        # Item 12: External Evidence Drift (Scene 18 Jazz Cue) -> NON-MATERIAL CREATIVE CONTEXT
        # (Audio and placement identical in script; drift comes strictly from external registry evidence)
        "music_cue_midnight_serenade": DeltaAnalysisResult(
            is_material=False,
            prominence_shift="Identical background jazz trio performance, 20s.",
            narrative_impact="Creative script context and placement identical across V7 and V8.",
            clearance_risk_level="low",
            statutory_fair_use_impact="Creative script context unchanged; external copyright assignment evaluated separately by InvalidationEngine.",
            recommended_action="carry",
            model_version="gemini-2.5-flash",
        ),
    })

    # Assert Item 11 (Scene 42 poster) has material delta (is_material=True)
    poster_delta = deltas.get("poster_noir_detective_magazine")
    assert poster_delta is not None, "Missing Item 11 in expected deltas"
    assert poster_delta.is_material is True, "Item 11 must have is_material=True"
    assert poster_delta.clearance_risk_level == "high", "Item 11 must have clearance_risk_level='high'"

    # Assert Item 12 and Items 1-10 have is_material=False for creative context
    music_delta = deltas.get("music_cue_midnight_serenade")
    assert music_delta is not None, "Missing Item 12 in expected deltas"
    assert music_delta.is_material is False, "Item 12 must have is_material=False for creative context"
    assert music_delta.clearance_risk_level == "low", "Item 12 must have clearance_risk_level='low'"

    for key, delta in deltas.items():
        if key != "poster_noir_detective_magazine":
            assert delta.is_material is False, f"Expected non-material delta for {key}"
            assert delta.clearance_risk_level == "low", f"Expected low risk for {key}"

    assert len(deltas) == 12, "get_golden_expected_deltas must contain exactly 12 items"

    return deltas
