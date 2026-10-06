# Lematización con spaCy y API ESCO
# nlp_normalizer.py

import asyncio
import re
import httpx
from typing import List, Tuple, Optional
from app.services.markdown_parser import clean_markdown_formatting


ESCO_SEARCH_URL = "https://ec.europa.eu/esco/api/search"

TECH_EXACT_MAP = {
    "python": "Python",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "sql": "SQL",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "docker": "Docker",
    "fastapi": "FastAPI",
    "react": "React",
    "git": "Git",
}

def collapse_spaced_letters(text: str) -> str:
    """
    Unifica secuencias de letras mayúsculas separadas por espacios.
    Ejemplo: 'E S T U D I A N T E' -> 'ESTUDIANTE'
    """
    if not text:
        return ""
    return re.sub(r'(?<=\b[A-Za-z])\s+(?=[A-Za-z]\b)', '', texto)

def extract_candidate_skills_from_text(raw_text: str) -> List[str]:
    tokens = re.findall(r"\b[A-Za-z0-9+#.-]{2,20}\b", raw_text)
    seen = set()
    candidates = []
    for token in tokens:
        lower_token = token.lower()
        if lower_token not in seen and not lower_token.isdigit():
            seen.add(lower_token)
            candidates.append(token)
    return candidates

async def extract_professional_title_esco(
    client: httpx.AsyncClient, raw_text: str
) -> str:
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
    exp_match = re.search(
        r"(?:EXPERIENCIA|EXPERIENCIA LABORAL|TRAYECTORIA PROFESIONAL)([\s\S]+?)(?=\n\s*(?:EDUCACIÓN|FORMACIÓN|HABILIDADES|CERTIFICADOS|DATOS)|$)",
        full_text,
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


async def normalize_skill_with_esco(
    client: httpx.AsyncClient, term: str
) -> Optional[str]:
    clean_term = term.strip().lower()

    if clean_term in TECH_EXACT_MAP:
        return TECH_EXACT_MAP[clean_term]

    if len(clean_term) < 3:
        return None

    params = {"text": term, "type": "skill", "language": "es", "limit": 3}

    try:
        response = await client.get(ESCO_SEARCH_URL, params=params, timeout=1.5)
        if response.status_code == 200:
            results = response.json().get("_embedded", {}).get("results", [])

            for item in results:
                title = item.get("title", "")
                title_lower = title.lower()

                if clean_term == title_lower:
                    return title
    except Exception:
        pass

    if clean_term in {
        "html",
        "css",
        "javascript",
        "python",
        "react.js",
        "node.js",
        "fastapi",
        "mongodb",
        "postgresql",
        "vlans",
        "ospf",
        "eigrp",
        "hsrp",
        "github",
        "docker",
        "wireshark",
        "java",
        "php",
        "vb",
    }:
        return term.upper() if len(term) <= 3 else term.title()

    return None


SOFT_SKILLS_KEYWORDS = [
    "trabajo en equipo",
    "comunicación asertiva",
    "liderazgo",
    "resolución de problemas",
    "pensamiento crítico",
    "empatía",
    "gestión del tiempo",
    "adaptabilidad",
    "proactividad",
    "razonamiento lógico",
    "creatividad",
    "responsabilidad",
    "aprendizaje rápido",
]


def extract_soft_skills_from_text(text: str) -> List[str]:
    found_soft_skills = []
    text_lower = text.lower()
    for skill in SOFT_SKILLS_KEYWORDS:
        if skill in text_lower:
            found_soft_skills.append(skill.title())
    return list(set(found_soft_skills))


async def process_and_normalize_resume_data(
    raw_text: str, candidate_tokens: List[str]
) -> Tuple[str, List[str], List[str], Optional[str]]:

    smart_candidates = extract_candidate_skills_from_text(raw_text)
    if not smart_candidates:
        smart_candidates = candidate_tokens[:15]

    async with httpx.AsyncClient() as client:
        title_task = extract_professional_title_esco(client, raw_text)
        skills_tasks = [
            normalize_skill_with_esco(client, token) for token in smart_candidates
        ]

        results = await asyncio.gather(title_task, *skills_tasks)

        professional_title = results[0]
        raw_skills = results[1:]

        tech_skills = list(dict.fromkeys([s for s in raw_skills if s]))
        soft_skills = extract_soft_skills_from_text(raw_text)
        address = extract_address_from_text(raw_text)

    return professional_title, tech_skills, soft_skills, address


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

def collapse_spaced_letters(text: str) -> str:
    """
    Unifica secuencias de letras mayúsculas separadas por espacios.
    Ejemplo: 'E S T U D I A N T E' -> 'ESTUDIANTE'
    """
    if not text:
        return ""
    return re.sub(r"(?<=\b[A-ZÁÉÍÓÚÑ])\s+(?=[A-ZÁÉÍÓÚÑ]\b)", "", text)

# nlp_normalizer.py

import re
from typing import Optional, List

def collapse_spaced_letters(text: str) -> str:
    """
    Unifica secuencias de letras mayúsculas separadas por espacios.
    Ejemplo: 'E S T U D I A N T E' -> 'ESTUDIANTE'
    """
    if not text:
        return ""
    return re.sub(r"(?<=\b[A-ZÁÉÍÓÚÑ])\s+(?=[A-ZÁÉÍÓÚÑ]\b)", "", text)


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