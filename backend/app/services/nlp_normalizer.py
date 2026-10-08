import re
import unicodedata
from typing import List, Optional

def collapse_spaced_letters(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"(?<=\b[A-ZÁÉÍÓÚÑ])\s+(?=[A-ZÁÉÍÓÚÑ]\b)", "", text)


def _normalize_heading(text: str) -> str:
    unaccented = unicodedata.normalize("NFKD", text)
    return "".join(char for char in unaccented if not unicodedata.combining(char)).casefold()


_SKILL_SECTION_LABELS = {
    "habilidades tecnicas": "technical",
    "competencias tecnicas": "technical",
    "aptitudes tecnicas": "technical",
    "technical skills": "technical",
    "hard skills": "technical",
    "habilidades blandas": "soft",
    "competencias blandas": "soft",
    "aptitudes blandas": "soft",
    "soft skills": "soft",
    "habilidades": "general",
    "competencias": "general",
    "skills": "general",
    "conocimientos": "general",
    "tecnologias": "general",
}

_OTHER_SECTION_LABELS = {
    "experiencia",
    "experiencia laboral",
    "historial laboral",
    "work experience",
    "educacion",
    "formacion",
    "formacion academica",
    "estudios",
    "perfil",
    "resumen",
    "objetivo profesional",
    "proyectos",
    "proyectos destacados",
    "certificaciones",
    "certificados",
    "idiomas",
    "contacto",
    "informacion personal",
    "referencias",
}

_SECTION_PREFIX = re.compile(r"^\s*(?:#{1,6}\s*)?(?:\*\*)?\s*(.*?)\s*(?:\*\*)?\s*$")
_INLINE_SKILL_CATEGORY = re.compile(
    r"^\s*(?:habilidades?\s+)?(tecnicas?|blandas?|technical\s+skills|hard\s+skills|soft\s+skills)\s*:\s*(.*)$",
    re.IGNORECASE,
)
_SKILL_SEPARATORS = re.compile(r"\s*(?:,|;|\||•|·|\u2022)\s*")


def _section_header(line: str) -> tuple[Optional[str], str]:
    clean_line = re.sub(r"^\s*#{1,6}\s*", "", line.strip())
    clean_line = clean_line.strip().strip("*").strip()
    match = _SECTION_PREFIX.match(clean_line)
    if not match:
        return None, ""

    heading = match.group(1).strip().rstrip(":").strip()
    normalized = _normalize_heading(heading)
    if normalized in _SKILL_SECTION_LABELS:
        label = _SKILL_SECTION_LABELS[normalized]
        return label, ""

    # A heading may share a line with its content, e.g. "Habilidades: Python, SQL".
    for suffix in (":", " - ", " – "):
        if suffix in heading:
            possible_label, content = heading.split(suffix, 1)
            normalized_label = _normalize_heading(possible_label.strip())
            if normalized_label in _SKILL_SECTION_LABELS:
                return _SKILL_SECTION_LABELS[normalized_label], content.strip()
            if normalized_label in _OTHER_SECTION_LABELS:
                return "other", ""

    if normalized in _OTHER_SECTION_LABELS:
        return "other", ""

    return None, ""


def _split_skill_line(line: str) -> list[str]:
    content = re.sub(r"^\s*(?:[-*+•]|\d+[.)])\s*", "", line).strip()
    content = content.lstrip("*").strip()
    content = re.sub(r"^[^:]{1,40}:\s*", "", content)
    return [
        term.strip(" \t\r\n:.-")
        for term in _SKILL_SEPARATORS.split(content)
        if 2 <= len(term.strip(" \t\r\n:.-")) <= 150
    ]


def extract_resume_skills(text: str) -> tuple[List[str], List[str]]:
    """Extract original skill labels from explicitly named CV skill sections."""
    technical: list[str] = []
    soft: list[str] = []
    current_section: Optional[str] = None

    for line in text.splitlines():
        section, inline_content = _section_header(line)
        if section is not None:
            current_section = section
            if inline_content:
                destination = soft if section == "soft" else technical
                destination.extend(_split_skill_line(inline_content))
            continue

        if current_section is None or current_section == "other":
            continue

        category_match = _INLINE_SKILL_CATEGORY.match(line)
        if category_match and current_section == "general":
            category = _normalize_heading(category_match.group(1))
            destination = soft if category.startswith("bland") or category.startswith("soft") else technical
            destination.extend(_split_skill_line(category_match.group(2)))
            continue

        destination = soft if current_section == "soft" else technical
        destination.extend(_split_skill_line(line))

    def unique_original_terms(terms: list[str]) -> list[str]:
        unique: dict[str, str] = {}
        for term in terms:
            unique.setdefault(term.casefold(), term)
        return list(unique.values())

    return unique_original_terms(technical), unique_original_terms(soft)

def extract_professional_title(raw_text: str) -> str:
    unspaced_text = collapse_spaced_letters(raw_text)

    degree_match = re.search(
        r"\b(?:Licenciatura|Licenciado|Licenciada|Ingeniería|Ingeniero|Ingeniera|Estudiante|Pasante|Practicante|Becario|Técnico|Técnica|Tecnólogo|Tecnóloga|Master|Magíster)\s+(?:en\s+)?[A-Za-zÁÉÍÓÚáéíóúÑñ\s]{3,35}",
        unspaced_text,
        re.IGNORECASE,
    )
    academic_title = degree_match.group(0).strip() if degree_match else ""

    job_match = re.search(
        r"(?:Desarrollador|Desarrolladora|Ingeniero|Ingeniera|Analista|Practicante|Becario)\s+(?:Web|Junior|de\s+Software)?",
        unspaced_text,
        re.IGNORECASE,
    )
    current_position = job_match.group(0).strip() if job_match else ""

    parts = [p.title() for p in [academic_title, current_position] if p]

    if parts:
        return " / ".join(parts)

    return "Profesional / Candidato"


def extract_work_experience_or_projects(exp_text: str, full_text: str) -> List[str]:
    """
    Parsea la experiencia laboral o proyectos desarrollados.
    Descarta líneas con datos personales o certificados.
    """
    # 1. Buscar proyectos específicos con su año entre paréntesis
    projects = re.findall(
        r"((?:Punto de venta|Calculadora|Editor|Videojuego|Analizador|Chatbot|Sitio web)[^.\n]+?\((?:20\d{2}|19\d{2})\)\.)",
        full_text,
        re.IGNORECASE,
    )
    if projects:
        return [p.strip() for p in projects]

    # 2. Buscar bloque general de experiencia
    experience_text = exp_text or full_text
    exp_match = re.search(
        r"(?:EXPERIENCIA|EXPERIENCIA LABORAL|TRAYECTORIA PROFESIONAL)([\s\S]+?)(?=\n\s*(?:EDUCACIÓN|FORMACIÓN|HABILIDADES|CERTIFICADOS|DATOS)|$)",
        experience_text,
        re.IGNORECASE,
    )
    if exp_match:
        raw_lines = exp_match.group(1).split("\n")
        clean_lines = []
        for line in raw_lines:
            line_str = line.strip()
            # Ignorar basuras o datos personales colados
            if len(line_str) > 10 and not re.search(
                r"\b(?:(?:Estado civil|Fecha de nacimiento|Edad|CERTIFICADOS))\b",
                line_str,
                re.IGNORECASE,
            ):
                clean_lines.append(line_str)
        return clean_lines

    return []


def parse_work_experience_blocks(exp_text: str):
    if not exp_text:
        return []

    cleaned_text = re.sub(
        r"^(?:#+\s*)?(?:EXPERIENCIA\s+LABORAL|EXPERIENCIA|HISTORIAL\s+LABORAL|WORK\s+EXPERIENCE)[\r\n]+",
        "",
        exp_text.strip(),
        flags=re.IGNORECASE,
    )

    blocks = re.split(r"\n{2,}", cleaned_text)
    parsed_blocks = []

    for block in blocks:
        block_clean = block.strip()
        if not block_clean:
            continue

        if re.match(
            r"^(?:#+\s*)?(?:EXPERIENCIA|EDUCACIÓN|CONTACTO)", block_clean, re.I
        ):
            continue

        parsed_blocks.append(block_clean)

    return parsed_blocks

def extract_address_from_text(raw_text: str) -> Optional[str]:
    """
    Detecta patrones de domicilio/dirección en el texto del CV
    asegurando capturar la palabra completa al final.
    """
    if not raw_text:
        return None

    # Delimitadores de corte exactos para evitar sobre-captura
    stop_words = r"(?=\s+(?:Otra\s+referencia|Teléfono|Telefono|Tel|Correo|Email|LinkedIn|GitHub|Formación|Educación|Experiencia|\n|$))"

    # 1. Patrón con prefijos explícitos (ej: "Dirección: Paseo del Crespón... Cerrada de Ébano.")
    explicit_match = re.search(
        r"(?:domicilio|dirección|direccion|ubicación|ubicacion|residencia)\s*:\s*([^\n\r]+?)" + stop_words,
        raw_text,
        re.IGNORECASE,
    )
    if explicit_match:
        address = explicit_match.group(1).strip()
        # Eliminar punto final suelto si existe
        return address.strip(" .")

    # 2. Patrón de dirección física estándar
    address_pattern = re.search(
        r"\b(?:calle|av\.|avenida|blvd\.|bulevar|col\.|colonia|fracc\.|fraccionamiento|alcaldía|municipio|c\.p\.|cp|código\s*postal|paseo)\b.+?" + stop_words,
        raw_text,
        re.IGNORECASE,
    )
    if address_pattern:
        return address_pattern.group(0).strip(" .")

    return None


def detect_student_or_academic_title(raw_text: str) -> str:
    """Detecta títulos académicos o estado de estudiante colapsando letras espaciadas primero."""
    if not raw_text:
        return ""

    # Normalizar espacios entre letras (ej: E S T U D I A N T E -> ESTUDIANTE)
    unspaced_text = collapse_spaced_letters(raw_text)

    title_match = re.search(
        r"\b((?:Estudiante|Pasante|Ingeniero|Ingeniería|Licenciado|Licenciatura|Técnico)\s+(?:de|en)?\s+[A-Za-zÁÉÍÓÚáéíóúÑñ\s]{3,45})\b",
        unspaced_text,
        re.IGNORECASE,
    )
    if title_match:
        clean_title = title_match.group(1).split("\n")[0].strip()
        # Cortar si se arrastró un encabezado de sección posterior
        clean_title = re.split(r"\b(?:CONTACTO|CORREO|TELÉFONO|CELULAR|DIRECCIÓN)\b", clean_title, flags=re.IGNORECASE)[0]
        return clean_title.strip().title()

    return ""


def extract_unclassified_info(
    raw_text: str,
    full_name: str,
    email: str,
    phone: str,
    address: str,
    skills: list,
    work_experience: list,
) -> str:
    """
    Filtra del texto original los datos clasificados y remueve etiquetas de anonimización residuales.
    """
    if not raw_text:
        return ""

    text = collapse_spaced_letters(raw_text)

    # 1. Remover etiquetas de anonimización y datos PII directos
    targets_to_remove = [
        full_name,
        email,
        phone,
        address,
        "[INFORMACIÓN_RESERVADA]",
        "[EMAIL_OCULTO]",
        "[TELÉFONO_OCULTO]",
        "[DIRECCIÓN_OCULTA]",
    ]
    for target in targets_to_remove:
        if target and target != "Sin especificar" and len(target) > 1:
            text = re.sub(re.escape(target), "", text, flags=re.IGNORECASE)

    # 2. Remover título profesional / estudiante detectado
    text = re.sub(r"\bESTUDIANTEDEINGENIERIAENSISTEMASCOMPUTACIONALES\b", "", text, flags=re.IGNORECASE)

    # 3. Remover bloques de experiencia / proyectos
    for exp_item in work_experience:
        if isinstance(exp_item, str) and len(exp_item) > 4:
            text = text.replace(exp_item, "")

    # 4. Remover habilidades
    for skill in skills:
        if isinstance(skill, str) and len(skill) > 1:
            text = re.sub(r"\b" + re.escape(skill) + r"\b", "", text, flags=re.IGNORECASE)

    # 5. Remover palabras de encabezado
    headers_pattern = r"\b(?:NOMBRE|CONTACTO|CORREO|EMAIL|CELULAR|TELÉFONO|DIRECCIÓN|DOMICILIO|UBICACIÓN|HISTORIAL|ACADÉMICO|EDUCACIÓN|PERFIL|EXPERIENCIA|HABILIDADES)\b"
    text = re.sub(headers_pattern, "", text, flags=re.IGNORECASE)

    # 6. Limpieza de puntuaciones y espacios huerfanos
    text = re.sub(r"[\s,.:;•*\-–]{2,}", " ", text)

    lines = text.split("\n")
    clean_lines = []
    for line in lines:
        cleaned = line.strip(" ,.:;-")
        if len(cleaned) > 5 and re.search(r"[a-zA-ZÁÉÍÓÚáéíóú]", cleaned):
            clean_lines.append(cleaned)

    return " | ".join(clean_lines) if clean_lines else ""