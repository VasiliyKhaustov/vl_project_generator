from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from backend.cad.dwg_pdf_exporter import (
    DwgPdfExportError,
    _find_qcad_dwg2pdf_executable,
    export_note_dwg_to_pdf,
)


class DwgPdfExporterTests(unittest.TestCase):
    def test_export_note_dwg_to_pdf_uses_qcad_when_available(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        work_dir = project_root / "output" / "result"
        dwg_path = work_dir / "dwg" / "note_result.dwg"
        if not dwg_path.exists():
            self.skipTest("note_result.dwg отсутствует в output/result/dwg")

        pdf_path = work_dir / "temp" / "test_note_qcad.pdf"
        with patch(
            "backend.cad.dwg_pdf_exporter._try_external_pdf_export",
            return_value=None,
        ), patch(
            "backend.cad.dwg_pdf_exporter._try_autocad_accoreconsole_export",
            return_value=None,
        ), patch(
            "backend.cad.dwg_pdf_exporter._try_qcad_dwg2pdf_export",
            return_value="qcad_dwg2pdf",
        ) as qcad_mock, patch(
            "backend.cad.dwg_pdf_exporter.render_dxf_to_pdf_faithful",
        ) as render_mock:
            result = export_note_dwg_to_pdf(
                dwg_path,
                pdf_path,
                work_dir=work_dir,
                project_root=project_root,
            )

        qcad_mock.assert_called_once()
        render_mock.assert_not_called()
        self.assertEqual(result["method"], "qcad_dwg2pdf")
        self.assertTrue(result["faithful"])
        self.assertEqual(result["sourceDwg"], str(dwg_path.resolve()))

    def test_export_note_dwg_to_pdf_raises_without_qcad(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        work_dir = project_root / "temp_test_pdf"
        work_dir.mkdir(parents=True, exist_ok=True)
        dwg_path = work_dir / "note.dwg"
        dwg_path.write_bytes(b"TEST")
        pdf_path = work_dir / "note.pdf"

        with patch(
            "backend.cad.dwg_pdf_exporter._try_external_pdf_export",
            return_value=None,
        ), patch(
            "backend.cad.dwg_pdf_exporter._try_autocad_accoreconsole_export",
            return_value=None,
        ), patch(
            "backend.cad.dwg_pdf_exporter._try_qcad_dwg2pdf_export",
            return_value=None,
        ), patch(
            "backend.cad.dwg_pdf_exporter._allow_ezdxf_pdf_fallback",
            return_value=False,
        ):
            with self.assertRaises(DwgPdfExportError):
                export_note_dwg_to_pdf(
                    dwg_path,
                    pdf_path,
                    work_dir=work_dir,
                    project_root=project_root,
                )

    def test_find_qcad_dwg2pdf_executable_from_settings(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        executable = _find_qcad_dwg2pdf_executable(project_root)
        if not Path("/Applications/QCAD.app/Contents/Resources/dwg2pdf").exists():
            self.skipTest("QCAD не установлен")
        self.assertIsNotNone(executable)
        self.assertTrue(str(executable).endswith("dwg2pdf"))


if __name__ == "__main__":
    unittest.main()
