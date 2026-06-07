"""Tests for MetadataViewModel worklist guidance (Work Unit 7)."""

from __future__ import annotations

from xfinaudio.desktop.metadata_view_model import MetadataViewModel


class TestWorklistGuidance:
    def test_worklist_guidance_mentions_bpm_key_energy(self) -> None:
        vm = MetadataViewModel()
        text = vm.worklist_guidance_text()
        assert text is not None
        assert "bpm" in text.lower() or "key" in text.lower() or "energy" in text.lower()

    def test_fix_metadata_guidance_mentions_external_fix(self) -> None:
        vm = MetadataViewModel()
        text = vm.fix_metadata_guidance_text()
        assert text is not None
        assert "external" in text.lower() or "tag" in text.lower() or "editor" in text.lower()

    def test_refresh_guidance_mentions_rescan(self) -> None:
        vm = MetadataViewModel()
        text = vm.refresh_guidance_text()
        assert text is not None
        assert "scan" in text.lower() or "refresh" in text.lower()
