# markdown_parser.py (Sección split_markdown_by_sections)
import fitz  # PyMuPDF
import re
from typing import Dict, List, Any


def convert_pdf_to_markdown(file_bytes: bytes) -> str:
    try:
        # IMPORTANTE: Usar stream y especificar filetype="pdf"
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        markdown_text = ""

        for page in doc:
            # En versiones recientes de PyMuPDF se puede extraer como markdown
            # O extraer texto plano estructurado
            text = page.get_text("text")  # o page.get_text("markdown")
            markdown_text += text + "\n\n"

        doc.close()
        return markdown_text
    except Exception as e:
        print(f"Error convirtiendo PDF a Markdown: {e}")
        return ""

# markdown_parser.py (Sección split_markdown_by_sections)

def split_markdown_by_sections(md_text: str) -> Dict[str, str]:
    sections = {
        "personal": "",
        "experience": "",
        "education": "",
        "skills": "",
        "projects": "",
        "other": "",
    }

    if not md_text:
        return sections

    patterns = {
        "experience": r"(?i)(?:^|\n)\s*(?:#+\s*|\*\*?|\bullet\s*)?(?:experiencia\s*laboral|experiencia|historial\s*laboral|work\s*experience)\b",
        "education": r"(?i)(?:^|\n)\s*(?:#+\s*|\*\*?|\bullet\s*)?(?:formación\s*académica|formación|educación|estudios|academic)\b",
        "skills": r"(?i)(?:^|\n)\s*(?:#+\s*|\*\*?|\bullet\s*)?(?:habilidades\s*técnicas|habilidades|competencias|skills|tecnologías)\b",
        "projects": r"(?i)(?:^|\n)\s*(?:#+\s*|\*\*?|\bullet\s*)?(?:proyectos\s*destacados|proyectos|projects)\b",
        # Agregamos patrones para detectar Domicilio / Dirección / Ubicación
        "personal": r"(?i)(?:^|\n)\s*(?:#+\s*|\*\*?|\bullet\s*)?(?:información\s*personal|datos\s*de\s*contacto|contacto|domicilio|dirección|ubicación|personal\s*info)\b",
    }

    current_section = "personal"
    lines = md_text.split("\n")

    for line in lines:
        clean_line = line.strip()
        matched_section = None

        for sec_key, pattern in patterns.items():
            if re.search(pattern, clean_line):
                matched_section = sec_key
                break

        if matched_section:
            current_section = matched_section

        sections[current_section] += line + "\n"

    return sections

def clean_markdown_formatting(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"[#\*\_`~]", "", text)
    text = re.sub(r"^\s*[-•+o]\s*", "", text, flags=re.MULTILINE)
    return re.sub(r"\s+", " ", text).strip()



