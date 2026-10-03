# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).
Versionado semántico ([SemVer](https://semver.org/lang/es/)): `MAJOR.MINOR.PATCH`.

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
