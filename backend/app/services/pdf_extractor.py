# pdf_extractor.py

import re
from typing import Tuple

from sqlalchemy.orm import Session

from app.services.markdown_parser import (
    convert_pdf_to_markdown,
    clean_markdown_formatting,
)

from app.services.nlp_normalizer import (
    extract_address_from_text,
    detect_student_or_academic_title,
    extract_work_experience_or_projects,
    extract_unclassified_info,
    collapse_spaced_letters,
    extract_professional_title,
    extract_resume_skills,
)
from app.services.skill_cache_service import cache_extracted_skill_terms



def clean_extracted_name(name_raw: str) -> str:
    """Limpia el nombre extraído eliminando letras espaciadas o títulos pegados."""
    if not name_raw:
        return ""
    # Desespaciar si el nombre viene separado por letras (ej: E R I K A)
    unspaced = collapse_spaced_letters(name_raw)
    name_clean = re.sub(r"\b(?:[A-Z]\s+){3,}[A-Z]\b.*", "", unspaced).strip()

    words = name_clean.split()
    if len(words) > 4:
        words = words[:4]
    return " ".join(words).title()

def extract_name_and_anonymize(raw_text: str, address: str = None) -> Tuple[str, str]:
    full_name = ""

    if raw_text:
        # 1. Obtener los primeros tokens antes de cualquier texto desespaciado como "E S T U D I A N T E"
        first_line = raw_text.split("\n")[0].strip()
        
        # Buscar palabras con formato de Nombre Propio al inicio (2 a 4 palabras)
        name_match = re.match(
            r"^([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})",
            first_line
        )
        if name_match:
            candidate_name = name_match.group(1).strip()
            # Validar que no contenga palabras clave reservadas
            if not re.search(r"\b(?:contacto|estudiante|ingenieria|curriculum|cv|perfil)\b", candidate_name, re.IGNORECASE):
                full_name = candidate_name.title()

    # Fallback RegEx si falla la primera línea
    if not full_name:
        fallback_match = re.search(
            r"(?:Nombre\s+completo|Nombre)\s*:\s*([A-Za-zÁÉÍÓÚáéíóúÑñ\s]{5,35}?)(?=\s+(?:Dirección|Teléfono|Correo|Email|\n|$))",
            raw_text,
            re.IGNORECASE,
        )
        if fallback_match:
            full_name = clean_extracted_name(fallback_match.group(1))

    anonymized_text = raw_text

    # Anonimizar Nombre
    if full_name and full_name != "Candidato Registrado":
        for part in full_name.split():
            if len(part) > 2:
                anonymized_text = re.sub(
                    r"\b" + re.escape(part) + r"\b",
                    "[INFORMACIÓN_RESERVADA]",
                    anonymized_text,
                    flags=re.IGNORECASE,
                )

    # Anonimizar PII
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    phone_pattern = r"(?:(?:\+|00)\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{4}"

    anonymized_text = re.sub(email_pattern, "[EMAIL_OCULTO]", anonymized_text)
    anonymized_text = re.sub(phone_pattern, "[TELÉFONO_OCULTO]", anonymized_text)

    # Anonimizar Dirección con límites de palabra (\b) para evitar romper palabras"
    if address and address != "Sin especificar":
        clean_addr_pattern = re.escape(address.strip())
        anonymized_text = re.sub(r"\b" + clean_addr_pattern + r"\b", "[DIRECCIÓN_OCULTA]", anonymized_text, flags=re.IGNORECASE)

    return full_name, anonymized_text
    
async def extract_data_from_pdf(
    file_contents: bytes, filename: str, db: Session | None = None
) -> dict:
    # 1. Convertir PDF a Markdown / Texto
    markdown_text = convert_pdf_to_markdown(file_contents)

    if not markdown_text.strip():
        import pdfplumber, io
        try:
            with pdfplumber.open(io.BytesIO(file_contents)) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        markdown_text += t + "\n"
        except Exception:
            markdown_text = f"Texto del archivo {filename}"

    # Parse skill terms from labeled sections while preserving their source spelling.
    technical_skills, soft_skills = extract_resume_skills(markdown_text)
    if db is not None:
        await cache_extracted_skill_terms(
            db, technical_skills + soft_skills
        )
    full_clean_text = clean_markdown_formatting(markdown_text)

    # 3. Contacto y extracción inicial de información
    email_match = re.search(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", full_clean_text
    )
    extracted_email = email_match.group(0) if email_match else ""

    phone_match = re.search(
        r"(?:(?:\+|00)\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{4}",
        full_clean_text,
    )
    extracted_phone = phone_match.group(0).strip() if phone_match else ""

    extracted_address = extract_address_from_text(full_clean_text)

    # Anonimizar texto
    full_name, anonymized_text = extract_name_and_anonymize(full_clean_text, extracted_address)
    if not full_name:
        full_name = "Candidato Registrado"

    # 4. Título profesional and original skill caching
    detected_title = detect_student_or_academic_title(full_clean_text)
    professional_title = extract_professional_title(full_clean_text)

    # Forzar el título académico/estudiante si fue detectado
    if detected_title:
        professional_title = detected_title
    elif not professional_title or professional_title == "Profesional / Candidato":
        professional_title = "Sin definir"

    # 5. Experiencia laboral o proyectos estructurados
    final_experience = extract_work_experience_or_projects("", full_clean_text)

    address_val = extracted_address or "Sin especificar"

    # 6. Extraer información no clasificada
    all_skills = list(dict.fromkeys(technical_skills + soft_skills))
    more_info = extract_unclassified_info(
        raw_text=anonymized_text,
        full_name=full_name,
        email=extracted_email,
        phone=extracted_phone,
        address=extracted_address,
        skills=all_skills,
        work_experience=final_experience,
    )

    summary_text = (
        f"Estudiante/Candidato con conocimientos en {', '.join(technical_skills[:5])}."
        if technical_skills
        else "Perfil profesional registrado."
    )

    return {
        "full_name": full_name,
        "email": extracted_email,
        "phone": extracted_phone,
        "address": address_val,
        "professional_title": professional_title,
        "technical_skills": technical_skills,
        "soft_skills": soft_skills,
        "work_experience": final_experience,
        "raw_text": anonymized_text,
        "extracted_skills": all_skills,
        "parsed_data": {
            "full_name": full_name,
            "email": extracted_email,
            "phone": extracted_phone,
            "professional_title": professional_title,
            "address": address_val,
            "location": address_val,
            "summary": summary_text,
            "work_experience": final_experience,
            "technical_skills": technical_skills,
            "soft_skills": soft_skills,
            "more_info": more_info,
        },
    }