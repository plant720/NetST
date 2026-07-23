"""General FASTA/NEXUS/PHYLIP/VCF conversion dialog."""

import os
from typing import Dict, Optional

from PyQt6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QVBoxLayout,
)

from .language_manager import lang_manager


class FormatConversionDialog(QDialog):
    FORMATS = (
        ('auto', 'Auto'),
        ('fasta', 'FASTA'),
        ('nexus', 'NEXUS'),
        ('phylip', 'PHYLIP'),
        ('vcf', 'VCF'),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(lang_manager.get('dlg_convert_title', 'Sequence Format Conversion'))
        self.setMinimumWidth(660)
        root = QVBoxLayout(self)
        form = QFormLayout()

        self.input_edit = QLineEdit()
        self.output_edit = QLineEdit()
        self.reference_edit = QLineEdit()
        self.reference_name_edit = QLineEdit()
        self.input_format = QComboBox()
        self.output_format = QComboBox()
        for value, label in self.FORMATS:
            self.input_format.addItem(label, value)
            if value != 'auto':
                self.output_format.addItem(label, value)

        form.addRow(lang_manager.get('dlg_convert_input', 'Input file:'),
                    self._path_row(self.input_edit, self._browse_input))
        form.addRow(lang_manager.get('dlg_convert_input_format', 'Input format:'),
                    self.input_format)
        form.addRow(lang_manager.get('dlg_convert_output', 'Output file:'),
                    self._path_row(self.output_edit, self._browse_output))
        form.addRow(lang_manager.get('dlg_convert_output_format', 'Output format:'),
                    self.output_format)
        form.addRow(lang_manager.get('dlg_convert_reference_fasta',
                                     'Reference FASTA for VCF input (optional):'),
                    self._path_row(self.reference_edit, self._browse_reference))
        form.addRow(lang_manager.get('dlg_convert_reference_name',
                                     'Reference sample for VCF output (optional):'),
                    self.reference_name_edit)
        root.addLayout(form)

        note = QLabel(lang_manager.get(
            'dlg_convert_note',
            'VCF without a reference FASTA is converted to a variable-site alignment.'))
        note.setWordWrap(True)
        root.addWidget(note)

        buttons = QHBoxLayout()
        buttons.addStretch()
        convert_button = QPushButton(lang_manager.get('btn_convert', 'Convert'))
        cancel_button = QPushButton(lang_manager.get('btn_cancel', 'Cancel'))
        convert_button.clicked.connect(self._accept_if_valid)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(convert_button)
        buttons.addWidget(cancel_button)
        root.addLayout(buttons)

    def _path_row(self, line_edit, callback):
        row = QHBoxLayout()
        row.addWidget(line_edit, 1)
        button = QPushButton(lang_manager.get('btn_browse', 'Browse...'))
        button.clicked.connect(callback)
        row.addWidget(button)
        return row

    def _browse_input(self):
        path, _ = QFileDialog.getOpenFileName(
            self, lang_manager.get('dlg_convert_input', 'Input file:'), '',
            lang_manager.get('filter_sequence_formats',
                             'Sequence Files (*.fasta *.fas *.fa *.nex *.nexus *.nxs *.phy *.phylip *.vcf *.vcf.gz);;All Files (*.*)'))
        if path:
            self.input_edit.setText(path)

    def _browse_output(self):
        value = self.output_format.currentData()
        filters = {
            'fasta': 'FASTA Files (*.fasta)',
            'nexus': 'NEXUS Files (*.nex *.nexus *.nxs)',
            'phylip': 'PHYLIP Files (*.phy)',
            'vcf': 'VCF Files (*.vcf)',
        }
        path, _ = QFileDialog.getSaveFileName(
            self, lang_manager.get('dlg_convert_output', 'Output file:'), '',
            filters.get(value, 'All Files (*.*)'))
        if path:
            extensions = {
                'fasta': ('.fasta', ('.fasta', '.fas', '.fa', '.fna', '.ffn')),
                'nexus': ('.nex', ('.nex', '.nexus', '.nxs')),
                'phylip': ('.phy', ('.phy', '.phylip')),
                'vcf': ('.vcf', ('.vcf',)),
            }
            default_extension, accepted_extensions = extensions.get(
                value, ('', ()))
            if default_extension and not path.lower().endswith(accepted_extensions):
                path += default_extension
            self.output_edit.setText(path)

    def _browse_reference(self):
        path, _ = QFileDialog.getOpenFileName(
            self, lang_manager.get('dlg_convert_reference_fasta',
                                   'Reference FASTA for VCF input (optional):'), '',
            lang_manager.get('filter_fasta',
                             'FASTA Files (*.fas *.fasta *.fa);;All Files (*.*)'))
        if path:
            self.reference_edit.setText(path)

    def _accept_if_valid(self):
        input_path = self.input_edit.text().strip()
        output_path = self.output_edit.text().strip()
        if not input_path or not os.path.isfile(input_path) or not output_path:
            QMessageBox.warning(
                self, lang_manager.get('title_warning', 'Warning'),
                lang_manager.get('msg_conversion_paths_required',
                                 'Select an existing input file and an output path.'))
            return
        if os.path.abspath(input_path) == os.path.abspath(output_path):
            QMessageBox.warning(
                self, lang_manager.get('title_warning', 'Warning'),
                lang_manager.get('msg_conversion_same_path',
                                 'Input and output paths must be different.'))
            return
        self.accept()

    def get_config(self) -> Dict[str, str]:
        return {
            'input_path': self.input_edit.text().strip(),
            'output_path': self.output_edit.text().strip(),
            'input_format': self.input_format.currentData(),
            'output_format': self.output_format.currentData(),
            'reference_fasta': self.reference_edit.text().strip(),
            'reference_name': self.reference_name_edit.text().strip(),
        }

    @staticmethod
    def get_conversion_config(parent=None) -> Optional[Dict[str, str]]:
        dialog = FormatConversionDialog(parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_config()
        return None
