import asyncio
from unittest.mock import AsyncMock, patch
from app.services import pdf_extractor


def test_convert_pdf_to_markdown_success():
    """Valida que el servicio procese los bytes de un PDF y devuelva texto en Markdown."""
    fake_pdf_bytes = b"%PDF-1.4 mock content bytes"

    with patch.object(
        pdf_extractor,
        "convert_pdf_to_markdown",
        return_value="# Ana Gómez\nPython Developer",
    ) as mock_convert:
        result = pdf_extractor.convert_pdf_to_markdown(fake_pdf_bytes)

        mock_convert.assert_called_once_with(fake_pdf_bytes)
        assert "Ana Gómez" in result
        assert "Python Developer" in result


def test_pdf_extraction_pipeline_flow():
    """Prueba el flujo del pipeline de extracción de datos del PDF a nivel de servicio."""
    db = object()

    with (
        patch.object(
            pdf_extractor,
            "convert_pdf_to_markdown",
            return_value="Resume contents",
        ),
        patch.object(
            pdf_extractor,
            "extract_resume_skills",
            return_value=(["Python", "FastAPI"], ["Comunicación"]),
        ),
        patch.object(
            pdf_extractor,
            "cache_extracted_skill_terms",
            new_callable=AsyncMock,
        ) as cache_terms,
        patch.object(
            pdf_extractor, "clean_markdown_formatting", side_effect=lambda text: text
        ),
        patch.object(pdf_extractor, "extract_address_from_text", return_value=None),
        patch.object(
            pdf_extractor,
            "extract_name_and_anonymize",
            return_value=("Ana Gómez", "Resume contents"),
        ),
        patch.object(
            pdf_extractor, "detect_student_or_academic_title", return_value=None
        ),
        patch.object(
            pdf_extractor, "extract_professional_title", return_value="Backend Engineer"
        ),
        patch.object(
            pdf_extractor, "extract_work_experience_or_projects", return_value=[]
        ),
        patch.object(pdf_extractor, "extract_unclassified_info", return_value=""),
    ):
        result = asyncio.run(
            pdf_extractor.extract_data_from_pdf(b"pdf_bytes", "cv_ana.pdf", db=db)
        )

    cache_terms.assert_awaited_once_with(db, ["Python", "FastAPI", "Comunicación"])
    assert result["technical_skills"] == ["Python", "FastAPI"]
    assert result["soft_skills"] == ["Comunicación"]
    assert result["professional_title"] == "Backend Engineer"
