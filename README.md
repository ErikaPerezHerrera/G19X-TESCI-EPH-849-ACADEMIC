# PluriJob

**Alumno:** Erika Pérez Herrera · **Matrícula:** G19X-TESCI-EPH-849
**Institución:** Tecnológico de Estudios Superiores de Cuautitlán Izcalli

## Descripción general

PluriJob puede describirse como un sistema de matching entre competencias y perfiles laborales optimizado con IA. Los trabajadores de Recursos Humanos pueden crear vacantes desde un formulario o con un asistente de IA que provee la información adecuada para llenar dicho formulario, y los candidatos pueden proveer la información para crear una Hoja de Vida o CV y postularse a las vacantes que quieran. En el momento que se hace la postulación se calcula el porcentaje de match entre candidato y vacante.
<p>
Si bien el sistema cuenta con la ayuda de un asistente de IA que optimiza la extracción de información de archivos PDF y hace un análisis entre CV y Vacante para proveer al reclutador una opinión extra, la aplicación funciona principalmente gracias al motor de matching potenciado con PostgreSQL/pgvector y fastembed que hacen posible la mayor parte del análisis semántico.

## ¿Qué hace?
### Administrador
- Agregar o eliminar reclutadores.
- Inicio de sesión.
- Crear vacantes.
- Reabrir y cerrar vacantes.
- Solicitar un borrador de vacante asistido por IA a partir de una descripción libre.
- Consultar vacantes activas y cerradas.
- Buscar y filtrar vacantes por texto, área, modalidad y estado.
- Reactivar una vacante cerrada reutilizando sus datos.
- Ver candidatos que aplicaron a una vacante.
- Ordenar candidatos por puntuación de matching.
- Revisar candidatos con habilidades adicionales o posible sobrecalificación.
- Consultar el detalle del CV.
- Descartar candidatos.

### Reclutador
- Inicio de sesión.
- Crear vacantes.
- Solicitar un borrador de vacante asistido por IA a partir de una descripción libre.
- Reabrir y cerrar vacantes.
- Consultar vacantes activas y cerradas.
- Buscar y filtrar vacantes por texto, área, modalidad.
- Reactivar una vacante cerrada reutilizando sus datos.
- Ver candidatos que aplicaron a una vacante.
- Ordenar candidatos por puntuación de matching.
- Revisar candidatos con habilidades adicionales o posible sobrecalificación.
- Consultar el detalle del CV.
- Descartar candidatos.

### Candidato
- Listar y filtrar vacantes por texto, modalidad y área.
- Extraer texto del PDF.
- Usar IA opcional sobre el texto para enriquecer la extracción de datos del CV.
- Revisar y editar los campos extraídos/sugeridos antes de enviar; el análisis local y la corrección manual siguen disponibles aunque la IA falle.
- Aplicar a una vacante como usuario casual (sin registrar en la plataforma).
- Registrarse y conservar el CV como usuario registrado.
- Como usuario registrado, consultar sus aplicaciones básicas mediante una lista sencilla de sus postulaciones.

## Tecnologías usadas:
- FastAPI
- Python
- PostgreSQL
- pgvector
- Docker
- Bootstrap
- Gemini API
- fastembed
- pdfplumber
- spacy

## ¿Qué necesitas instalado?
- WSL + Docker Desktop (versión 4.92.0).
- Python.
- Git (opcional, y agregado a PATH para poder usar desde cualquier terminal).
- **Tener 2GB de RAM disponibles para levantar el contenedor**.

## Esquema visual de las carpetas.
```
plurijob/
├── backend/                       # APLICACIÓN FASTAPI / PYTHON / PSpgSQL
│   ├── app/
│   │   ├── api/                   
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/		# Rutas 
│   │   │   │   │   ├── applications.py  # Crear, ver, listar, rechazar postulaciones.
│   │   │   │   │   ├── auth.py          # Registro (Sign Up), Inicio de sesión (Log In), JWT.
│   │   │   │   │   ├── jobs.py          # Reabrir, cerrar, listar vacantes; sincronizar estado de las vacantes. Crear vacantes manualmente o solicitar un borrador a API de Gemini, buscar detalles de una vacante.
│   │   │   │   │   ├── resumes.py       # Da formato a la información del CV para guardarla. Consulta, creación, actualización de CV y matching asociados al CV.
│   │   │   │   │   └── users.py         
│   │   │   │   └── router.py            # Enrutador principal de la API.
│   │   │   └── dependencies.py          # Inyección de dependencias (Auth JWT, DB Session).
│   │   │
│   │   ├── core/                  # Configuraciones Globales
│   │   │   ├── config.py            # Lectura de variables de entorno (.env), configuración de CORS, integración de API KEY de Gemini.
│   │   │   ├── database.py          # Conexión a PostgreSQL (SQLAlchemy, SQLAlchemy.orm)
│   │   │   └── security.py          # Hashing de contraseñas, creación/validación de tokens JWT, guardias de acceso según rol.
│   │   │
│   │   ├── db/                    # Scripts
│   │   │   ├── backup.sql           # Respaldo de la base da datos (datos de las pruebas)
│   │   │   └── init_db.sql          # Script SQL inicial con pgvector
│   │   │
│   │   ├── models/                # Modelos ORM (Mapeo de las tablas SQL)
│   │   │   ├── application.py
│   │   │   ├── email_template.py
│   │   │   ├── job.py
│   │   │   ├── resume.py
│   │   │   ├── skill_cache.py
│   │   │   └── user.py
│   │   │
│   │   ├── schemas/               # Esquemas Pydantic (Validación de Entrada / Salida JSON)
│   │   │   ├── application.py
│   │   │   ├── job.py
│   │   │   ├── resume.py
│   │   │   └── users.py
│   │   │
│   │   ├── services/              # Lógica de los motores y algoritmos e IA.
│   │   │   ├── gemini_service.py		 # Cliente API Gemini (System Prompt).
│   │   │   ├── markdown_parser.py		 # Conversión y limpieza del PDF a Markdown.
│   │   │   ├── matching_engine.py		 # Algoritmo de calculo de match.
│   │   │   ├── nlp_normalizer.py		 # Fragmentación de la información de Markdown, primer ordenamiento de información
│   │   │   ├── pdf_extractor.py		 # Extracción de información. Desde PDF hasta los datos obtenidos listos.
│   │   │   ├── skill_cache_service.py # Búsqueda de habilidades guardadas en la base de datos.
│   │   │   ├── skill_cosine_match.py  # Cálculo de cercanía de cosenos entre habilidades de la base.
│   │   │   ├── skill_exact_match.py   # Búsqueda de habilidades exactas entre habilidades de la base.
│   │   │   └── vector_service.py		 # Generación de embeddings.
│   │   │
│   │   └── main.py                # Punto de entrada FastAPI (CORS, Middlewares, Handlers, PostgreSQL, pgvector).
│   │
│   ├── .env.example               # Plantilla de variables de entorno del backend
│   ├── Dockerfile                 # Imagen Docker para el servidor FastAPI
│   └── requirements.txt           # Dependencias Python (fastapi, uvicorn, spacy, etc.)
│
├── frontend/                      # APLICACIÓN FRONTEND BOOTSTRAP (HTML5 / JS / CSS)
│   ├── public/                    # Archivos estáticos directos
│   │   └── favicon.ico
│   │
│   ├── src/                       # Código Fuente
│   │   ├── js/                    # Módulos JavaScript (Consumo de API REST / Renderizado)
│   │   │   ├── views/             # Lógica de interacción por vista
│   │   │   │   ├── casual_user.js			# Subida de CV, filtros de búsqueda
│   │   │   │   ├── dashboard_candidate.js	# Estado de postulación, edición de CV, subida de CV
│   │   │   │   ├── dashboard_recruiter.js	# Filtros de búsqueda, revisión de CVs y match de las postulaciones, descarte de candidatos
│   │   │   │   └── publish_job.js			# Publicación/reapertura de vacantes
│   │   │   ├── auth.js            # Manejo de Tokens JWT (LocalStorage/SessionStorage), Login, Signup
│   │   │   ├── config.js          # URLs base de API (http://localhost:8000/api/v1)
│   │   │   └── guard.js			 # Autenticación de roles y acceso a páginas protegidas
│   │   │
│   │   └── pages/                 # Vistas de la aplicación
│   │       ├── candidate/			 # Vistas de candidato
│   │       │   ├── dashboard.html		# Vacantes Aplicadas, estadísticas, información del matching de las postulaciones
│   │       │   └── cv_profile.html	# Información extraída del PDF
│   │       └── recruiter/			 #Vistas de reclutador y admin
│   │       │   ├── jobs.html			# Vacantes activas y lista de candidatos ordenados con su análisis de matching
│   │       │   └── publish.html		# Creación de vacante
│   │       ├── index.html         # Vista Casual / Landing de Vacantes
│   │       ├── login.html         # Inicio de Sesión
│   │       └── signup.html        # Registro
│
├── docker-compose.yml             # Orquestador local (PostgreSQL + pgvector, Backend, Frontend)
├── .gitignore                     # Exclusión de venv, __pycache__, .env, node_modules, .vscode, etcetera
└── README.md                      # Documentación del proyecto e instrucciones de instalación
```

## Configuración e Instalación
1. Descarga el ZIP del proyecto y descomprimelo. O clónalo con Git:
  ```
   git clone https://github.com/ErikaPerezHerrera/G19X-TESCI-EPH-849-ACADEMIC.git
   cd G19X-TESCI-EPH-849-ACADEMIC
  ```
2. Renombra los archivos `docker-compose.yml.example`, `backend/.env.example` y `backend/app/core/config.py.example`o créalos desde cero (quítales el .example en el nombre). 

3. Copia y pega en `.env` y `docker-compose.yml` los Datos de Acceso que se encuentran en Mis Documentos > Accesos de Prueba. Y en `.env` cambia el valor de SECRET_KEY.

4. Abre Docker Desktop para que el servicio de Docker empieze a escuchar.

5. Abre una terminal (PowerShell en Windows, Terminal en macOS/Linux), navega hasta la carpeta del proyecto y ejecuta:
  ```
docker-compose up --build -d
  ```
A continuación se leerá el archivo **Dockerfile** y comenzarán a descargarse los requerimientos extra descritos en **requirements.txt**. De igual forma, se buscará la base de datos Plurjob y si esta no existe, se creará de forma automática con el archivo `init_db.sql`. (No incluye la ejecución de `backup.sql`, la base de datos se inicia casí vacia con excepción de las tablas email_templates y skills_cache).

6. Abre una terminal y navega hasta la carpeta frontend del proyecto. Ejecuta el siguiente comando:
  ```
python -m http.server 5500 --bind 127.0.0.1
  ```
7. Copia la siguiente dirección y pégala en tu navegador para probar el sistema de forma local: 
`http://127.0.0.1:5500/frontend/src/pages/index.html`

## Respaldo de la base de datos
Este proyecto tiene en la carpeta `backend/app/db/`:
- `init_db.sql`: crea la estructura mínima y datos iniciales necesarios para un funcionamiento mínimo, como el contenido de email_templates y algunas habilidades blandas en skills_cache. Esta es la base "vacía" usada por el sistema cuando se levanta por primera vez el contenedor de Docker.
- `backup.sql`: respaldo completo de la base con datos generados durante el desarrollo. No se recomienda usarlo si se va a probar el sistema desde cero.

### Restaurar respaldo
Para restaurar el respaldo en un contenedor nuevo ejecuta en terminal:
  ```
docker exec -i nombreContenedor psql -U nombreUsuario -d nombreBase < backup.sql
  ```
**nombreContenedor**, **nombreUsuarioBasedeDatos**, **nombreBasedeDatos** y **contraseñaBasedeDatos** deben coincidir con los de los archivos `docker-compose.yml`, `backend.env` y `backend/app/core/config.py`.

**GEMINI_API_KEY** debe coincidir en `backend/.env` y `backend/app/core/config.py`. 


### Notas importantes
- El volumen `postgres_data` asegura que los datos persistan aunque se reinicie el contenedor.
- Si quieres reiniciar la base desde cero, usa:
  ```
  docker-compose down -v
  docker-compose up -d
    ```
- Para las pruebas (y fueron muy pocas pruebas) he usado dos a tres API KEYs gratuitas proporcionadas por Google AI Studio. **No se incluirán en Accesos de prueba** porque ya excedieron el límite de consultas por día. Se recomienda crear y usar una API KEY con mayor capacidad de consultas por día.

- Si no se ingresa una API KEY, conviene usar el respaldo de la base de datos para ver un desglose del análisis de IA hecho en una vacante (accediendo como un usuario de rol **"admin"** o **"recruiter"** de acuerdo a los Accesos de prueba).

- Al crearse la base de datos no hay ningún usuario, por lo que no hay credenciales de administrador, reclutador, usuario registrado; así como no hay nada de información sobre vacantes, postulaciones, CVs, trabajos.

- Por defecto Docker Desktop asigna una cantidad prudente de recursos de tu PC (2GB de RAM aproximadamente). Si en algún momento notas que los contenedores se detienen solos o tardan demasiado, puedes revisar desde Docker Desktop, en Settings > Resources que tenga suficiente memoria RAM asignada.

## Restricciones
- Si el sistema se prueba sin restaurar la base de datos con `backup.sql`, el primer usuario que se registre desde `signup.html` tendrá el rol **"admin"**, y podrá registrar reclutadores.
- Si una persona sin registro se postula a una vacante, su CV vence en 12 meses. Al registrarse, se elimina la fecha de vencimiento del CV.

## Falta por implementar
- Manejo de las diferentes etapas del proceso de selección: por el momento solo se ve el estatus received para el candidato, y el reclutador o admin pueden rechazar la postulación.
- Envio de correos a los candidatos según la fase en la que se encuantra su proceso. Sin embargo, se contemplaron plantillas disponibles en la base de datos (tabla email_templates). (En el documento `MVP.md` se consideró como parte de otra etapa fuera del alcance de los avances hasta el día 16/10/2026)