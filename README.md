
# PluriJob

**Alumno:** Erika Pérez Herrera · **Matrícula:** G19X-TESCI-EPH-849
**Institución:** Tecnológico de Estudios Superiores de Cuautitlán Izcalli

## Qué hace

PluriJob puede describirse como un sistema de matching entre competencias y perfiles laborales optimizado con IA. Los trabajadores de Recursos Humanos pueden crear vacantes desde un formulario o con un asistente de IA que provee la información adecuada para llenar dicho formulario, y los candidatos pueden proveer la información para crear una Hoja de Vida o CV y postularse a las vacantes que quieran. En el momento que se hace la postulación se calcula el porcentaje de match entre candidato y vacante.
<p>
Si bien el sistema cuenta con la ayuda de un asistente de IA que optimiza la extracción de información de archivos PDF y hace un análisis entre CV y Vacante para proveer al reclutador una opinión extra, la aplicación funciona principalmente gracias al motor de matching potenciado con PostgreSQL/pgvector y fastembed que hacen posible la mayor parte del análisis semántico.

## Qué necesitas instalado
- Docker Desktop 

## Configuración e Instalación
1. Descarga el ZIP del proyecto y descomprimelo. O clónalo con Git:
 ```
   git clone https://github.com/ErikaPerezHerrera/G19X-TESCI-EPH-849-ACADEMIC.git
   cd G19X-TESCI-EPH-849-ACADEMIC
```
2. Copia y pega los Datos de Acceso de `docker-compose.yml`, `.env` y `app>core>config.py` que se encuentran en Mis Documentos> Accesos de Prueba.

3. Abre una terminal (PowerShell en Windows, Terminal en macOS/Linux) y ejecuta:
```
docker-compose up --build -d
```
4. Copia la siguiente direcció y pégala en tu navegador para probar el sistema de forma local: 
`http://127.0.0.1:5500/frontend/src/pages/index.html`

## Respaldo de la base de datos
Este proyecto incluye:
- `init_db.sql`: crea la estructura mínima y datos iniciales necesarios para un funcionamiento mínimo, como el contenido de email_templates y algunas habilidades blandas en skills_cache. Esta es la base "vacía" usada por el sistema cuando se levanta por primera vez el contenedor de Docker.
- `backup.sql`: respaldo completo de la base con datos generados durante el desarrollo. No se recomienda usarlo si se va a probar el sistema desde cero.

### Restaurar respaldo
Para restaurar el respaldo en un contenedor nuevo ejecuta en terminal:
```
docker exec -i nombreContenedor psql -U nombreUsuario -d nombreBase < backup.sql
```
**nombreContenedor**, **nombreUsuario** y **nombreBase** deben coincidir con los de los archivos`docker-compose.yml`, `.env` y `app>core>config.py`.

### Notas importantes
- El volumen `postgres_data` asegura que los datos persistan aunque se reinicie el contenedor.
- Si quieres reiniciar la base desde cero, usa:
  ```
  docker-compose down -v
  docker-compose up -d
    ```

## Restricciones
- Si el sistema se prueba sin respaldo, el primer usuario que se registre desde `signup.html` tendrá el rol "admin", y podrá registrar reclutadores.
- Si una persona sin registro se postula, su CV vence en 12 meses.

## Falta por implementar:
- Configuración del tema (oculto en `settings.html`).