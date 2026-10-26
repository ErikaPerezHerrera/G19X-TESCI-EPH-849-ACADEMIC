# Plurijob -  Manual de Usuario
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
- Generar vacantes mediante formulario manual.
- Generar vacantes mediante asistencia de IA.
- Generar vacantes reutilizando la información de otras vacantes.
- Publicar vacantes
- Cerrar vacantes sin eliminar postulaciones.
- Consultar vacantes activas y cerradas.
- Buscar y filtrar vacantes por texto, área, modalidad y estado.
- Reactivar vacantes cerradas o vencidas reutilizando sus datos.
- Ver candidatos que aplicaron a una vacante.
- Ordenar candidatos por puntuación de matching.
- Revisar candidatos con habilidades adicionales o posible sobrecalificación.
- Consultar el detalle del CV.
- Descartar candidatos sin eliminar los datos del CV.

### Administrador 
Es el rol que obtiene la primera persona que se registra.
#### Funciones:
- Las mismas funciones que un Reclutador.
- Registrar reclutadores.
- Archivar vacantes cerradas, eliminando postulaciones.

### Usuario casual
Es el rol que adquiere una persona al entrar a la página principal de la aplicación **sin iniciar sesión**.
#### Funciones:
- Crear un CV digital manualmente o usando la extracción de información de PDF asistida por IA.
- Listar y filtrar vacantes por texto clave en el contenido.
- Aplicar a una vacante como usuario casual, es decir, sin necesidad de registrarse en el sistema.
- Registrarse.

### Usuario registrado
Es el rol que adquiere una persona al registrarse en el sistema. Se diferencia de Reclutador porque este es registrado por un usuario Administrador.
#### Funciones:
- Crear un CV digital manualmente o usando la extracción de información de PDF asistida por IA.
- Listar y filtrar vacantes por texto clave en el contenido.
- Inicio de sesión con correo y contraseña.
- Aplicar a una vacante como usuario registrado (máximo 3 postulaciones simultaneas).
- Revisar el contenido de su CV digital.
- Revisar las estadísticas disponibles de su perfil.
- Revisar la información del análisis de match de las postulaciones asociadas a su perfil, así como el estado e información de sus postulaciones.
- Cancelar una postulación.

___

## Distribución de páginas
- **Reclutador** y **Administrador**: Al iniciar sesión tienen acceso a "Vacantes"/`jobs.html` (página que carga al iniciar sesión) y "Crear Vacante"/`publish.html` (accesible desde un botón en la parte superior derecha de la página).

- **Usuario registrado**: Al iniciar sesión tiene acceso a "Mis postulaciones"/`dashboard.html,`(página que carga al iniciar sesión) y "Mi CV"/`cv_profile.html`. Aún puede acceder a "Buscar Vacantes"/`index.html`, que ahora despliega los botones necesarios para navegar a las otras dos páginas.

- **Usuario casual**: Sólo tiene acceso a "Buscar vacantes"/`index.html` en su versión sin hipervínculos a otras páginas.
___

## Datos requeridos en la plataforma
- **Para registrarse**: Nombre completo (mayor a 10 caracteres), Correo electrónico, Contraseña (mínimo de 12 caracteres).
- **Para crear un CV**: Nombre completo, Correo electrónico, Número telefónico, Domicilio, Titulo profesional o Cargo actual, Habilidades técnicas, Habilidades blandas, Experiencia Laboral, Más Información.
- **Campos de una Vacante**: Título del puesto, Área o departamento, Típo de perfil, Modalidad, Ubicación, Descripción del puesto y Responsabilidades, Beneficios, Habilidades técnicas, Habilidades blandas, Fecha límite de recepción.
- **Estados de una Vacante**: Abierta, Vencida, Cerrada, Archivada.
- **Estados de una Postulación**: Sólo Enviada y Descartada por el momento.

___

## Registro, Acceso y Autenticación
La primera vez que el sistema es construido no cuenta con usuarios ni credenciales de ningún tipo. Por ello es necesario que a partir de `index.html`, den click en "Iniciar Sesión" para ir a `login.html`, ahí dar click en "Registrate aquí" para que los redirija a `signup.html`.

En `signup.html` se puede registrar cualquier persona mediante un formulario que pide un nombre de usuario, un correo y una contraseña que se va a encriptar. Si bien cualquiera puede registrarse, sólo el primer usuario que se registre obtendrá el rol **Administrador**; el resto de personas que se registren por este método serán **Usuario registrado**.

Los usuarios con rol **Reclutador** son registrados por el Administrador, nunca podrán registrarse por el método convencional.
Luego de ser registrados, **Administrador**, **Usuario registrado** y **Reclutador** pueden iniciar sesión dirigiendose a `index.html`, dando click en "Iniciar Sesión" para ir a `login.html`. Ahí se escribe en el formulario el correo y la contraseña con la que fueron registrados y dan click en "Iniciar sesión".

Después de iniciar sesión, cada que el usuario se desplaza entre páginas se valida la existencia del token JWT y su coincidencia con el que se le otorgó al usuario al iniciar la sesión. De esta forma se evita que con el cambio manual de ubicación de la página en la barra de URL del navegador, los usuarios puedan acceder a páginas cuando no han iniciado sesión. Al mismo tiempo también se corrobora que el usuario que inició sesión y el que está en la página sean el mismo y tengan el rol adecuado para la página a la que quieren acceder. Así los candidatos no pueden acceder a las páginas de los reclutadores y viceversa.

Cualquier intento de acceso invalidado a páginas protegidas mediante la edición de la dirección en barra de URL resultará en la redirección a `login.html`.

El token JWT tiene una duración de 8 horas.

**Advertencia**: la empresa debe realizar el primer registro inicial inmediatamente al desplegar el sistema por primera vez, para evitar que cualquier usuario externo tome accidentalmente el rol de Administrador si la plataforma se expone públicamente sin protección previa.

**Nota**: Al registrarse un Usuario Registrado, se envía un correo notificatorio.
___

## Funciones de Usuarios Casual Y Registrado

### Creación de un CV digital
Esto puede hacerse desde `index.html` para **Usuario Casual** y desde `cv_profile.html` para **Usuario Registrado**.

**Notas:** Dado que el sistema esta diseñado para la contratación de personal en una empresa, sólo puede haber un CV por correo, esto con el fin de evitar que la misma persona aplique para dos vacantes en departamentos distintos. Sin embargo, no se le niega la posibilidad de aplicar a 3 vacantes y editar el contenido de su CV bajo su consentimiento.

#### Mediante el botón "Buscar Vacantes" en `index.html`:
Este medio para crear un CV puede ser usado por el Usuario casual.
1. Da click sobre el botón **"Postularme"** situado en la tarjeta de una vacante.
2. Se despliega un botón con la leyenda **"Elegir archivo"** para abrir el selector de archivos, así como un formulario.

    *Si lo desea puede generar la información del CV llenando el fomulario manualmente. Si quiere digitalizar la información de un CV en formato PDF seleccione uno con el selector de archivos.*

3. Si seleccionó un archivo para extraer su información, de click en el botón **"Extraer información con IA"**. Se llenará automaticamente el formulario mencionado. Si el servicio de IA está configurado y disponible o no lo está, aparecerá una sección que nos afirma o niega la participación de la IA en el enriquecimiento de la información extraída.

#### Mediante el botón "Mi CV" en `cv_profile.html`:
Está situado en el navegador en la parte superior de la página y se abre solo a usuarios que iniciaron sesión con rol "Usuario registrado".

1. En esta página se encuentra un botón con la leyenda **"Elegir archivo"** para abrir el selector de archivos, así como un formulario y una barra de progreso que se llena según haya contenido o no en ciertos campos del formulario. 

    *Si lo desea puede generar la información del CV llenando el formulario manualmente. Si quiere digitalizar la información de un CV en formato PDF seleccione uno con el selector de archivos.*

2. Si seleccionó un archivo para extraer su información, de click en el botón **"Extraer y autocompletar"**. Se llenará automaticamente el formulario mencionado. Si el servicio de IA está configurado y disponible o no lo está, aparecerá una sección que nos afirma o niega la participación de la IA en el enriquecimiento de la información extraída.
___

### Postulación y Guardado de CV
#### Guardado de CV y Creación de Postulación en "Buscar Vacantes"/`index.html` (Usuario Casual):
Relacionando el proceso de extracción de información del PDF, el **Usuario Casual** puede revisar la información y editarla antes de dar click en **"Enviar postulación"**. 
1. Da click en **"Enviar postulación"**. Aparecerá una advertencia que informa que si ya habia una postulación asociada al mismo correo ingresado podría afectar su visibilidad en dichas postulaciones. Puede elegir entre continuar o cancelar la postulación.

2. Si da click en **"Continuar"**, el sistema se tardará un poco en mostrar un mensaje que confirme el guardado exitoso del CV o un error en el proceso de guardado. El retraso para mostrar la alerta se debe al proceso de comprobación y guardado de habilidades técnicas y blandas, y el cálculo de matching en las postulaciones relacionadas con el correo del usuario.

#### Guardado de CV en "Mi CV"/`cv_profile.html` (Usuario Registrado):
Relacionando el proceso de extracción de información del PDF y continuando con el guardado de CV, el **Usuario Registrado** puede revisar la información y editarla antes de dar click en **"Guardar cambios"**.
1. Da click en **"Guardar cambios"**. Aparecerá una advertencia que informa que si ya habia una postulación asociada al mismo correo ingresado podría afectar su visibilidad en dichas postulaciones. Puede elegir entre continuar o cancelar la postulación.

2. Si da click en **"Continuar"**, el sistema se tardará un poco en mostrar un mensaje que confirme el guardado exitoso del CV o un error en el proceso de guardado. El retraso para mostrar la alerta se debe al proceso de comprobación y guardado de habilidades técnicas y blandas, y el cálculo de matching en las postulaciones relacionadas con el correo del usuario.

Si realizó cambios en la información del formulario (ya sea que sea creación del primer CV asociado a la cuenta o cambios en información del CV encontrado en la base de datos), si cambia de página sin presionar **"Guardar cambios"** estos no se aplicarán.

#### Postulación en "Buscar Vacantes"/`index.html` (Usuario Registrado):

1. Da click sobre el botón **"Postularme"** (sobre una vacante).

2. Aparecerá una advertencia que informa que si ya habia una postulación asociada al mismo correo ingresado podría afectar su visibilidad en dichas postulaciones. Puede elegir entre continuar o cancelar la postulación. Si da click en **"Continuar"**, el sistema se tardará un poco en mostrar un mensaje que confirme el guardado exitoso del CV o un error en el proceso de guardado. El retraso para mostrar la alerta se debe al proceso de comprobación y guardado de habilidades técnicas y blandas, y el cálculo de matching en las postulaciones relacionadas con el correo del usuario.

__

**Nota:** el CV asociado a un correo de un usuario casual tiene una vigencia de 12 meses. Luego de ese tiempo se elimina de la base de datos. Si en algún momento se registra un usuario con el correo asociado a ese CV, se elimina la fecha de vencimiento. Todos los candidatos tienen un máximo de 3 postulaciones, por lo que si se intenta tener una cuarta esta no se podrá realizar. Al crearse una postulación, se envía un correo notificatorio que incluye el porcentaje del match obtenido al postularse.

___

### Consultar CV guardado
Si el usuario registrado cuenta con un CV guardado en la base de datos, su información se mostrará al iniciar sesión y dirigirse a la página `cv_profile.html` mediante el botón **"Mi CV"** ubicado en la parte superior derecha. Un Usuario casual no puede consultar la información de CV a no ser que se registre.

____
### Ver Vacantes
Esto puede hacerse desde "Buscar Vacantes"/ `index.html`.
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

___
### Buscar Vacantes activas
En "Buscar Vacantes"/`index.html` el buscador es capaz de usar lo que se escriba en él para filtrar las vacantes activas y mostrar las que contengan en alguno de sus campos la palabra que se busque. Básicamente hace búsqueda en tiempo real sobre todo el contenido de las vacantes activas y muestra las que contienen el texto exacto escrito en el buscador.

___
### Revisar dashboard con estadísticas 
Al iniciar sesión, un Usuario registrado es redirigido a "Mis postulaciones"/`dashboard.html` donde es capaz de ver una sección que indica:
- El número de postulaciones activas.
- El promedio de las puntuaciones de match, considerando las postulaciones asociadas a su correo y usuario.
- El estado del CV. Puede ser "Cargado" si ya tiene un CV en la base de datos, o "Pendiente" si no hay ningún CV asociado a su usuario y correo.

___
### Ver tabla de postulaciones
Al iniciar sesión, un Usuario Registrado es redirigido a "Mis postulaciones"/`dashboard.html` donde debajo del dashboard puede ver una tabla con sus postulaciones o la leyenda "No tienes postulaciones registradas todavía. Ver vacantes disponibles", con esto último siendo un hipervínculo para dirigir a la "Buscar Vacantes"/`index.html` en donde se visualizan las vacantes.

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
Sólo los Usuarios Registrados pueden hacer esto. Se puede realizar desde la página dashboard.html, en la tabla de postulaciones. En dicha tabla se encuentra la columna "Acciones", donde se encuentra el botón **"Cancelar"**. Al hacer click sobre este le preguntará si realmente quiere elimininar su postulación a la vacante. Si acepta, se eliminará su postulación y dispondrá de una ranura más para postularse a la vacante de su preferencia. Se enviará un correo notificando al usuario su acción.

___
## Funciones de Administrador y Reclutador

### Ver Vacantes 
Cuando inician sesión se muestra la página "Vacantes"`jobs.html`, donde se muestran un buscador en la parte superior y tres selectores donde se puede cambiar las vacantes que se ven según su estado. Todas las vacantes mostradas tienen el formato de una tarjeta informativa que contiene:
- Título de la vacante
- Área o Departamento
- Modalidad
- Descripción del trabajo y responsabilidades
- Beneficios
- Habilidades técnicas requeridas

**Nota:** La información se distribuye en espacios pequeños, por lo que podría mostrarse entrecortada.

Dependiendo del selector de vacantes por estado las tarjetas de las vacantes cuentan con diferentes botones de acción: 
- **Ver**: Al pulsarlo se muestra la información completa de la vacante. Incluye la información listada arriba más ubicación y habilidades blandas y fecha de expiración (si es que tiene).
- **Candidatos**: Permite ver una lista de los candidatos postulados a la vacante.
- **Cerrar**: Permite cerrar la vacante.
- **Reabrir**: Permite reabrir una vacante que fue cerrada.
____
### Buscar Vacantes
En "Vacantes"/`jobs.html` el buscador es capaz de usar lo que se escriba en él para filtrar las vacantes y mostrar las que contengan en alguno de sus campos la palabra que se busque. Básicamente hace búsqueda en tiempo real sobre todo el contenido de las vacantes y muestra las que contienen el texto exacto escrito en el buscador.

Este buscador es sensible al selector de estado de vacantes. Por ejemplo, si se está en la sección de "Vacantes cerradas" y se escribe texto en el buscador se mostraran en la sección las vacantes cerradas que contengan texto iguaal al que se busca.

___
### Administración de Candidatos
Al pulsar el botón "Candidatos" se abre una lista de candidatos postulados a la vacante. Además sobre cada postulación se muestran tres botones:
- **Ver CV**: Despliega la información del CV del candidato postulado. Provoca que se envíe un correo al candidato acerca de que su CV ha sido visto y el cambio de estado de su postulación (postulación recibida--->postulación bajo revisión).
- **Detalles del Match**: Despliega una sección informativa que muestra el puntaje de coincidencia exacta, el puntaje de coincidencia semántica y el análisis hecho por la IA (si es que se pudo conectar al servicio de IA al realizar la postulación), incluyendo su opinión y un juicio de fortalezas y debilidades encontrados en el candidato a la postulación.
- **Botón cambiante Programar Entrevista/Contratar**.
- **Descartar**: Permite al Reclutador o Administrador eliminar una postulación.
- ***Ver Sobrecalificado**: Este botón solo se muestra si se detectó que el candidato está sobrecalificado para la vacante. Despliega las razones sobre los cuales se basó el sistema para hacer tal declaración.*

Además se puede ver un botón de filtro que permite ordenar a los candidatos por Match total, Coincidencia exacta, Coincidencia semántica, Otras Habilidades. Todos los filtros se aplican de mayor a menor, a excepción del "Otras Habilidades", el cual muestra a los candidatos ordenados por match total, invertidos.

__
### Programar entrevista
Cuando el texto del botón cambiante indica "Programar entrevista", al pulsarlo muestra un mensaje que busca la confirmación. Si acepta, se enviará un correo al candidato para decirle que tiene que estar pendiente porque alguien se comunicará con él para programar la entrevista. El estado de la postulación pasa a "entrevista programada".

**Atención**: El reclutador se tiene que poner en contacto directamente con el candidato para agendar la entrevista. Para obtener información de contacto revise el CV del candidato.

__
### Contratar
Si el botón dice "Contratar" se lanzará un mensaje buscando confirmación. Si acepta, la vacante se cerrará y comenzará el periodo de prueba para el candidato cuya postulación paso a estado "contratado". No se borra ninguna postulación. Se envía un mensaje notificatorio al candidato contratado, y otro a los demás candidatos postulados informando que en un lapso de 30 días o menos su postulación será eliminada y podrán participar en otro proceso de selección.
___
### Descartar candidato
Se trata de la eliminación directa de la postulación del candidato. Siguiendo con la Administración de Candidatos, al pulsar sobre el botón **Descartar** se muestra un mensaje que pide una razón de descarte (opcional) y la confirmación. Si se acepta, la postulación del candidato será eliminada permanentemente y el candidato dispondrá de una ranura más para hacer postulaciones. Se enviará al candidato un correo notificatorio con o sin el motivo del descarte.

___
### Reabrir vacante
Al pulsar el botón **"Reabrir"** sobre una vacante, todos los datos de la vacante serán mostrados en el formulario de "Publicar vacante"/`publish.html`. En este caso no se podrá editar la información de la vacante, sólo se permite seleccionar una fecha de vencimiento (opcional). Al presionar el botón **"Guardar y Reabrir"** la vacante cambia su estado a Activa y ahora puede verse en el selector de vacantes activas y en el panel de búsqueda de vacantes al que Usuario Casual y Usuario Registrado pueden acceder. Se enviará un correo notificatorio a los candidatos para que estén pendientes de su proceso de selección.

____
### Cerrar Vacante
Si se pulsa el botón **"Cerrar"** sobre una vacante abierta/vencida se pide una confirmación. Al aceptar, el estado de la vacante pasará a "Cerrada" y podrá visualizarse desde la sección de vacantes cerradas. Se enviará un correo notificatorio a los usuarios, informando que en 30 días o menos su postulación será eliminada.

___
### Publicar Vacante
A esta función se puede acceder presionando el botón **"Crear Vacante** ubicado en la parte superior derecha de la página **"Vacantes"**`jobs.html`. Al dar click en este botón se dirigira a la página para crear vacantes y se mostrarán en pantalla tres opciones. Independientemente de cual se tome, para publicar la vacante todos los campos del formulario posterior deben estar llenos y la fecha de vencimiento es opcional o mayor a la fecha de creación de la vacante.

En el formulario se presentan dos botones: uno para limpiar los campos de formulario y otro para **"Guardar y publicar"** la vacante. Si la vacante se publica exitosamente se mostrará un mensaje en la pantalla y lo redigirá a **"Vacantes"**`jobs.html`.

- **Redactar vacante**: se muestra el formulario para introducir los datos de la vacante.
- **Redactar con IA**: se muestra un campo de texto donde se escribe la instrucción de creación de vacante a la IA, y el formulario para introducir los datos de la vacante.
- **Reutilizar plantilla**: se muestra un panel con tarjetas informativas de todas las vacantes existentes, con un botón para **"Ver"** que muestra todos los datos de la vacante, y otro para **"Seleccionar"** que permite tomar la información de los campos de la vacante plantilla y colocarlos en el formulario para editarlos.

______
## Funciones Exclusivas de Administrador
El Administrador, al igual que el Reclutador, tiene acceso a "Vacantes y "Publicar vacantes" así como todas es capaz de ejecutar todas las funciones descritas hasta el momento en el apartado "Funciones de Administrador y Reclutador. Sin embargo hay dos funciones disponibles para el administrador. Ambas funciones son usables desde "Vacantes"/`jobs.html`.

### Registrar Reclutador
En la parte superior de la página se encuentra el botón **"Crear Reclutador"**. Al dar click en él se despliega un pequeño formulario donde el administrador ingresa los datos para crear el usuario del reclutador. Al dar click en **"Guardar Reclutador"** se guarda el usuario creado y se le asigna el rol Reclutador.

### Archivar Vacantes cerradas
Al ver las vacantes cerradas, el administrador puede encontrar sobre las tarjetas de vacantes el botón **"Archivar"**. Al dar click se pide la confirmación para archivar la vacante y eliminar todas las postulaciones relacionadas a la vacante. Si acepta, la vacante ya no podrá ser vista en "Vacantes"/`jobs.html`. Al archivar la vacantes se envía un correo notificatorio a los candidatos avisando que su postulación fue eliminada y disponen de una ranura más para empezar otro proceso de selección.

Sin embargo, los datos de la vacante pueden ser vistos desde "Crear Vacante"/`publish.html` mediante la función **"Reutilizar plantilla"**.

____

## Otras funciones
* **Archivado automático**: Si una vacante cerrada no es archivada, a los 30 días de ser cerrada se cambia el estado a "stored" (archivada) y se eliminan las postulaciones. Se usa un plazo de 30 días a partir de la asignacion de estado "cerrada" para que si al administrador o reclutador se les olvida archivarla los candidatos puedan participar nuevamente en procesos de selección. Mientras tanto esos 30 días sirven como periodo de prueba en caso que se haya contratado un candidato. Si se reabre la vacante, los candidatos siguen enlistados y listos para continuar con su proceso.
* **Chequeo de vencimiento**: Se comprueba que las vacantes con fecha límite no estén vencidas. En ese caso, su estado pasa a "expired" (vencida). Pueden reabrirse, y no es el mismo estado que "closed" (cerrada) o "stored" (archivada).

____
## Preguntas Frecuentes (FAQ) y Soporte
### Preguntas
- **¿La interfaz es responsiva (se ajusta a todos los tamaños de página)?** 
    **Respuesta**: Si.
- **¿El sistema cuenta con envío de correos notificatorios sobre el estado de la postulación?** 
    **Respuesta**: No, solo simulación de estos. Fecha del 26/10/2026
- **¿Cómo puedo ver el resultado de mis postulaciones?** 
    **Respuesta**: Para ver el resultado de tus postulaciones debes registrarte en el sistema para poder acceder a la tabla de postulaciones que realizaste. Ahí mismo encontrarás el análisis.
- **¿Puedo subir más de un CV?** 
    **Respuesta**: No. El sistema guarda una sola versión de tu CV asociado al correo que se cargó en el CV.
- **¿Puedo usar un archivo tipo Word o .docs para extraer su información?** 
    **Respuesta**: No. El extractor solo acepta archivos en formato PDF.

### Problemas
#### Problemas con postulaciones
- Para el usuario registrado, si en los "Detalles del match" de alguna postulación aparece que no se pudo realizar el análisis con IA, si esta sigue abierta puede cancelar la postulación y volver a aplicar. Si la postulación está cerrada o vencida, puede ir al formulario de CV y "Guardar cambios" para intentar recalcular el match. Considere que la segunda opción puede afectar el puntaje de match de todas sus postulaciones si realiza cambios de verdad en la información de su CV.

#### Problemas con guardado de CVs
- El texto de la experiencia laboral debe tener mínimo 50 caracteres para guardarse. Esto se debe a que debe haber algo de información con la que se pueda hacer el cálculo del match.

#### Problemas con publicación de vacantes
- El texto de la descripción del trabajo debe tener mínimo 70 caracteres para guardarse. Esto se debe a que debe haber algo de información con la que se pueda hacer el cálculo del match.

## Notas finales
Hasta el 26/10/2026 el sistema simula el envio de los correos. Si usted quisiera notificar a los candidatos sobre el estado de sus postulaciones o las vacantes, debe comunicarse directamente con él por otros medios. Aún así se recomienda al reclutador usar los botones que ofrece el sistema para ejecutar un ciclo de vida correcto de las vacantes y postulaciones.