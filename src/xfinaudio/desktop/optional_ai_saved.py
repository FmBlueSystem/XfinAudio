"""Anonymous saved-set selection with local evidence and no repository writes."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt

from xfinaudio.ai import structured_assists
from xfinaudio.ai.structured_assists import SavedInterpretation
from xfinaudio.application.saved_playlist_assistant import compare_saved_sets, describe_saved_set
from xfinaudio.desktop.optional_ai_assist import OptionalAssistController, Prepared
from xfinaudio.desktop.optional_ai_surfaces import add_panel, library_context, playlist_context


def install_saved_control(window: Any, *, services: Any = structured_assists) -> OptionalAssistController:
    screen = window._playlists_screen
    panel = add_panel(
        window,
        screen,
        2,
        "Share your request with exact saved-set names replaced by anonymous IDs, plus aggregate set metadata.",
    )
    rendered: list[str | None] = [None]

    def saved_sets() -> list:
        repository = window._playlist_repository
        return [p for summary in repository.list_summaries() if (p := repository.get_by_id(summary.id)) is not None]

    def context() -> tuple:
        return (
            library_context(window),
            id(window._playlist_repository),
            tuple(screen.list_widget.item(i).data(Qt.ItemDataRole.UserRole) for i in range(screen.list_widget.count())),
        )

    def clear() -> None:
        if rendered[0] is not None and screen.assistant_output.toPlainText() == rendered[0]:
            screen.assistant_output.clear()
        rendered[0] = None

    def prepare(request: str) -> Prepared:
        playlists, records = saved_sets(), list(window.scanned_records)
        if not playlists:
            raise ValueError("Save a playlist before asking AI to find or compare sets.")
        snapshot = tuple(playlist_context(p) for p in playlists)
        safe_request = services.anonymize_saved_request(request, playlists)
        descriptors = services.build_saved_descriptors(playlists, records)
        known = {f"s{i}": playlist for i, playlist in enumerate(playlists)}

        def show(value: object) -> None:
            if not isinstance(value, SavedInterpretation) or any(key not in known for key in value.selected_ids):
                raise ValueError("Invalid saved-set references")
            if snapshot != tuple(playlist_context(p) for p in saved_sets()):
                raise ValueError("Saved sets changed")
            if len(set(value.selected_ids)) != len(value.selected_ids):
                raise ValueError("Duplicate saved-set references")
            selected = [known[key] for key in value.selected_ids]
            text = (
                compare_saved_sets(selected, records)
                if value.action == "compare"
                else "\n".join(describe_saved_set(p, records) for p in selected) or "No saved playlists match."
            )
            rendered[0] = "AI-selected sets · facts calculated locally\n" + text
            screen.show_assistant_result(selected, rendered[0])

        return lambda: services.interpret_saved_request(safe_request, descriptors), show

    controller = OptionalAssistController(
        panel,
        screen.query_input,
        prepare=prepare,
        context=context,
        configure=window._settings_controller.open_ai_settings_dialog,
        parent=window,
        clear=clear,
    )
    for signal in (
        screen.query_requested,
        screen.compare_requested,
        screen.create_requested,
        screen.rename_requested,
        screen.duplicate_requested,
        screen.delete_requested,
    ):
        signal.connect(controller._invalidate)
    return controller
