Integración con la función Prepare de Serato DJ: Hallazgos técnicos

Funcionamiento del panel Prepare

En Serato DJ Pro la bandeja Prepare actúa como una lista temporal para preparar la siguiente canción.  Cuando el DJ encuentra una pista en su biblioteca que quiere reproducir más adelante puede enviarla a Prepare mediante la combinación Ctrl + P (o Cmd + P en Mac).  Las pistas se muestran en esa bandeja y, en cuanto se cargan en un deck, desaparecen automáticamente para evitar reproducirlas dos veces .  Serato permite deshacer la carga con Ctrl + Z/Cmd + Z y devolver el tema a Prepare .  Al cerrar la aplicación la lista se vacía y, aunque Serato 4.0 incluye una opción para mantener los temas en Prepare, la funcionalidad sigue siendo interna y no se guarda de forma persistente.

Falta de una API oficial

Serato no proporciona un SDK o API pública para manipular su biblioteca o modificar la lista Prepare desde aplicaciones externas.  Un hilo de Reddit resume esta realidad al señalar que Serato es un sistema cerrado y que para integrarse hay que asociarse con la compañía, mientras que otros programas como Virtual DJ sí exponen una API .  Por tanto, no existe un método documentado para que software externo añada o elimine canciones de la bandeja Prepare o que lea su contenido.

Serato Remotes y Bonjour

Serato sí dispone de una API de control remoto para aplicaciones oficiales como Serato Remote o herramientas de iluminación como SoundSwitch.  Esta API no está documentada públicamente y está limitada a socios autorizados.  En los foros de SoundSwitch se indica que, en Windows, es necesario instalar el software Bonjour para que el Remotes API permita que programas externos se conecten a Serato .  El mismo hilo aclara que esta conexión remota ofrece control sobre ciertos parámetros de reproducción pero no publica listas internas como Prepare, ni permite modificarlas .

Alternativas no oficiales

SSL‑API

Ante la ausencia de un SDK oficial, algunos desarrolladores han creado bibliotecas que interpretan los archivos internos de Serato.  El proyecto SSL‑API lee el archivo de historial binario que Serato genera en cada sesión y publica eventos cada vez que se carga o se descarga un tema.  Su documentación señala que esta biblioteca está pensada como un API no oficial para obtener datos de reproducción .  El uso típico consiste en instanciar la clase SslApi, registrar un servicio para recibir eventos como TrackLoadedMessage y TrackUnloadedMessage, y luego iniciar la API para que empiece a monitorizar el archivo de sesión.  Este servicio permite saber cuándo se carga una pista en un deck y recupera metadatos como BPM o tonalidad .  Aunque no da acceso directo a la bandeja Prepare, puede utilizarse para detectar si un tema de dicha lista ha sido cargado y así replicar la cola en otra aplicación.

Base de datos master.sqlite en Serato 4.0

A partir de Serato DJ Pro 4.0 la compañía abandonó los ficheros .crate y almacenó su biblioteca en un archivo SQLite (master.sqlite).  La plataforma de gestión Lexicon DJ explica que la versión 1.10 de Lexicon ofrece soporte completo para este nuevo formato y que Serato “ha pasado de su sistema de crates legado a una base de datos SQLite moderna” .  Esta base de datos guarda crates, playlists y su orden, pero Prepare sigue siendo una lista en memoria; no existe una tabla visible que represente sus elementos, de modo que no se puede modificar mediante consultas SQL.

Recomendaciones para integrar una “preparación”

* Considerar la ausencia de API: no hay un método oficial para interactuar con la bandeja Prepare; cualquier integración debe asumir que la lista es temporal y gestionada por Serato.
* Usar la Remotes API solo con autorización: la API de control remoto está orientada a aplicaciones oficiales y requiere Bonjour en Windows ; además, no expone la lista Prepare .
* Aprovechar bibliotecas no oficiales: proyectos como SSL‑API permiten escuchar eventos de carga y descarga de pistas leyendo el archivo de sesión  .  Esto no controla la bandeja, pero sí facilita replicar una cola de próximas canciones y sincronizarla con tu aplicación.
* Replicar la lista en la aplicación: dado que Prepare es solo una bandeja temporal, muchos DJs utilizan crates normales o listas inteligentes para organizar sus sets.  Una aplicación externa podría gestionar su propia lista de preparación, leer metadatos de Serato a través del archivo master.sqlite (para crates y tags) y utilizar eventos de carga para saber cuándo eliminar un tema de la cola.

Conclusión

La bandeja Prepare de Serato DJ es una herramienta pensada para la organización temporal de canciones durante una sesión.  No existe una API pública para acceder a ella, y su contenido no se guarda en la base de datos de la biblioteca.  Cualquier integración con Serato deberá partir de esta limitación y apoyarse en soluciones no oficiales como SSL‑API para vigilar eventos de reproducción, o recrear la funcionalidad de preparación en la propia aplicación.