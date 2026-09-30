# Design

Extend the centralized text redactor with suffix-qualified relative audio paths;
quoted paths allow spaces in directory names. Keep existing absolute and known
path handling. The transport boundary stays unchanged and tests inject responses.
Disclosure avoids an absolute claim about arbitrary user-provided free text.

Store the raw saved-set name separately from decorated list text. Gate the
existing delete signal behind a named QMessageBox with Cancel default. Repository
and coordinator deletion semantics do not change; synthetic persistence tests
exercise acceptance and denial through the actual button.

Surgically add/update catalog messages in the actual QObject contexts and compile
with existing pyside6-lrelease, without a repository-wide lupdate or dependencies.
Use runtime QTranslator assertions and preserve all unrelated catalog entries.
