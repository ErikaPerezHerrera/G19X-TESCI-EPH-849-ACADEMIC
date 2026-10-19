# PluriJob

**Alumno:** Erika Pérez Herrera · **Matrícula:** G19X-TESCI-EPH-849
**Institución:** Tecnológico de Estudios Superiores de Cuautitlán Izcalli

## Descripción

PluriJob puede describirse como un sistema de matching entre competencias y perfiles laborales optimizado con IA. Los trabajadores de Recursos Humanos pueden crear vacantes desde un formulario o con un asistente de IA que provee la información adecuada para llenar dicho formulario, y los candidatos pueden proveer la información para crear una Hoja de Vida o CV y postularse a las vacantes que quieran. En el momento que se hace la postulación se calcula el porcentaje de match entre candidato y vacante.
<p>
Si bien el sistema cuenta con la ayuda de un asistente de IA que optimiza la extracción de información de archivos PDF y hace un análisis entre CV y Vacante para proveer al reclutador una opinión extra, la aplicación funciona principalmente gracias al motor de matching potenciado con PostgreSQL/pgvector y fastembed que hacen posible la mayor parte del análisis semántico.

## ¿Que hace?

## Qué necesitas instalado
- WSL + Docker Desktop (versión 4.92.0).
- Python.
- Git (opcional, y agregado a PATH para poder usar desde cualquier terminal).
- **Tener 2GB de RAM disponibles para levantar el contenedor**.

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
**nombreContenedor**, **nombreUsuarioBasedeDatos**, **nombreBasedeDatos** y **contraseñaBasedeDatos** deben coincidir con los de los archivos`docker-compose.yml`, `.env` y `backend/app/core/config.py`.

**GEMINI_API_KEY** debe coincidir en `.env` y `backend/app/core/config.py`. 


### Notas importantes
- El volumen `postgres_data` asegura que los datos persistan aunque se reinicie el contenedor.
- Si quieres reiniciar la base desde cero, usa:
  ```
  docker-compose down -v
  docker-compose up -d
    ```
- Para las pruebas (y fueron muy pocas pruebas) he usado dos a tres API KEYs gratuitas proporcionadas por Google AI Studio. **No se incluirán en Accesos de prueba** porque ya excedieron el límite de consultas por día. Se recomienda crear y usar una API KEY con mayor capacidad de consultas por día o vinculada a una Cuanta de facturación configurada en Google Cloud.

- Si no se ingresa una API KEY, conviene usar el respaldo de la base de datos para ver un desglose del análisis de IA hecho en una vacante (accediendo como un usuario de rol "admin" o "recruiter" de acuerdo a los Accesos de prueba).

- Al crearse la base de datos no hay ningun usuario, por lo que no hay credenciales de administrador, reclutador, usuario registrado; así como no hay nada de información sobre vacantes, postulaciones, CVs, trabajos.

- Por defecto, Docker Desktop asigna una cantidad prudente de recursos de tu PC. Si en algún momento notas que los contenedores se detienen solos o tardan demasiado, puedes revisar en Settings > Resources que tenga suficiente memoria RAM asignada.

## Restricciones
- Si el sistema se prueba sin restaurar la base de datos con `backup.sql`, el primer usuario que se registre desde `signup.html` tendrá el rol "admin", y podrá registrar reclutadores.
- Si una persona sin registro se postula, su CV vence en 12 meses.

## Falta por implementar:
- Manejo de las diferentes etapas del proceso de selección: por el momento solo se ve el estatus received para el candidato, y el reclutador o admin pueden rechazar la postulación.
- Envio de correos a los candidatos según la fase en la que se encuantra su proceso. Sin embargo, se contemplaron plantillas disponibles en la base de datos (tabla email_templates). (En el documento MVP.md se consideró como parte de otra etapa fuera del alcance de los avances hasta el día 16/10/2026)