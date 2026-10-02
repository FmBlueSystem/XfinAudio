"""Install optional AI interpretation without replacing offline screen workflows."""

from __future__ import annotations

from typing import Any, cast

from PySide6.QtWidgets import QVBoxLayout

from xfinaudio.ai import structured_assists
from xfinaudio.ai.connection_test import endpoint_label
from xfinaudio.ai.privacy import redact_paths
from xfinaudio.ai.structured_assists import EditorInterpretation
from xfinaudio.desktop.library_query import LibraryQuery
from xfinaudio.desktop.optional_ai_assist import OptionalAssistController, OptionalAssistPanel, Prepared


def library_context(window: Any) -> tuple:
    state = window._state
    return (
        state.selected_folder,
        id(window.scanned_records),
        len(window.scanned_records),
        state.locked_paths,
        state.excluded_paths,
    )


def playlist_context(playlist: Any) -> tuple | None:
    if playlist is None:
        return None
    return (playlist.id, playlist.name, playlist.updated_at, tuple(playlist.track_paths))


def add_panel(window: Any, owner: Any, index: int, disclosure: str) -> OptionalAssistPanel:
    panel = OptionalAssistPanel(f"{disclosure} Sent to {endpoint_label()}. No audio or automatic changes.", owner)
    cast(QVBoxLayout, owner.layout()).insertWidget(index, panel)
    owner.ai_assist = panel
    return panel


def install_library_editor_controls(
    window: Any, *, services: Any = structured_assists
) -> dict[str, OptionalAssistController]:
    """All operation inputs and result consumers are captured on the GUI thread."""
    query = window._library_screen.query_panel
    editor = window._playlist_editor
    configure = window._settings_controller.open_ai_settings_dialog
    library_panel = add_panel(window, query, 1, "Share your typed request and genre vocabulary with AI.")

    def query_context() -> tuple:
        return library_context(window), query.query, tuple(field.text() for field in query.fields.values())

    def prepare_query(request: str) -> Prepared:
        if not window.scanned_records:
            raise ValueError("Scan your Library before asking AI.")
        paths = tuple(record.path for record in window.scanned_records)
        genres = sorted(
            {r.genre for r in window.scanned_records if r.genre and redact_paths(r.genre, paths) == r.genre}
        )

        def show(value: object) -> None:
            if not isinstance(value, LibraryQuery):
                raise ValueError("Invalid filters")
            query._show_query(value)
            query.editor.show()
            query.status.setText(query.tr("AI-suggested filters. Review, edit, then choose Apply edited filters."))

        return lambda: services.interpret_library_query(request, genres), show

    library = OptionalAssistController(
        library_panel,
        query.request_input,
        prepare=prepare_query,
        context=query_context,
        configure=configure,
        parent=window,
    )
    for button in (query.interpret_button, query.apply_button, query.clear_button):
        button.clicked.connect(library._invalidate)
    for field in query.fields.values():
        field.textEdited.connect(library._invalidate)

    editor_panel = add_panel(window, editor, 3, "Share only your typed edit request with AI. Avoid private details.")
    displayed_preview: list[object] = [None]

    def clear_preview() -> None:
        if displayed_preview[0] is not None and editor._preview is displayed_preview[0]:
            editor.dismiss_preview()
        displayed_preview[0] = None

    def editor_context() -> tuple:
        return (
            library_context(window),
            editor._playlist_id,
            editor.session_revision,
            tuple(editor._track_paths),
            editor._saved_paths,
            editor._locked_paths,
            editor._excluded_paths,
        )

    def prepare_edit(request: str) -> Prepared:
        if editor._playlist_id is None or not editor._track_paths or not window.scanned_records:
            raise ValueError("Open a saved set with current Library metadata before asking AI.")

        saved = window._playlist_repository.get_by_id(editor._playlist_id)
        snapshot = playlist_context(saved)
        if saved is None or tuple(saved.track_paths) != editor._saved_paths:
            raise ValueError("Saved set changed. Reopen it before asking AI.")

        def preview(value: object) -> None:
            if not isinstance(value, EditorInterpretation):
                raise ValueError("Invalid edit")
            if snapshot != playlist_context(window._playlist_repository.get_by_id(editor._playlist_id)):
                raise ValueError("Saved set changed")
            window._playlist_coordinator.preview_edit(value.command)
            displayed_preview[0] = editor._preview
            editor.status_label.setText(
                editor.tr("AI interpretation: ") + value.command + "\n" + editor.status_label.text()
            )

        return lambda: services.interpret_editor_request(request), preview

    editing = OptionalAssistController(
        editor_panel,
        editor.edit_input,
        prepare=prepare_edit,
        context=editor_context,
        clear=clear_preview,
        configure=configure,
        parent=window,
    )
    for button in (
        editor.preview_button,
        editor.confirm_button,
        editor.cancel_preview_button,
        editor.cancel_button,
        editor.save_button,
    ):
        button.clicked.connect(editing._invalidate)
    return {"library": library, "editor": editing}
