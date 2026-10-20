# Plurijob -  Manual de Usuario (NO ESTÁ TERMINADO AÚN)
## Descripción General
PluriJob es un sistema de matching entre competencias y perfiles laborales optimizado con IA. Los trabajadores de Recursos Humanos pueden crear vacantes desde un formulario o con un asistente de IA que provee la información adecuada para llenar dicho formulario, y los candidatos pueden proveer la información para crear una Hoja de Vida o CV y postularse a las vacantes que quieran. En el momento que se hace la postulación se calcula el porcentaje de match entre candidato y vacante.
<p>
Si bien el sistema cuenta con la ayuda de un asistente de IA que optimiza la extracción de información de archivos PDF y hace un análisis entre CV y Vacante para proveer al reclutador una opinión extra, la aplicación funciona principalmente gracias al motor de matching potenciado con PostgreSQL/pgvector y fastembed que hacen posible la mayor parte del análisis semántico.

El siguiente manual de usuario está dirigido a las personas que participen como administradores del sistema, reclutadores y candidatos.

## Tipos de Usuarios y Permisos (Roles)
### Reclutador
Administra vacantes. El rol se le otorga cuando un usuario Administrador lo da de alta en el sistema.
#### Funciones:
- Inicio de sesión con correo y contraseña.
- Crear vacantes mediante formulario manual.
- Publicar y cerrar vacantes.
- Consultar vacantes activas y cerradas.
- Buscar y filtrar vacantes por texto, área, modalidad y estado.
- Reactivar una vacante cerrada reutilizando sus datos.
- Ver candidatos que aplicaron a una vacante.
- Ordenar candidatos por puntuación de matching.
- Revisar candidatos con habilidades adicionales o posible sobrecalificación.
- Consultar el detalle del CV.
- Descartar candidatos sin eliminar los datos del CV.

### Administrador 
Es el rol que obtiene la primera persona que se registra.
#### Funciones:
- Las mismas funciones que un Reclutador.
- Agregar o eliminar reclutadores.

### Usuario casual
Es el rol que adquiere una persona al entrar a la página principal de la aplicación **sin iniciar sesión**.
#### Funciones:
- Listar y filtrar vacantes por texto clave en el contenido.
- Extraer texto del PDF.
- Usar IA opcional para enriquecer y complementar el texto extraído del PDF.
- Revisar y editar los campos con información extraída antes de enviar.
- Aplicar a una vacante como usuario casual, es decir, sin necesidad de registrarse en el sistema.
- Registrarse.

### Usuario registrado
Es el rol que adquiere una persona al registrarse en el sistema. Se diferenci  a de Reclutador porque este es registrado por un usuario Administrador.
#### Funciones:
- Listar y filtrar vacantes por texto clave en el contenido.
- Extraer texto del PDF.
- Usar IA opcional para enriquecer y complementar el texto extraído del PDF.
- Revisar y editar los campos con información extraída antes de enviar.
- Aplicar a una vacante como usuario registrado.
- Inicio de sesión con correo y contraseña.
- Revisar el contenido de su CV digital
- Revisar las estadísticas disponibles de su perfil 
- Revisar la información del análisis de match para las postulaciones asociadas a su perfil, así como el estado de sus postulaciones.

### Distribución de páginas
- **Reclutador** y **Administrador**: Al iniciar sesión tienen acceso a `jobs.html` y `publish.html`.
- **Usuario registrado**: Al iniciar sesión tiene acceso a `dashboard.html,` y `cv_profile.html`. Aún puede acceder a `index.html` el cuál despliega los botones necesarios para navegar a las otras dos páginas.
- **Usuario casual**: Sólo tiene acceso a `index.html` en su versión sin hipervínculos a otras páginas.

## Acceso y Autenticación
La primera vez que el sistema es construido no cuenta con usuarios ni credenciales de ningún tipo. Por ello es necesario que a partir de `index.html`, den click en "Iniciar Sesión" para ir a `login.html`, ahí dar click en "Registrate aquí" para que los redirija a `signup.html`.

En `signup.html` se puede registrar cualquier persona mediante un formulario que pide un nombre de usuario, un correo y una contraseña que se va a encriptar. Si bien cualquiera puede registrarse, sólo el primer usuario que se registre obtendrá el rol **Administrador**; el resto de personas que se registren por este método serán **Usuario registrado**.

Los usuarios con rol **Reclutador** son registrados por el Administrador, nunca podrán registrarse por el método convencional.
Luego de ser registrados, **Administrador**, **Usuario registrado** y **Reclutador** pueden iniciar sesión dirigiendose a `index.html`, dando click en "Iniciar Sesión" para ir a `login.html`. Ahí se escribe en el formulario el correo y la contraseña con la que fueron registrados y dan click en "Iniciar sesión".

Después de iniciar sesión, cada que el usuario se desplaza entre páginas se valida la existencia del token JWT y su coincidencia con el que se le otorgó al usuario al iniciar la sesión. De esta forma se evita que con el cambio manual de ubicación de la página en la barra de URL del navegador, los usuarios puedan acceder a páginas cuando no han iniciado sesión. Al mismo tiempo también se corrobora que el usuario que inició sesión y el que está en la página sean el mismo y tengan el rol adecuado para la página a la que quieren acceder. Así los candidatos no pueden acceder a las páginas de los reclutadores y viceversa.

Cualquier intento de acceso invalidado a páginas protegidas mediante la edición de la dirección en barra de URL resultará en la redirección a `login.html`.

El token JWT tiene una duración de 8 horas.

## Funciones
### Extraer información del PDF
Esto puede hacerse desde `index.html` para **Usuario Casual** y desde `cv_profile.html` para **Usuario Registrado**.

**Notas:** Dado que el sistema esta diseñado para la contratación de personal en una empresa, sólo puede haber un CV por correo, esto con el fin de evitar que la misma persona aplique para dos vacantes en departamentos distintos. Sin embargo, no se le niega la posibilidad de aplicar a varias vacantes y editar el contenido de su CV bajo su consentimiento.

En `index.html`:
1. Da click sobre el botón *"Postularme"* (sobre una vacante). 
2. Se despliega un botón con la leyenda *"Elegir archivo"* para abrir el selector de archivos. Elige un CV en formato PDF para extraer la información.
3. Da click en *"Extraer información con IA"*. Se llenará automaticamente el formulario mencionado. Si el servicio de IA está configurado y disponible o no lo está, aparecerá una sección que nos afirma o niega la participación de la IA en el enriquecimiento de la información extraída.

En `cv_profile.html`:
1. Da click en el botón con la leyenda *"Elegir archivo"*. Elige un CV en formato PDF para extraer la información.
2. Da click en el botón *"Extraer y autocompletar". Se llenará automaticamente el formulario mencionado. Si el servicio de IA está configurado y disponible o no lo está, aparecerá una sección que nos afirma o niega la participación de la IA en el enriquecimiento de la información extraída.

### Postulación y guardado de CV
En `index.html`:
Relacionando el proceso de extracción de información del PDF, el **Usuario Casual** puede revisar la información y editarla antes de dar click en *"Enviar postulación"*. Al dar click en *"Enviar postulación"* aparecerá una advertencia que informa que si ya habia una postulación asociada al mismo correo ingresado podría afectar su visibilidad en dichas postulaciones. Puede elegir entre continuar o cancelar la postulación.

Al dar click en "Continuar", el sistema se tardará un poco en mostrar un mensaje que confirme el guardado exitoso del CV o un error en el proceso de guardado. El retraso para mostrar la alerta se debe al proceso de comprobación y guardado de habilidades técnicas y blandas, y el cálculo de matching en las postulaciones relacionadas con el correo del usuario.

**Nota:** el cv asociado a un correo de un usuario casual tiene una vigencia de 12 meses. Luego de ese tiempo se elimina de la base de datos. Si en algun momento se registra un usuario con el correo asociado a ese CV, se elimina la fecha de vencimiento.

En `cv_profile.html`:
Relacionando el proceso de extracción de información del PDF y continuando con el guardado de CV, el **Usuario Registrado** puede revisar la información y editarla antes de dar click en *"Guardar cambios"*. Al dar click en *"Guardar cambios"* aparecerá una advertencia que informa que si ya habia una postulación asociada al mismo correo ingresado podría afectar su visibilidad en dichas postulaciones. Puede elegir entre continuar o cancelar la postulación.

Al dar click en "Continuar", el sistema se tardará un poco en mostrar un mensaje que confirme el guardado exitoso del CV o un error en el proceso de guardado. El retraso para mostrar la alerta se debe al proceso de comprobación y guardado de habilidades técnicas y blandas, y el cálculo de matching en las postulaciones relacionadas con el correo del usuario.

En el caso del **Usuario Registrado** la postulación se lleva a cabo igualmente en `index.html`.

1. Da click sobre el botón *"Postularme"* (sobre una vacante).
2. Se llenará automaticamente un formulario con los datos del CV guardado. Se pueden realizar cambios.
3. Dar click en "Enviar postulación".

Al dar click en *"Enviar postulación"* aparecerá una advertencia que informa que si ya habia una postulación asociada al mismo correo ingresado podría afectar su visibilidad en dichas postulaciones. Puede elegir entre continuar o cancelar la postulación.

Al dar click en "Continuar", el sistema se tardará un poco en mostrar un mensaje que confirme el guardado exitoso del CV o un error en el proceso de guardado. El retraso para mostrar la alerta se debe al proceso de comprobación y guardado de habilidades técnicas y blandas, y el cálculo de matching en las postulaciones relacionadas con el correo del usuario.

**Nota:** Si el usuario no tiene un CV asociado a su correo, se lleva a cabo el mismo proceso de extracción de información del CV y postulación descrito para el Usuario Casual.

### Ver y Buscar Vacantes (usuarios con rol Casual y Registrado)
Esto puede hacerse desde `index.html`.
Al cargar la página se muestra un buscador en la parte superior. Si existen vacantes, en la parte principal de la página se ven tarjetas que incluyen:
- Título de la vacante
- Área o Departamento
- Modalidad
- Descripción del trabajo y responsabilidades
- Beneficios
- Habilidades técnicas requeridas.
**Nota:** La información se distribuye en espacios pequeños, por lo que podría parecer entrecortada.

En la tarjeta también hay dos botones: *"Información"* y *"Postularme"*. Al pulsar click en *"Información"* se despliega un modal que muestra la información completa de la vacante: los datos listados arriba más Habilidades blandas y Fecha de expiración (si es que tiene).

**Nota**
**Nota**
**Nota**
**Nota**: AQUÍ ME QUEDÉ EN LA REDACCIÓN 20/10/2026
El buscador en la parte superior es capaz de 

### Ver Vacantes (usuarios con rol Administrador y Reclutador)
Esto puede hacerse desde `jobs.html`.
Visualización del procesamiento y normalización automática de habilidades (skills).


Pasos para crear, editar y dar de baja ofertas de empleo.

Definición de requisitos y competencias técnicas clave.

Motor de Matching y Análisis de IA:

Cómo se vinculan los perfiles con las vacantes ideales.

Explicación del indicador de compatibilidad y la evaluación de sobrecalificación (over_ia_analysis).

5. Preguntas Frecuentes (FAQ) y Soporte
Respuestas a dudas comunes sobre el comportamiento de la interfaz, subida de archivos o visualización de resultados.

Canales de contacto o soporte técnico en caso de incidencias.