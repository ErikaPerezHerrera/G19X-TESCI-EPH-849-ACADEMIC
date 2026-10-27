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
- Archivar vacantes.
- Inicio de sesión.
- Crear vacantes redactando personalmente el contenido.
- Reabrir y cerrar vacantes.
- Crear vacantes tomando la información de otras vacantes en la base de datos.
- Solicitar un borrador de vacante asistido por IA a partir de una descripción libre.
- Consultar vacantes activas y cerradas.
- Buscar y filtrar vacantes por texto, área, modalidad y estado.
- Reactivar una vacante cerrada o vencida reutilizando sus datos.
- Ver candidatos que aplicaron a una vacante.
- Ordenar candidatos por puntuación de matching.
- Revisar candidatos con habilidades adicionales o posible sobrecalificación.
- Consultar el detalle del CV.
- Descartar candidatos.
- Envío de correos con actualización de estado de postulaciones o vacantes.
- Programar entrevista.
- Contratar (cierra la vacante y avisa a los demás).

### Reclutador
- Inicio de sesión.
- Crear vacantes redactando personalmente el contenido.
- Crear vacantes tomando la información de otras vacantes en la base de datos.
- Solicitar un borrador de vacante asistido por IA a partir de una descripción libre.
- Reabrir y cerrar vacantes.
- Consultar vacantes activas y cerradas.
- Buscar y filtrar vacantes por texto, área, modalidad.
- Reactivar una vacante cerrada o vencida reutilizando sus datos.
- Ver candidatos que aplicaron a una vacante.
- Ordenar candidatos por puntuación de matching.
- Revisar candidatos con habilidades adicionales o posible sobrecalificación.
- Consultar el detalle del CV.
- Descartar candidatos.
- Envío de correos con actualización de estado de postulaciones o vacantes.
- Programar entrevista.
- Contratar (cierra la vacante y avisa a los demás)

### Candidato
- Listar y filtrar vacantes por texto, modalidad y área.
- Extraer texto del PDF.
- Usar IA opcional sobre el texto para enriquecer la extracción de datos del CV.
- Como usuario no registrado, revisar los campos extraídos/sugeridos antes de enviar la postulación.
- Aplicar a una vacante.
- Tener máximo 3 procesos al mismo tiempo.
- Registrarse y conservar el CV como usuario registrado.
- Como usuario registrado, consultar sus aplicaciones básicas mediante una lista sencilla de sus postulaciones.
- Como usuario registrado, cancelar postulaciones.
- Para la creación del CV, el uso de IA es opcional. El CV puede crearse directamente en el formulario provisto.


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
│   │   │   ├── config.py            # Lectura de variables de entorno (.env), configuración de CORS.
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
│   │   │   └── user.py
│   │   │
│   │   ├── services/              # Lógica de los motores y algoritmos e IA.
│   │   │   ├── autostore_job.py		 # Automatización de archivo de vacantes.
│   │   │   ├── email_service.py		 # Plantillas y envío de correos (SMTP real o simulado).
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
│   ├── tests/                     # Algunas pruebas Unitarias y de Integración (pytest)
│   │   ├── conftest.py
│   │   ├── test_applications.py
│   │   ├── test_auth.py
│   │   ├── test_email_service.py
│   │   ├── test_job_draft.py
│   │   ├── test_job_reopening.py
│   │   ├── test_job_skill_extraction.py
│   │   ├── test_jobs_management.py
│   │   ├── test_matching_engine.py
│   │   ├── test_pdf_extraction.py
│   │   ├── test_record_embeddings.py
│   │   ├── test_resume_ai_enrichment.py
│   │   └── test_resume_skill_extraction.py
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
│   │   ├── css/                   # Carpeta de archivos CSS (Estilos)
│   │   │   ├── styles.css         # Estilos extra aplicados (actualmente solo jobs.html lo usa)
│   │   │
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
2. Renombra los archivos `docker-compose.yml.example` y `backend/.env.example` o créalos desde cero (quítales el .example en el nombre). 

3. Copia y pega en `.env` y `docker-compose.yml` los Datos de Acceso que se encuentran en Mis Documentos > Accesos de Prueba. Y en `.env` cambia el valor de SECRET_KEY.

4. Abre Docker Desktop para que el servicio de Docker empieze a escuchar. Podrás continuar con la instalación hasta que en la barra de tareas, en el apartado de Iconos Ocultos, aparezca el icono de Docker con la leyenda "Docker Desktop Running".

5. Abre una terminal (PowerShell en Windows, Terminal en macOS/Linux), navega hasta la carpeta del proyecto y ejecuta:
  ```
  docker-compose up --build -d
  ```
A continuación se leerá el archivo **Dockerfile** y comenzarán a descargarse los requerimientos extra descritos en **requirements.txt**. De igual forma, se buscará la base de datos Plurjob y si esta no existe, se creará de forma automática con el archivo `init_db.sql`. (No incluye la ejecución de `backup.sql`, la base de datos se inicia casí vacia con excepción de las tablas email_templates y skills_cache).
Espera hasta que en la terminal aparezca el mensaje `plurijob-api INFO: Application startup complete`.

6. Copia la siguiente dirección y pégala en tu navegador para probar el sistema de forma local: 
`http://127.0.0.1:5500/src/pages/` ó `http://localhost:5500/src/pages/`


## Configuración para activar el envío de correos electrónicos
- En el archivo `.env.example` (que se renombrará como `.env`) se encuentran las constantes que usa `email_service.py` para enviar correos, pero en formato de comentario. Si se quiere probar la función de envío de correos deben quitarse los símbolos hash (#) que acompañan a las constantes. De lo contrario, el envío de correos se simulará en la terminal.
El correo de Google que se use tiene que tener forzosamente la verificación en dos pasos activada, de lo contrario no podrá adquirir una "Contraseña de aplicación", que es la que se usa en las variantes de `.env`.

## Respaldo de la base de datos
Este proyecto tiene en la carpeta `backend/app/db/`:
- `init_db.sql`: crea la estructura mínima y datos iniciales necesarios para un funcionamiento mínimo, como el contenido de email_templates y algunas habilidades blandas en skills_cache. Esta es la base "vacía" usada por el sistema cuando se levanta por primera vez el contenedor de Docker.
- `backup.sql`: respaldo completo de la base con datos generados durante el desarrollo. No se recomienda usarlo si se va a probar el sistema desde cero.

### Restaurar respaldo
Para restaurar el respaldo en un contenedor nuevo ejecuta en terminal de Git Bash o WSL, desde la carpeta principal del proyecto:
  ```
  docker exec -i nombreContenedor psql -U nombreUsuario -d nombreBase < backend/app/db/backup.sql
  ```
Para restaurar el respaldo en un contenedor nuevo ejecuta en terminal de Powershell o CMD desde la carpeta principal del proyecto:
  ```
  docker cp .\backend\app\db\backup.sql nombreContenedor:/tmp/backup.sql
  docker exec -it nombreContenedor psql -U nombreUsuarioBasedeDatos -d nombreBasedeDatos -f /tmp/backup.sql
  ```
**nombreContenedor**, **nombreUsuarioBasedeDatos**, **nombreBasedeDatos** y **contraseñaBasedeDatos** deben coincidir con los de los archivos `docker-compose.yml` y `backend/.env` (mismos datos de los Accesos de prueba)

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
- Si el sistema se usa sin restaurar la base de datos con `backup.sql`, el primer usuario que se registre desde `signup.html` tendrá el rol **"admin"**, y podrá registrar reclutadores.
- Si una persona sin registro se postula a una vacante, su CV vence en 12 meses. Al registrarse, se elimina la fecha de vencimiento del CV.
- Un candidato tiene un límite de 3 postulaciones máximo. Esto con el fin de reducir la posibilidad de sobrecarga por peticiones en el servicio de Gemini.
- Si el sistema se usa sin establecer un correo electrónico en .env para enviar correos, se simulará su envío en la terminal donde esté ejecutandose Docker

## Ejecución de Pruebas
El proyecto utiliza **pytest** para garantizar el correcto funcionamiento de el motor de matching, autenticación, procesamiento de archivos y manejo de base de datos en el backend, entre otras funciones. Para ejecutar las pruebas almacenadas en `backend/tests/` se tiene que levantar el sistema tal cual está descrito en la sección **Configurar e Instalar**. No requiere la instalación de **pytest** porque este ya está incluido en el archivo `requirements.txt` (que Docker usa para crear el contenedor).

**Atención:** (**nombreContenedor**, **nombreUsuarioBasedeDatos** deben ser los mismos que se usaron en docker-compose.yml, porque la base se va a crear en el mismo contenedor).

Si se quieren ejecutar debes seguir los siguientes pasos:
1. Crea una base de datos de prueba ejecutando en la terminal (Shell) en la ubicación de la carpeta principal del proyecto:
  ```
  docker exec -it nombreContenedor psql -U nombreUsuarioBasedeDatos -c "CREATE DATABASE plurijob_test;" ; docker exec -it nombreContenedor psql -U nombreUsuarioBasedeDatos -d plurijob_test -c "CREATE EXTENSION IF NOT EXISTS vector;"
  ```
2. Para ejecutar todas las pruebas ejecuta desde la carpeta principal del proyecto:
  ```
  python -m pytest
  ```
- Para ejecutar un archivo en específico, escribe la ruta completa hacia el archivo, por ejemplo:
  ```
  python -m pytest backend/tests/test_archivo_de_ejemplo.py
  ```
Y si deseas ver el nombre exacto de cada función de prueba conforme se va ejecutando y su estatus individual, añade la bandera -v:
  ```
  python -m pytest -v
  ```
ó
  ```
  python -m pytest backend/tests/test_archivo_de_ejemplo.py -v
  ```
**Otras opciones** 
- Dentro del contenedor Docker: Si no tienes un entorno de Python configurado localmente en tu máquina, puedes ejecutar las pruebas directamente dentro del contenedor en ejecución:
```
docker exec -it plurijob-api python -m pytest
```
Para ejecutar `python -m pytest` desde tu máquina local, asegúrate de haber instalado previamente las dependencias ejecutando `pip install -r backend/requirements.txt` en tu propio entorno virtual.

__

## Uso de IA
Me voy a extender más de lo que pidió:
* Se usó Copilot Free directamente en Visual Studio Code, y Gemini versión web cuando los creditos a partir del 16/10/2026.
* En el archivo MVP declaré que hasta el 23 de septiembre me la pasé investigando y anotando ideas. Todo ese tiempo estuve estableciendo la primer versión de lo que sería el funcionamiento del motor de extracción de PDF y el motor de matching que son las partes más complejas y pesadas del sistema; a partir de eso redacté el PRD y el MVP.
Para empezar a desarrollar el sistema usé primero a Gemini en la web. Como los únicos lenguajes que usé en el proyecto había usado eran HTML, CSS, JS y SQL, no sabía ni que usar. La estructura del arbol de carpetas, las tecnologías a usar y las primeras versiones de los motores se crearon con Gemini en web: yo redacté el pseudocódigo y las reglas de funcionamiento y la IA daba código, yo hacia pequeñas pruebas con los datos del match y los revisaba usando pgAdmin4 para conectarme a la base y veía si faltaba afinar el motor. Como evidencia está en Documentos la bitácora "Conversaciones con la IA": cuando el código se volvió muy grande como para pasarselo a Gemini empecé a discutir primero con ella la estrategia y retomando sus resultados para ordenar a Copilot que creara más código, corrigiera errores que yo todavía no ubicaba por donde salían y refinara los motores.
* Alrededor del 16/10 comencé a leer el código, comentar las funciones e identificar los pequeños errores de lógica que se escaparon de las reglas iniciales. Estos últimos diez días me he dedicado a conocer mi código, redactar personalmente README y Manual de usuario, y agregar las correciones y adiciones que la plataforma indica apoyandome de la capacidad de programación de la IA y mi comprensión del código para encontrar errores que ni ella podría detectar porque olvida constantemente.
* Creo que este proyecto es audaz por lo ambicioso que es el alcance del MVP, la inexperiencia en casi todas las tecnologías usadas y el uso de IA de la forma más migajera y controlada que jamás he hecho. Y me divertí.

__
## Notas para la evaluación:
- Hasta el 27/10/2026 12:36 am, al ejecutar las pruebas pasaron 86 de 86 sin errores.

- Se eliminó send_template_email de email_service.py y se usó send_email en conjunto con render_template.

- En los archivos subidos a plataforma se incluye una carpeta .zip con captura de pantalla de la interfaz de usuario sometida a revisión de los diferentes elementos y funciones de la página. Puede verse el uso de IA para las funciones para las que fue implementada, y pueden verse las capturas de las simulaciones de envio de correo en diferentes funciones del sistema. También se han subido dos capturas de pantalla por aparte mostrando el correo enviado y recibido. Y una foto de un mural de ideas.