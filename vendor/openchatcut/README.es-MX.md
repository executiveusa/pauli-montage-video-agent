<p align="center">
  <img src="public/openchatcut-icon.png" width="96" alt="OpenChatCut" />
</p>

<h1 align="center">OpenChatCut</h1>

<p align="center">
  <a href="README.md">English</a> · <a href="README_ZH.md">简体中文</a> · <strong>Español (México)</strong>
</p>

> Esta es una versión en español de México, resumida, del [README principal](README.md). Si algo no coincide, manda el README en inglés. El código y la documentación completa son del proyecto original: https://github.com/0xsline/OpenChatCut (AGPL-3.0-or-later).

## ¿Qué es OpenChatCut?

OpenChatCut es una alternativa de código abierto a ChatCut: un editor de video que junta **agentes conversacionales** y **edición profesional en línea de tiempo** en el mismo espacio de trabajo. Es un proyecto independiente de código abierto (AGPL) y no tiene relación con el producto comercial ChatCut.

**OpenChatCut = proyectos de video locales + línea de tiempo multipista + agentes de IA + MCP + exportaciones listas para producción.**

No se limita a generar un video que ya no se puede cambiar. Cada edición se escribe en pistas, clips, transiciones, subtítulos, efectos y medios reales dentro del proyecto. Puedes seguir editando a mano, deshacer y rehacer, guardar versiones o pasarle el proyecto a otro agente.

- **Nativo para agentes:** el agente integrado y los agentes externos por MCP comparten las mismas herramientas de edición.
- **Línea de tiempo real:** varias pistas de video y audio, transiciones, efectos, LUTs, zooms y fotogramas clave.
- **Edición guiada por la transcripción:** transcripción palabra por palabra, cortes a partir del texto, manejo de pausas, hablantes y subtítulos vinculados.
- **Generación y medios:** imágenes, video, voz, música, efectos de sonido y búsqueda de medios en línea.
- **Motion graphics y WebGL:** plantillas de movimiento editables, shaders personalizados, efectos visuales y transiciones.

## Inicio rápido

### Instaladores de escritorio

Descarga las versiones más recientes para macOS, Windows y Linux desde [GitHub Releases](https://github.com/0xsline/OpenChatCut/releases/latest). Son versiones tempranas. Los paquetes de macOS todavía no están firmados ni notarizados, así que el sistema puede pedirte aprobación manual la primera vez que los abras.

### Ejecutar desde el código fuente

Requiere Node.js 24.x y npm.

```bash
npm install
cp .env.example .env.local
npm run dev
```

Abre `http://localhost:5199`.

El editor necesita un [contexto seguro](https://developer.mozilla.org/es/docs/Web/Security/Secure_Contexts) del navegador: ábrelo en `http://localhost` o `http://127.0.0.1` en la computadora donde corre, o sírvelo por HTTPS. Si lo abres por HTTP desde otro dispositivo, el navegador desactiva Web Crypto, WebCodecs y el portapapeles.

Agrega a `.env.local` solo las credenciales de modelos o servicios de medios que realmente uses. Las funciones sin credenciales indican qué clave falta; la edición local de la línea de tiempo y los medios incluidos siguen funcionando.

> **En este repositorio** esta carpeta está incluida tal cual, sin instalar y fuera de los workspaces de npm. Para ejecutarla, trabaja dentro de `vendor/openchatcut` en una copia aparte y no desde la raíz del monorepo.

### Idioma de la interfaz

La interfaz está disponible en chino, inglés, italiano, ruso y español de México (`es`). El botón de idioma de la barra superior recorre los idiomas disponibles, y la primera vez se usa el idioma del sistema. Las cadenas no traducidas aparecen en inglés. Los diccionarios están en `src/i18n/dict/`; el texto original en chino funciona como llave, así que esas llaves en chino son intencionales.

### Autenticación del Agente integrado

- **Claves de API:** abre **Ajustes → Modelo del Agente**, elige un proveedor y guarda su clave de API y su modelo. Las claves se quedan en el servidor.
- **Suscripción de ChatGPT:** instala la CLI oficial de Codex y abre **Ajustes → Modelo del Agente → OpenAI · Codex**. La CLI oficial administra las credenciales.
- **Suscripción de Claude:** OpenChatCut no recolecta credenciales OAuth de Claude. Usa Claude Code por la conexión MCP local. El Agente integrado puede usar Anthropic con una clave de API.

El Agente integrado ejecuta el ciclo del modelo en el servidor local. Los cambios en la línea de tiempo siempre pasan por comandos validados y reversibles del editor.

## Uso con Codex y Claude Code (MCP)

OpenChatCut expone un endpoint MCP de HTTP en streaming. Agentes externos como Claude Code, Codex y Cursor comparten las herramientas de edición del agente integrado y pueden leer y editar el proyecto actual. Los pasos de conexión para cada cliente están en el [README en inglés](README.md#using-openchatcut-with-codex--claude-code) y en **Ajustes → Agentes externos (MCP)**.

### Protección del acceso MCP

Si expones tú mismo el endpoint MCP, configura:

```bash
OPENCHATCUT_MCP_TOKEN=tu-token
OPENCHATCUT_EDITOR_URL=https://tu-editor.example.com
```

Los clientes deben enviar `Authorization: Bearer <token>`. El puente actual está pensado para una sola persona en una sola computadora, no como servicio para varios usuarios.

## Datos y privacidad

- Los proyectos, el historial de chat y las versiones se guardan en el almacén local compartido en `~/.openchatcut`.
- Los medios del usuario se guardan en una carpeta local que puedes respaldar o migrar.
- Que una solicitud de IA salga de tu computadora depende de los servicios de modelos, generación o medios que configures.
- Las funciones en la nube sin configurar no afectan la línea de tiempo local ni la edición de medios existentes.
- Si expones MCP hacia afuera, configura un token de portador y limita el acceso de red al endpoint del editor.

## Modelo de seguridad

- Las claves de API solo están disponibles para la configuración del servidor; las credenciales de los proveedores nunca deben llegar al navegador mediante `VITE_`.
- La salida de los LLM, los paquetes de complementos, el código de las plantillas y lo que escribe el usuario se validan en los límites de confianza.
- El código de motion graphics y de shaders corre en un sandbox restringido.
- Los agentes modifican los proyectos solo mediante comandos de `EditorCore`, así que las ediciones se pueden rastrear y deshacer.
- MCP escucha solo en local por defecto.

## Licencia

OpenChatCut se distribuye bajo la [Licencia Pública General de Affero de GNU v3.0 o posterior](LICENSE). Los componentes y recursos de terceros siguen sujetos a sus propias licencias. Consulta también [NOTICE](NOTICE) para el origen y las modificaciones de esta copia.

## Contribuir

1. Crea una rama a partir de `main`.
2. Agrega una verificación ejecutable para la lógica que no sea trivial.
3. Ejecuta `npm test`, `npm run lint` y `npm run build` antes de hacer commit.
4. Abre un Pull Request e incluye capturas o evidencia de aceptación para los cambios de interfaz o de comportamiento del video.

Para reportar errores o pedir funciones, usa los [Issues de GitHub](https://github.com/0xsline/OpenChatCut/issues).
