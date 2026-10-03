# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).
Versionado semántico ([SemVer](https://semver.org/lang/es/)): `MAJOR.MINOR.PATCH`.

## [1.2.1] — 2026-10-03

Pequeñas incongruencias que quedaron tras mover el panel de administración
a la SPA en 1.2.0.

### Arreglado
- Los chips rápidos ("Toda la música/Favoritas/Más escuchadas") y la barra
  de búsqueda seguían visibles en Artistas/Álbumes/Administración, donde no
  pintan nada — y escribir en el buscador ahí sacaba a la fuerza de esa
  vista. Ahora se ocultan junto con el resto de controles de biblioteca.
- Añadir una canción con el botón "+" mientras se veía Artistas/Álbumes/
  Administración sustituía silenciosamente esa vista por la lista de
  canciones. Ahora solo refresca la vista si se está viendo la biblioteca.

## [1.2.0] — 2026-10-03

### Arreglado
- **La música ya no se corta al entrar en "Administración"**: el panel de
  administración era una página aparte (`<a href>` con recarga completa, que
  destruía el reproductor de audio). Ahora es una vista más dentro de la SPA,
  igual que Artistas/Álbumes — navegar por el menú nunca recarga la página.
- **PWA en iOS**: faltaban las meta tags de Apple (`apple-mobile-web-app-capable`
  y similares); sin ellas, la app instalada desde "Añadir a pantalla de inicio"
  se abría dentro de Safari con barra de URL en vez de a pantalla completa.
- **Notch / Dynamic Island**: la barra superior, el menú lateral y el botón de
  cerrar del reproductor a pantalla completa ahora respetan las zonas seguras
  (`safe-area-inset`) en iPhones con notch.
- **Seek de audio offline roto tras cachear**: el service worker guardaba la
  respuesta parcial (`206`) de la primera petición de `Range` tal cual; al
  buscar otro punto de la canción servía el tramo equivocado porque
  `Cache.match()` no distingue por cabecera `Range`, solo por URL. Ahora el
  service worker cachea siempre el fichero completo y recorta el rango
  correcto él mismo.
- `theme-color` ya se actualiza al cambiar de tema claro/oscuro (antes se
  quedaba fijo en oscuro, desentonando con la barra de Chrome en Android).
- Lista de precaché del service worker desincronizada de la versión real de
  los assets (`?v=4` cuando ya íbamos por `v=11`); ahora solo precachea
  archivos sin versión en la URL y el resto se cachea solo al primer uso.

### Añadido
- `id` y `description` en `manifest.json`.

## [1.1.0] — 2026-10-03

### Añadido
- Gráfico de historial de estrellas de GitHub en el README.
- Enlace al repositorio de GitHub al pie del menú lateral.

### Cambiado
- El menú de usuario (avatar, rol, cerrar sesión) se movió del desplegable de la
  esquina superior derecha a la parte inferior del menú lateral, junto con el
  enlace de administración y el de GitHub, dejando la barra superior más limpia.

## [1.0.0] — 2026-10-03

Primera versión versionada de Sonara.

### Cambiado
- Migración completa del backend de Django a **FastAPI** + SQLAlchemy 2.0, manteniendo
  toda la funcionalidad (login, panel de administración, biblioteca, descarga vía
  yt-dlp, streaming con `Range` HTTP, favoritos, contador de reproducciones).
- Sesiones firmadas (`itsdangerous`) y CSRF por token de sesión en vez del middleware
  de Django. Hash de contraseñas PBKDF2-SHA256 compatible con el formato de Django
  (los usuarios existentes no necesitan resetear su contraseña).

### Añadido
- Menú lateral desplegable (botón hamburguesa) en móvil y escritorio, con opción de
  colapsarlo en escritorio (se recuerda la preferencia).
- Vistas nuevas de **Artistas** y **Álbumes**, con navegación en profundidad hacia la
  lista de canciones de cada uno.
- Número de versión visible al pie del menú lateral.

### Arreglado
- Botón de reproducir con un color plano (mate) consistente en tema claro y oscuro,
  en vez de blanco fijo.
- Barra de progreso del reproductor (`mini-seek`) ya no muestra el track nativo
  blanco del navegador por encima del degradado personalizado.
