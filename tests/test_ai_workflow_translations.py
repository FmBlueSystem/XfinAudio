"""Core AI actions and destructive confirmation use the shipped QObject contexts."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from PySide6.QtCore import QTranslator
from PySide6.QtWidgets import QMessageBox

from xfinaudio.config.settings import AiSettings
from xfinaudio.desktop.ai_settings_panel import AiSettingsPanel
from xfinaudio.desktop.create_intent_preview import CreateIntentPreview
from xfinaudio.desktop.library_query_panel import LibraryQueryPanel
from xfinaudio.desktop.optional_ai_assist import OptionalAssistPanel
from xfinaudio.desktop.screens.playlist_editor import PlaylistEditor

ROOT = Path(__file__).resolve().parents[1]
CORE = {
    "OptionalAssistPanel": {
        "Allow this AI request": "Permitir esta solicitud de IA",
        "Ask AI": "Consultar IA",
        "Cancel AI": "Cancelar IA",
        "Configure AI": "Configurar IA",
    },
    "AiSettingsPanel": {
        "AI Settings": "Configuración de IA",
        "Enable AI for actions I request": "Activar IA para las acciones que solicite",
        "Test connection": "Probar conexión",
        "Cancel test": "Cancelar prueba",
        "Provider:": "Proveedor:",
        "Choose existing env file…": "Elegir archivo env existente…",
        "Use default file": "Usar archivo predeterminado",
        "Choose existing AI env file": "Elegir archivo env de IA existente",
        "Credential file: {0}": "Archivo de credenciales: {0}",
        "Testing connection…": "Probando conexión…",
        "AI disabled. Offline tools remain available.": "IA desactivada. Las herramientas locales siguen disponibles.",
        "Configuration found, not tested. No data has been sent by this dialog.": (
            "Configuración encontrada, sin probar. Este diálogo no ha enviado datos."
        ),
        "Credential not found. Configure NAN_API_KEY outside the app or choose an existing env file.": (
            "Credencial no encontrada. Configure NAN_API_KEY fuera de la app o elija un archivo env existente."
        ),
        "Authentication rejected. Check your provider credential outside the app, then retry.": (
            "Autenticación rechazada. Revise la credencial del proveedor fuera de la app e inténtelo de nuevo."
        ),
        "Connection unavailable. Check network or provider, then retry. Offline tools still work.": (
            "Conexión no disponible. Revise la red o el proveedor e inténtelo de nuevo. "
            "Las herramientas locales funcionan."
        ),
        "Connection successful. No library content was sent.": (
            "Conexión correcta. No se envió contenido de la biblioteca."
        ),
        "Invalid configuration. Check the HTTPS endpoint and NAN_API_KEY outside the app, then retry.": (
            "Configuración no válida. Revise el destino HTTPS y NAN_API_KEY fuera de la app e inténtelo de nuevo."
        ),
        "The provider returned an invalid response. Check the endpoint, then retry.": (
            "El proveedor devolvió una respuesta no válida. Revise el destino e inténtelo de nuevo."
        ),
        "Test cancelled. An already sent request may finish; retry when it stops. No settings were saved.": (
            "Prueba cancelada. Una solicitud ya enviada puede terminar; reintente cuando se detenga. "
            "No se guardó la configuración."
        ),
        (
            "AI actions send your request text and track/set metadata (titles, artists, genres, BPM, key, energy "
            "and transition/readiness summaries) to {0}; never audio. "
            "Known and recognizable file paths are removed. Avoid private information in free text. "
            "Opening Settings sends nothing. Offline tools remain available."
        ): (
            "Las acciones de IA envían su solicitud y metadatos de pistas/sets (títulos, artistas, géneros, BPM, "
            "tonalidad, energía y resúmenes de transiciones/preparación) a {0}; nunca audio. "
            "Se eliminan las rutas de archivo conocidas y reconocibles. Evite información privada en el texto libre. "
            "Abrir Configuración no envía nada. Las herramientas locales siguen disponibles."
        ),
        (
            "Configure NAN_API_KEY outside this app, in your launch environment or an operator-owned env file. "
            "Keep that file private (owner-only access). The environment key takes precedence. "
            "Never paste keys here; XfinAudio stores only the file path."
        ): (
            "Configure NAN_API_KEY fuera de esta app, en el entorno de inicio o en un archivo env de su propiedad. "
            "Mantenga ese archivo privado (acceso solo para el propietario). La clave del entorno tiene prioridad. "
            "Nunca pegue claves aquí; XfinAudio solo guarda la ruta del archivo."
        ),
        (
            'Test connection sends only "{0}" plus the model name and app identifier to {1}, authenticated '
            "with your key. No library content is sent. It may use provider quota. "
            "Testing does not save or enable AI for other actions."
        ): (
            'Probar conexión envía solo "{0}", el nombre del modelo y el identificador de la app a {1}, usando '
            "su clave para autenticarse. No se envía contenido de la biblioteca. Puede consumir cuota del proveedor. "
            "La prueba no guarda la configuración ni activa la IA para otras acciones."
        ),
    },
    "LibraryQueryPanel": {
        "Interpret locally": "Interpretar localmente",
        "Edit filters": "Editar filtros",
        "Apply edited filters": "Aplicar filtros editados",
        "Clear described filters": "Borrar filtros descritos",
    },
    "PlaylistEditor": {
        "Preview edit": "Previsualizar edición",
        "Apply preview to draft": "Aplicar vista previa al borrador",
        "Dismiss preview": "Descartar vista previa",
        "Discard draft": "Descartar borrador",
    },
    "CreateIntentPreview": {
        "Confirm and generate locally": "Confirmar y generar localmente",
        "Edit request": "Editar solicitud",
        "Review the interpreted request before generating local variants": (
            "Revise la solicitud interpretada antes de generar variantes locales"
        ),
    },
    "BuildScreen": {"Configure AI": "Configurar IA", "Cancel AI request": "Cancelar solicitud de IA"},
    "ReviewScreen": {"Configure AI": "Configurar IA"},
    "MyPlaylistsScreen": {
        "Delete": "Eliminar",
        "Cancel": "Cancelar",
        "Delete Playlist": "Eliminar playlist",
        'Delete "{0}" permanently? This cannot be undone. Audio files will not be deleted.': (
            '¿Eliminar "{0}" permanentemente? Esta acción no se puede deshacer. No se eliminarán archivos de audio.'
        ),
    },
}


@pytest.mark.parametrize("language", ["en", "es"])
def test_core_ai_messages_are_finished_in_source_and_compiled_catalog(qapp, language):
    root = ET.parse(ROOT / f"translations/xfinaudio_{language}.ts").getroot()
    messages = {
        (context.findtext("name"), message.findtext("source")): message.find("translation")
        for context in root.findall("context")
        for message in context.findall("message")
    }
    translator = QTranslator()
    assert translator.load(str(ROOT / f"assets/translations/xfinaudio_{language}.qm"))
    for context, entries in CORE.items():
        for source, spanish in entries.items():
            expected = spanish if language == "es" else source
            translation = messages.get((context, source))
            assert translation is not None, (context, source)
            assert translation.attrib.get("type") != "unfinished", (context, source)
            assert translation.text == expected
            assert translator.translate(context, source) == expected


def test_spanish_core_controls_render_in_actual_widgets(qapp, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    translator = QTranslator()
    assert translator.load(str(ROOT / "assets/translations/xfinaudio_es.qm"))
    qapp.installTranslator(translator)
    widgets = []
    try:
        assist = OptionalAssistPanel("Synthetic disclosure")
        settings = AiSettingsPanel(AiSettings())
        library = LibraryQueryPanel(lambda: [])
        editor = PlaylistEditor()
        preview = CreateIntentPreview()
        widgets.extend((assist, settings, library, editor, preview))
        assert assist.ask_button.text() == "Consultar IA"
        assert assist.configure_button.text() == "Configurar IA"
        assert assist.consent.text() == "Permitir esta solicitud de IA"
        assert settings.title() == "Configuración de IA"
        assert "nunca audio" in settings.privacy_label.text()
        assert "rutas de archivo conocidas y reconocibles" in settings.privacy_label.text()
        assert "Evite información privada en el texto libre" in settings.privacy_label.text()
        assert "Nunca pegue claves aquí" in settings.guidance_label.text()
        assert "Puede consumir cuota del proveedor" in settings.test_disclosure.text()
        assert settings.status_label.text() == "IA desactivada. Las herramientas locales siguen disponibles."
        assert library.interpret_button.text() == "Interpretar localmente"
        assert editor.preview_button.text() == "Previsualizar edición"
        assert editor.confirm_button.text() == "Aplicar vista previa al borrador"
        assert preview.confirm_button.text() == "Confirmar y generar localmente"
        from tests.test_my_playlists_screen import deletion_screen

        screen, repository, selected, _ = deletion_screen(tmp_path)
        widgets.append(screen)
        assert selected.id is not None

        prompts = []

        def confirm(dialog):
            prompts.append((dialog.text(), dialog.defaultButton().text()))
            return int(QMessageBox.StandardButton.Cancel)

        monkeypatch.setattr(QMessageBox, "exec", confirm)
        screen.delete_button.click()
        assert len(prompts) == 1
        assert selected.name in prompts[0][0]
        assert "Esta acción no se puede deshacer" in prompts[0][0]
        assert prompts[0][1] == "Cancelar"
        assert repository.get_by_id(selected.id) == selected
    finally:
        qapp.removeTranslator(translator)
        for widget in widgets:
            widget.close()
            widget.deleteLater()
