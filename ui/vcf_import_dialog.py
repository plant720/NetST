"""Dialog for importing a VCF together with McAN metadata."""

import os
from typing import Dict, Optional

from PyQt6.QtWidgets import (
    QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QVBoxLayout,
)

from .language_manager import lang_manager


class VcfImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(lang_manager.get('dlg_vcf_import_title', 'Import VCF and Metadata'))
        self.setMinimumWidth(640)

        root = QVBoxLayout(self)
        form = QFormLayout()
        self.vcf_edit = QLineEdit()
        self.metadata_edit = QLineEdit()
        self.reference_edit = QLineEdit()
        form.addRow(lang_manager.get('dlg_vcf_file', 'VCF file:'),
                    self._path_row(self.vcf_edit, self._browse_vcf))
        form.addRow(lang_manager.get('dlg_vcf_metadata', 'Metadata file:'),
                    self._path_row(self.metadata_edit, self._browse_metadata))
        form.addRow(lang_manager.get('dlg_vcf_reference', 'Reference FASTA (optional):'),
                    self._path_row(self.reference_edit, self._browse_reference))
        root.addLayout(form)

        note = QLabel(lang_manager.get(
            'dlg_vcf_import_note',
            'Without a reference FASTA, NetST imports a variable-site alignment.'))
        note.setWordWrap(True)
        root.addWidget(note)

        buttons = QHBoxLayout()
        buttons.addStretch()
        ok_button = QPushButton(lang_manager.get('btn_ok', 'OK'))
        cancel_button = QPushButton(lang_manager.get('btn_cancel', 'Cancel'))
        ok_button.clicked.connect(self._accept_if_valid)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        root.addLayout(buttons)

    def _path_row(self, line_edit: QLineEdit, callback):
        row = QHBoxLayout()
        row.addWidget(line_edit, 1)
        button = QPushButton(lang_manager.get('btn_browse', 'Browse...'))
        button.clicked.connect(callback)
        row.addWidget(button)
        return row

    def _browse_vcf(self):
        path, _ = QFileDialog.getOpenFileName(
            self, lang_manager.get('dlg_vcf_file', 'VCF file:'), '',
            lang_manager.get('filter_vcf', 'VCF Files (*.vcf *.vcf.gz);;All Files (*.*)'))
        if path:
            self.vcf_edit.setText(path)

    def _browse_metadata(self):
        path, _ = QFileDialog.getOpenFileName(
            self, lang_manager.get('dlg_vcf_metadata', 'Metadata file:'), '',
            lang_manager.get('filter_metadata',
                             'Metadata Files (*.tsv *.txt *.csv);;All Files (*.*)'))
        if path:
            self.metadata_edit.setText(path)

    def _browse_reference(self):
        path, _ = QFileDialog.getOpenFileName(
            self, lang_manager.get('dlg_vcf_reference', 'Reference FASTA (optional):'), '',
            lang_manager.get('filter_fasta',
                             'FASTA Files (*.fas *.fasta *.fa);;All Files (*.*)'))
        if path:
            self.reference_edit.setText(path)

    def _accept_if_valid(self):
        required = (self.vcf_edit.text().strip(), self.metadata_edit.text().strip())
        if any(not path or not os.path.isfile(path) for path in required):
            QMessageBox.warning(
                self, lang_manager.get('title_warning', 'Warning'),
                lang_manager.get('msg_vcf_metadata_required',
                                 'Select an existing VCF file and metadata file.'))
            return
        reference = self.reference_edit.text().strip()
        if reference and not os.path.isfile(reference):
            QMessageBox.warning(
                self, lang_manager.get('title_warning', 'Warning'),
                lang_manager.get('msg_reference_not_found',
                                 'The selected reference FASTA does not exist.'))
            return
        self.accept()

    def get_config(self) -> Dict[str, str]:
        return {
            'vcf_path': self.vcf_edit.text().strip(),
            'metadata_path': self.metadata_edit.text().strip(),
            'reference_fasta': self.reference_edit.text().strip(),
        }

    @staticmethod
    def get_import_config(parent=None) -> Optional[Dict[str, str]]:
        dialog = VcfImportDialog(parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_config()
        return None
