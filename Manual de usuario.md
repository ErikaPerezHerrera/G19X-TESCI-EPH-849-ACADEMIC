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

|X| Inicio de sesión con correo y contraseña.
- Generar vacantes mediante formulario manual.
- Generar vacantes mediante asistencia de IA.
- Generar vacantes reutilizando la información de otras vacantes.
- Publicar vacantes.
- Cerrar vacantes sin eliminar postulaciones.
- Consultar vacantes activas y cerradas.

|X| Buscar y filtrar vacantes por texto, área, modalidad y estado.

- Reactivar vacantes cerradas o vencidad reutilizando sus datos.
- Ver candidatos que aplicaron a una vacante.
- Ordenar candidatos por puntuación de matching.
- Revisar candidatos con habilidades adicionales o posible sobrecalificación.
- Consultar el detalle del CV.
- Descartar candidatos sin eliminar los datos del CV.

### Administrador 
Es el rol que obtiene la primera persona que se registra.
#### Funciones:
- Las mismas funciones que un Reclutador.

|X| Registrar reclutadores.

- Archivar vacantes cerradas, eliminando postulaciones.

### Usuario casual
Es el rol que adquiere una persona al entrar a la página principal de la aplicación **sin iniciar sesión**.
#### Funciones:
- Crear un CV digital manualmente o usando la extracción de información de PDF asistida por IA.
- Listar y filtrar vacantes por texto clave en el contenido.
- Aplicar a una vacante como usuario casual, es decir, sin necesidad de registrarse en el sistema.
- Registrarse.

### Usuario registrado
Es el rol que adquiere una persona al registrarse en el sistema. Se diferenci  a de Reclutador porque este es registrado por un usuario Administrador.
#### Funciones:
- Crear un CV digital manualmente o usando la extracción de información de PDF asistida por IA.
- Listar y filtrar vacantes por texto clave en el contenido.
- Inicio de sesión con correo y contraseña.
- Aplicar a una vacante como usuario registrado (máximo 3 postulaciones simultaneas).
- Revisar el contenido de su CV digital.
- Revisar las estadísticas disponibles de su perfil.
- Revisar la información del análisis de match de las postulaciones asociadas a su perfil, así como el estado e información de sus postulaciones.
- Cancelar una postulación.

### Distribución de páginas
- **Reclutador** y **Administrador**: Al iniciar sesión tienen acceso a `jobs.html` y `publish.html`.
- **Usuario registrado**: Al iniciar sesión tiene acceso a `dashboard.html,` y `cv_profile.html`. Aún puede acceder a `index.html` el cuál despliega los botones necesarios para navegar a las otras dos páginas.
- **Usuario casual**: Sólo tiene acceso a `index.html` en su versión sin hipervínculos a otras páginas.
___

## Registro, Acceso y Autenticación
La primera vez que el sistema es construido no cuenta con usuarios ni credenciales de ningún tipo. Por ello es necesario que a partir de `index.html`, den click en "Iniciar Sesión" para ir a `login.html`, ahí dar click en "Registrate aquí" para que los redirija a `signup.html`.

En `signup.html` se puede registrar cualquier persona mediante un formulario que pide un nombre de usuario, un correo y una contraseña que se va a encriptar. Si bien cualquiera puede registrarse, sólo el primer usuario que se registre obtendrá el rol **Administrador**; el resto de personas que se registren por este método serán **Usuario registrado**.

Los usuarios con rol **Reclutador** son registrados por el Administrador, nunca podrán registrarse por el método convencional.
Luego de ser registrados, **Administrador**, **Usuario registrado** y **Reclutador** pueden iniciar sesión dirigiendose a `index.html`, dando click en "Iniciar Sesión" para ir a `login.html`. Ahí se escribe en el formulario el correo y la contraseña con la que fueron registrados y dan click en "Iniciar sesión".

Después de iniciar sesión, cada que el usuario se desplaza entre páginas se valida la existencia del token JWT y su coincidencia con el que se le otorgó al usuario al iniciar la sesión. De esta forma se evita que con el cambio manual de ubicación de la página en la barra de URL del navegador, los usuarios puedan acceder a páginas cuando no han iniciado sesión. Al mismo tiempo también se corrobora que el usuario que inició sesión y el que está en la página sean el mismo y tengan el rol adecuado para la página a la que quieren acceder. Así los candidatos no pueden acceder a las páginas de los reclutadores y viceversa.

Cualquier intento de acceso invalidado a páginas protegidas mediante la edición de la dirección en barra de URL resultará en la redirección a `login.html`.

El token JWT tiene una duración de 8 horas.
___

## Funciones de Usuarios Casual Y Registrado
### Creación de un CV digital
Esto puede hacerse desde `index.html` para **Usuario Casual** y desde `cv_profile.html` para **Usuario Registrado**.

**Notas:** Dado que el sistema esta diseñado para la contratación de personal en una empresa, sólo puede haber un CV por correo, esto con el fin de evitar que la misma persona aplique para dos vacantes en departamentos distintos. Sin embargo, no se le niega la posibilidad de aplicar a 3 vacantes y editar el contenido de su CV bajo su consentimiento.

En `index.html`:
1. Da click sobre el botón **"Postularme"** (sobre una vacante). 
2. Se despliega un botón con la leyenda **"Elegir archivo"** para abrir el selector de archivos, así como un formulario.

    *Si lo desea puede generar la información del CV llenando el fomulario manualmente. Si quiere digitalizar la información de un CV en formato PDF seleccione uno con el selector de archivos.*

3. Si seleccionó un archivo para extraer su información, de click en el botón **"Extraer información con IA"**. Se llenará automaticamente el formulario mencionado. Si el servicio de IA está configurado y disponible o no lo está, aparecerá una sección que nos afirma o niega la participación de la IA en el enriquecimiento de la información extraída.

En `cv_profile.html`:
1. En esta página se encuentra un botón con la leyenda **"Elegir archivo"** para abrir el selector de archivos, así como un formulario y una barra de progreso que se llena según haya contenido o no en ciertos campos del formulario. 

    *Si lo desea puede generar la información del CV llenando el formulario manualmente. Si quiere digitalizar la información de un CV en formato PDF seleccione uno con el selector de archivos.*

2. Si seleccionó un archivo para extraer su información, de click en el botón **"Extraer y autocompletar"**. Se llenará automaticamente el formulario mencionado. Si el servicio de IA está configurado y disponible o no lo está, aparecerá una sección que nos afirma o niega la participación de la IA en el enriquecimiento de la información extraída.
___

### Postulación y Guardado de CV
#### Usuario casual: Guardado de cv y creación de postulación en `index.html`:
Relacionando el proceso de extracción de información del PDF, el **Usuario Casual** puede revisar la información y editarla antes de dar click en **"Enviar postulación"**. 
1. Da click en **"Enviar postulación"**. Aparecerá una advertencia que informa que si ya habia una postulación asociada al mismo correo ingresado podría afectar su visibilidad en dichas postulaciones. Puede elegir entre continuar o cancelar la postulación.

2. Si da click en **"Continuar"**, el sistema se tardará un poco en mostrar un mensaje que confirme el guardado exitoso del CV o un error en el proceso de guardado. El retraso para mostrar la alerta se debe al proceso de comprobación y guardado de habilidades técnicas y blandas, y el cálculo de matching en las postulaciones relacionadas con el correo del usuario.

#### Usuario registrado: Guardado de CV en `cv_profile.html`:
Relacionando el proceso de extracción de información del PDF y continuando con el guardado de CV, el **Usuario Registrado** puede revisar la información y editarla antes de dar click en **"Guardar cambios"**.
1. Da click en **"Guardar cambios"**. Aparecerá una advertencia que informa que si ya habia una postulación asociada al mismo correo ingresado podría afectar su visibilidad en dichas postulaciones. Puede elegir entre continuar o cancelar la postulación.

2. Si da click en **"Continuar"**, el sistema se tardará un poco en mostrar un mensaje que confirme el guardado exitoso del CV o un error en el proceso de guardado. El retraso para mostrar la alerta se debe al proceso de comprobación y guardado de habilidades técnicas y blandas, y el cálculo de matching en las postulaciones relacionadas con el correo del usuario.

Si realizó cambios en la información del formulario (ya sea que sea creación del primer CV asociado a la cuenta o cambios en información del CV encontrado en la base de datos), si cambia de página sin presionar **"Guardar cambios"** estos no se aplicarán.

#### Usuario registrado: Postulación en `index.html`.

1. Da click sobre el botón **"Postularme"** (sobre una vacante). Se llenará automaticamente un formulario con los datos del CV guardado. Estos datos no se pueden editar.
2. Da click en **"Enviar postulación"**.

3. Da click en **"Enviar postulación"**. Aparecerá una advertencia que informa que si ya habia una postulación asociada al mismo correo ingresado podría afectar su visibilidad en dichas postulaciones. Puede elegir entre continuar o cancelar la postulación.

4. Si da click en **"Continuar"**, el sistema se tardará un poco en mostrar un mensaje que confirme el guardado exitoso del CV o un error en el proceso de guardado. El retraso para mostrar la alerta se debe al proceso de comprobación y guardado de habilidades técnicas y blandas, y el cálculo de matching en las postulaciones relacionadas con el correo del usuario.

**Nota:** el CV asociado a un correo de un usuario casual tiene una vigencia de 12 meses. Luego de ese tiempo se elimina de la base de datos. Si en algún momento se registra un usuario con el correo asociado a ese CV, se elimina la fecha de vencimiento. Todos los candidatos tienen un máximo de 3 postulaciones, por lo que si se intenta tener una cuarta esta no se podrá realizar.
___

### Usuario registrado: COnsultar CV guardado
Si el usuario registrado cuenta con un CV guardado en la base de datos, su información se mostrará al iniciar sesión y dirigirse a la página `cv_profile.html`. Un Usuario casual no puede consultar la información de CV a no ser que se registre.

____
### Ver Vacantes
Esto puede hacerse desde `index.html`.
Al cargar la página se muestra un buscador en la parte superior. Si existen vacantes, en la parte principal de la página se ven tarjetas que incluyen:
- Título de la vacante
- Área o Departamento
- Modalidad
- Descripción del trabajo y responsabilidades
- Beneficios
- Habilidades técnicas requeridas.

**Nota:** La información se distribuye en espacios pequeños, por lo que podría mostrarse entrecortada.

En la tarjeta también hay dos botones: **"Información"** y **"Postularme"**. 
Al pulsar click en **"Información"** se despliega un modal que muestra la información completa de la vacante: los datos listados arriba más Habilidades blandas y Fecha de expiración (si es que tiene).

Dependiendo de si el usuario inició sesión o no, al presionar el botón **"Postularme"** aparecerán las opciones descritas para Usuario casual o Usuario registrado y se puede llevar a cabo la postulación de acuerdo a los procesos discutidos en la sección Postulación y Guardado de CV.

### Buscar Vacantes activas
En `index.html` el buscador es capaz de usar lo que se escriba en él para filtrar las vacantes activas y mostrar las que contengan en alguno de sus campos la palabra que se busque. Básicamente hace búsqueda en tiempo real sobre todo el contenido de las vacantes activas y muestra las que contienen el texto exacto escrito en el buscador.

### Revisar dashboard con estadísticas
Al iniciar sesión, un Usuario registrado es redirigido a `dashboard.html` donde es capaz de ver una sección que indica:
- El número de postulaciones activas.
- El promedio de las puntuaciones de match, considerando las postulaciones asociadas a su correo y usuario.
- El estado del CV. Puede ser "Cargado" si ya tiene un CV en la base de datos, o "Pendiente" si no hay ningún CV asociado a su usuario y correo.

___
### Ver tabla de postulaciones
Al iniciar sesión, un Usuario registrado es redirigido a `dashboard.html` donde debajo del dashboard puede ver una tabla con sus postulaciones o la leyenda "No tienes postulaciones registradas todavía. Ver vacantes disponibles", con esto último siendo un hipervínculo para dirigir a la página `index.html` en donde se visualizan las vacantes.

Si se carga la tabla de las postulaciones se puede ver que esta consta de cinco columnas:
- **Vacante**: esta muestra el nombre de la vacante.
- **Fecha de postulación**.
- **Match %**: muestra el porcentaje total de match calculado al crear la postulación.
- **Estado**: muestra el estado de la postulación (recibida, bajo revisión, preseleciconado, entrevista programada, rechazada, contratado). (Todavía no se usan los estados más que recibida y rechazada).
- **Acciones**: 
    - Ver Vacante: Un botón que al pulsarlo muestra toda la información de la vacante.
    - Detalles del Match: Despliega una sección informativa que muestra el puntaje de coincidencia exacta, el puntaje de coincidencia semántica y el análisis hecho por la IA (si es que se pudo conectar al servicio de IA al realizar la postulación), incluyendo su opinión y un juicio de fortalezas y debilidades encontrados en el candidato a la postulación.
    - Cancelar Postulación.
En esta tabla se mostrarán máximo 3 postulaciones.
___
### Cancelar postulación
Sólo los Usuarios Registrados pueden hacer esto. Se puede realizar desde la página dashboard.html, en la tabla de postulaciones. En dicha tabla se encuentra la columna "Acciones", donde se encuentra el botón **"Cancelar"**. Al hacer click sobre este le preguntará si realmente quiere elimininar su postulación a la vacante. Si acepta, se eliminará su postulación y dispondrá de una ranura más para postularse a la vacante de su preferencia.

___
### Ver Vacantes (usuarios con rol Administrador y Reclutador)
Esto puede hacerse desde `jobs.html`.



**NOTA**
**NOTA**
**NOTA**
**NOTA**
Hasta aquí llegó la redacción del manual de usuario el 23/10/2026, 1:14am


## Preguntas Frecuentes (FAQ) y Soporte

### Usuarios registrados

#### Problemas con postulaciones
- Si en los "Detalles del match" de alguna postulación aparece que se pudo realizar el análisis con IA, si esta sigue abierta puede cancelar la postulación y volver a aplicar. Si la postulación está cerrada o vencida, puede ir al formulario de CV y "Guardar cambios" para intentar recalcular el match. Considere que la segunda opción puede afectar el puntaje de match de todas sus postulaciones si realiza cambios de verdad en la información de su CV.


Temas tentativos sujetos a cambios:
Visualización del procesamiento y normalización automática de habilidades (skills).
Pasos para crear, editar y dar de baja ofertas de empleo.
Definición de requisitos y competencias técnicas clave.
Motor de Matching y Análisis de IA:
Explicación del indicador de compatibilidad y la evaluación de sobrecalificación (over_ia_analysis).
Respuestas a dudas comunes sobre el comportamiento de la interfaz, subida de archivos o visualización de resultados.
Canales de contacto o soporte técnico en caso de incidencias.