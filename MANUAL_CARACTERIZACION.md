# Manual del Sistema — Caracterización y Analítica Académica
**IU Digital de Antioquia · Plataforma Analítica Institucional**
Versión 1.0 · Actualizado: Feb 2026

---

## 1. Descripción general

**Caracterización y Analítica Académica** es la plataforma institucional de la IU Digital de Antioquia para la gestión, caracterización, seguimiento académico y georreferenciación de la totalidad de la comunidad estudiantil. La plataforma opera exclusivamente sobre **datos reales institucionales** cargados desde archivos Excel oficiales.

**Objetivos principales**
- Centralizar la caracterización sociodemográfica, académica y territorial de todos los estudiantes.
- Ofrecer dashboards en tiempo real por facultad, programa, docente, grupo y estudiante.
- Detectar tempranamente estudiantes en **riesgo académico** y en **alerta primer nivel**.
- Georreferenciar la matrícula a nivel de municipio (DIVIPOLA – DANE) para lecturas territoriales.
- Generar **insights con Inteligencia Artificial** (Gemini / GPT) sobre datos agregados.
- Gestionar cargas masivas de datos con trazabilidad, backups y rollback.

**Stack técnico**
- Frontend: React 18 + Tailwind + Shadcn UI + Recharts + React‑Leaflet.
- Backend: FastAPI (Python 3.11) + Motor (MongoDB async).
- Base de datos: MongoDB.
- IA: Google Gemini (`gemini-3.6-flash`) y OpenAI GPT‑4o vía Emergent LLM Key.
- Correo: SMTP Gmail con App Password (o Gmail API OAuth).

---

## 2. Roles y control de acceso (RBAC)

El sistema implementa **cinco roles jerárquicos** con permisos estrictos.

| Rol | Alcance de datos | Módulos accesibles |
|---|---|---|
| 🔴 **Superadmin** | Toda la institución | Todos + Administración + Configuración |
| 🔵 **Dirección** | Toda la institución | Dashboards, Caracterización, Insights, Cargas, Grupos, Administración |
| 🟣 **Decano** | Su facultad | Dashboards filtrados a su facultad, Grupos, Caracterización |
| 🟢 **Coordinador** | Su programa | Dashboards filtrados a su programa, Grupos, Caracterización |
| 🟡 **Profesor** | Sus grupos asignados | Mi Panel (Docente), sus grupos y estudiantes |

**Regla institucional de credenciales (feb 2026):**
- **Docentes:** usuario = **cédula**, contraseña inicial = **cédula**, con `must_change_password = true`.
- **Personal administrativo:** usuario = **correo institucional**, contraseña gestionada por Admin.
- El backend acepta cédula (numérica) **o** correo en el login. Cascada: numérica → busca por documento; texto → busca por email.

**Descarga de datos:** Todos los roles pueden descargar únicamente los datos a los que tienen acceso por su rol. Un decano no puede descargar información de otra facultad. Existe un flag `download_enabled` por usuario que el Superadmin puede desactivar.

---

## 3. Módulos funcionales

### 3.1 Autenticación e Inicio (`Login.jsx`)
- Pantalla institucional dividida (formulario a la izquierda + héroe con imagen a la derecha).
- Muestra estadísticas globales en vivo: **estudiantes matriculados**, **programas**, **municipios cubiertos**.
- Enlace de recuperación asistida (contactar administrador).
- Endpoint: `POST /api/auth/login` → devuelve JWT y datos de usuario.
- Cambio de contraseña obligatorio en primer ingreso (`ChangePassword.jsx`).

### 3.2 Mi Panel
- Vista contextual según rol.
- Para Profesores redirige a **Docente**; para Decanos/Coordinadores/Dirección/Superadmin, a **Ejecutivo**.

### 3.3 Ejecutivo — Dashboard institucional (`Executive.jsx`)
Panorama global con KPIs y gráficos:
- **KPIs principales:** total estudiantes, matriculados vigentes, promedio general, programas, facultades, avance curricular promedio.
- **Caracterización especial:** Vivienda rural, Víctimas del conflicto, Grupo vulnerable, Discapacidad.
- **Histórico comparativo:** promedio del periodo actual vs. periodo anterior, variación, aprobación (%).
- **Gráficos:** estudiantes por programa (barras horizontales), género (donut), edad (histograma), estrato (barras), zona (residencia).
- Descargas: Excel del dashboard, CSV, Base completa de estudiantes.
- Endpoint: `GET /api/dashboards/executive?facultad_id=&programa_id=&...`

### 3.4 Caracterización sociodemográfica (`Caracterizacion.jsx`)
Vista profunda de variables no académicas:
- Género, edad, estado civil, tipo de documento.
- Vivienda (rural/urbana/semirrural), estrato socioeconómico.
- Víctimas del conflicto, grupo étnico, discapacidad, jefatura del hogar.
- Situación laboral, nivel educativo previo, personas a cargo.
- Todo cruzable por filtros globales (facultad, programa, periodo).
- Endpoint: `GET /api/caracterizacion/dashboard/{scope}` y `GET /api/caracterizacion/students`

### 3.5 Académico (`Academic.jsx`)
Analítica de rendimiento:
- **Promedio general** calculado sin materias de extensión ni inglés fuera de la malla.
- **Estudiantes en riesgo académico:** nivel ≥ 2 con promedio bajo o materias reprobadas.
- **Alerta primer nivel:** nivel ≤ 1 con notas 0 (datos incompletos o inicio de trayectoria) — **separado** del riesgo académico.
- Distribución de notas por franjas (0‑2, 2‑3, 3‑4, 4‑5).
- Top programas por promedio, materias con mayor reprobación.
- Endpoint: `GET /api/dashboards/academic` y `GET /api/dashboards/en-riesgo?tipo=academico|primer_nivel|all`.

### 3.6 Territorial (`Territorial.jsx`) — Georreferenciación
- Mapa Leaflet con marcadores agregados por municipio.
- Cada municipio mapeado por su **código DANE (DIVIPOLA)** → coordenadas GPS.
- Filtros: departamento, zona, programa, facultad.
- Búsqueda por municipio y foco automático en el mapa.
- Manejo de **homónimos** (p. ej. Argelia en Cauca vs. Antioquia): la búsqueda cruza municipio + departamento.
- Cobertura actual: **99.7%** de estudiantes con coordenadas asignadas.
- Endpoint: `GET /api/dashboards/territorial`.

### 3.7 Histórico (`Historical.jsx`)
- Serie temporal de matrícula, promedio, aprobación por periodo (2023‑1 → 2026‑1).
- Comparativos entre facultades y programas a lo largo del tiempo.
- Endpoint: `GET /api/dashboards/historical`.

### 3.8 Insights IA (`Insights.jsx`)
Análisis inteligentes generados por IA sobre datos agregados (nunca datos personales):
- Ámbitos: **Ejecutivo**, **Académico**, **Territorial**, **Histórico**.
- Pregunta libre opcional para orientar el análisis.
- Motor: Gemini `gemini-3.6-flash` (o GPT‑4o si el Superadmin lo cambia en Configuración).
- Endpoint: `POST /api/ai/insights`.
- Complementos IA:
  - `POST /api/ai/docente/alerta-estudiante` → plan de intervención personalizado por estudiante.
  - `POST /api/ai/docente/resumen-grupo` → resumen y focos de un grupo específico.

### 3.9 Cargas Excel (`Upload.jsx`) — Gestión de datos
Panel para ingestar los tres archivos maestros del sistema.

**Plantillas descargables** (con cabeceras + fila de ejemplo):
- Estudiantes → `GET /api/uploads/template/estudiantes` → `plantilla_estudiantes.xlsx`
- Notas históricas → `GET /api/uploads/template/notas` → `plantilla_notas.xlsx`
- Docente–Materia → `GET /api/uploads/template/docente_materia` → `plantilla_docente_materia.xlsx`

**Flujo de carga:**
1. Descargar plantilla y completarla con los datos institucionales.
2. Subir el `.xlsx` → `POST /api/uploads/preview` → previsualiza cambios sin persistir.
3. Confirmar → `POST /api/uploads/ingest` → persiste con `upload_id` para rollback.
4. En caso de error → `POST /api/uploads/rollback/{upload_id}` restaura el estado anterior.

**Refresh completo:** `POST /api/uploads/full-refresh` reprocesa todos los cálculos derivados (promedio académico, alertas, geocoding) sin borrar datos originales.

**Descarga de base:** Superadmin/Dirección pueden descargar toda la base actual con filtros aplicados.

### 3.10 Grupos (`Grupos.jsx`)
- Listado de grupos activos por periodo con: código, materia, docente, número de estudiantes, promedio del grupo.
- Filtros por facultad, programa, docente, periodo.
- Detalle de cada grupo → vista completa de estudiantes matriculados con nota vigente.
- Endpoint: `GET /api/admin/grupos` y `GET /api/admin/grupos/{codigo_grupo}`.

### 3.11 Docente (`Docente.jsx`) — Mi Panel del profesor
Vista exclusiva del docente:
- **KPIs personales:** grupos asignados, total estudiantes, promedio general de sus grupos, en riesgo académico, alerta primer nivel.
- Selector de grupo (dropdown).
- Tabla de estudiantes con: cédula, nombre, programa, nivel, promedio, nota vigente, alertas (semáforo).
- Botón **"IA"** por estudiante → alerta temprana personalizada (académico o de acompañamiento según el nivel).
- Botón **"Resumen IA del grupo"** → análisis agregado del grupo.
- Descarga: vista del grupo actual en Excel.
- Endpoint: `GET /api/dashboards/docente/grupo/{codigo_grupo}/vista`.

### 3.12 Administración (`Admin.jsx`)
Sólo Superadmin y Dirección.

**Tabs disponibles:**
- **Usuarios:** listar, crear, editar, eliminar, activar/desactivar, resetear contraseña, activar/desactivar descarga.
- **Catálogos:** editar Facultades, Programas, Materias, Docentes.
- **Docente–Materia:** asignación masiva por periodo. Si el docente no existe se crea con rol `profesor` y contraseña = cédula.
- **DIVIPOLA:** administrar el catálogo de municipios (agregar códigos DANE personalizados).
- **Facultades — Ficha detalle:** vista consolidada por facultad con métricas y edición inline.
- **Backups y estadísticas:** `GET /api/uploads/backup-stats` y descarga por colección.

### 3.13 Configuración (`Configuracion.jsx`)
Sólo Superadmin.

- **SMTP Gmail** (App Password) para envío institucional de credenciales.
- **Gmail API OAuth** (opcional, deshabilitado por defecto).
- **Proveedor de IA:** Google (Gemini) o OpenAI (GPT). API key propia o Emergent LLM Key.
- **Envío de credenciales:** individual (`POST /api/config/send-credentials/{user_id}`) o masivo (`POST /api/config/send-credentials-bulk`).
- **Reset masivo de docentes:** `POST /api/config/reset-initial-passwords` restaura la regla "cédula = usuario = contraseña" para los 399 docentes.
- **Descarga de credenciales iniciales:** `GET /api/config/initial-credentials.xlsx`.

---

## 4. Reglas de negocio clave

### 4.1 Cálculo del promedio académico
- Se excluyen las materias de **extensión** y de **inglés fuera de la malla** del programa del estudiante.
- Solo se consideran notas del periodo o del histórico según el dashboard.
- Al hacer `full-refresh`, el sistema recomputa el promedio para los 13.194 estudiantes con matrícula vigente.

### 4.2 Alertas académicas (separadas)
| Tipo | Condición | Interpretación |
|---|---|---|
| **Riesgo académico** | Nivel ≥ 2 **y** promedio < 3.0 (o ≥ 2 materias reprobadas) | Rendimiento insuficiente — requiere plan académico. |
| **Alerta primer nivel** | Nivel ≤ 1 con notas 0 o incompletas | No es reprobación — es inicio de trayectoria; requiere acompañamiento. |

Estas dos alertas nunca se suman ni se muestran juntas: son KPIs y badges separados en todos los dashboards.

### 4.3 Georreferenciación (DIVIPOLA)
- Cada estudiante tiene `municipio_residencia` + `departamento_residencia` en su ficha.
- El geocoder busca **por combinación municipio + departamento** para evitar homónimos.
- Fuente: catálogo oficial DANE + `divipola_extra.py` (correcciones institucionales).
- Cobertura actual: **99.7%** — solo ~40 estudiantes sin coordenadas por datos faltantes en origen.

### 4.4 Vulnerabilidad y caracterización
- **Grupo vulnerable** = víctima del conflicto **o** grupo étnico reconocido **o** discapacidad reportada **o** jefe de hogar menor de edad.
- **Vivienda rural** = zona `Rural` o `Semirrural`.

### 4.5 Seguridad y privacidad
- Todas las llamadas a IA envían **agregados**, nunca cédulas ni nombres.
- JWT con expiración; refresco por login.
- Cambio obligatorio de contraseña en primer ingreso (`must_change_password`).
- Bandera `download_enabled` para restringir descargas por usuario.

---

## 5. Flujos operativos recomendados

### 5.1 Puesta en marcha por periodo académico
1. Superadmin descarga la plantilla de **estudiantes** y la completa con la matrícula del nuevo periodo.
2. Sube el archivo → previsualiza → confirma ingesta.
3. Sube la plantilla de **notas históricas** con el corte más reciente.
4. Sube la **relación docente–materia** del periodo.
5. Ejecuta **Refresh completo** → recalcula promedios y alertas.
6. Envía credenciales masivas a docentes desde Configuración.

### 5.2 Uso diario del docente
1. Ingresa con su cédula (o correo institucional si es admin).
2. Selecciona el grupo desde el dropdown.
3. Revisa KPIs y estudiantes en riesgo o en alerta primer nivel.
4. Pulsa **IA** en un estudiante crítico para obtener un plan de intervención.
5. Pulsa **Resumen IA del grupo** para insights agregados.
6. Descarga la vista del grupo en Excel para reportes internos.

### 5.3 Vista del decano / coordinador
1. Ingresa con su correo institucional.
2. Los filtros globales quedan bloqueados a su facultad/programa.
3. Navega por Ejecutivo → Académico → Territorial → Insights IA.
4. Descarga base filtrada de su facultad.

---

## 6. Endpoints API — Referencia

Prefijo base: `/api`

### Autenticación
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/auth/login` | Login (email o cédula + contraseña). |
| GET | `/auth/me` | Info del usuario actual. |
| POST | `/auth/change-password` | Cambio de contraseña. |

### Dashboards
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/dashboards/executive` | KPIs institucionales. |
| GET | `/dashboards/academic` | Analítica académica. |
| GET | `/dashboards/territorial` | Datos para el mapa. |
| GET | `/dashboards/historical` | Series históricas. |
| GET | `/dashboards/en-riesgo?tipo=` | Riesgo académico / primer nivel / todos. |
| GET | `/dashboards/students` | Estudiantes filtrados. |
| GET | `/dashboards/students.xlsx` | Exportar Excel. |
| GET | `/dashboards/docente/grupo/{codigo}/vista` | Vista del docente por grupo. |

### Caracterización
| GET | `/caracterizacion/dashboard/{scope}` | Dashboards de caracterización. |
| GET | `/caracterizacion/students` | Estudiantes con filtros de caracterización. |

### Cargas / Uploads
| GET | `/uploads/template/{tipo}` | Descarga plantilla (`estudiantes`, `notas`, `docente_materia`). |
| POST | `/uploads/preview` | Previsualiza carga. |
| POST | `/uploads/ingest` | Persiste carga. |
| POST | `/uploads/rollback/{upload_id}` | Revierte una carga. |
| POST | `/uploads/full-refresh` | Recalcula derivados. |
| GET | `/uploads/backup/{coleccion}` | Backup por colección. |

### Administración
| GET/POST/PATCH/DELETE | `/admin/users` | CRUD de usuarios. |
| GET/POST | `/admin/docente-materia` | Asignación docente↔materia. |
| GET | `/admin/grupos` | Lista de grupos. |
| GET | `/admin/facultades-stats` | Estadísticas por facultad. |
| PUT | `/admin/facultades/{id}` | Editar facultad. |
| PUT | `/admin/programas/{id}` | Editar programa. |
| CRUD | `/admin/divipola` | Catálogo de municipios. |

### IA
| POST | `/ai/insights` | Insights por ámbito. |
| POST | `/ai/docente/alerta-estudiante` | Plan por estudiante. |
| POST | `/ai/docente/resumen-grupo` | Resumen de grupo. |

### Configuración
| GET/PATCH | `/config/smtp` | SMTP Gmail. |
| POST | `/config/smtp/test` | Test SMTP. |
| GET/PATCH | `/config/ai` | Proveedor y llaves de IA. |
| POST | `/config/send-credentials/{user_id}` | Envío individual. |
| POST | `/config/send-credentials-bulk` | Envío masivo. |
| POST | `/config/reset-initial-passwords` | Reset masivo docentes. |
| GET | `/config/initial-credentials.xlsx` | Excel de credenciales. |

---

## 7. Estructura de datos (MongoDB)

Colecciones principales:

| Colección | Contenido |
|---|---|
| `users` | Usuarios del sistema. Campos: `email`, `documento`, `hashed_password`, `role`, `docente_id`, `facultad_id`, `programa_id`, `must_change_password`, `download_enabled`, `is_active`. |
| `estudiantes` | Ficha completa del estudiante: identificación, sociodemografía, geolocalización (`municipio`, `departamento`, `lat`, `lng`), académico (`programa_id`, `facultad_id`, `nivel`, `avance_curricular`, `promedio_general`). |
| `notas_historicas` | Registro por `cedula × periodo × materia × docente × nota`. |
| `docente_materia` | Asignación por periodo: `docente_id`, `materia_id`, `periodo`, `codigo_grupo`. |
| `facultades` | Catálogo institucional. |
| `programas` | Catálogo con `facultad_id`. |
| `materias` | Catálogo con flags `es_extension`, `es_ingles_fuera_malla`. |
| `docentes` | Ficha del docente (nombres, cédula, correo). |
| `uploads` | Historial de cargas: `upload_id`, `tipo`, `usuario`, `fecha`, `resumen`, `estado`. |
| `system_settings` | Configuración global (SMTP, IA). |

---

## 8. Anexo — Plantillas Excel

### 8.1 Plantilla estudiantes
Campos mínimos requeridos: `documento`, `tipo_documento`, `nombres`, `apellidos`, `email`, `celular`, `fecha_nacimiento`, `genero`, `estado_civil`, `estrato`, `zona`, `municipio_residencia`, `departamento_residencia`, `programa`, `facultad`, `nivel`, `victima_conflicto`, `grupo_etnico`, `discapacidad`, `situacion_laboral`, `personas_a_cargo`.

### 8.2 Plantilla notas históricas
`cedula`, `periodo` (ej. `2026-1`), `codigo_grupo`, `materia`, `docente_documento`, `docente_nombre`, `nota`, `estado` (aprobado/reprobado/en curso).

### 8.3 Plantilla docente–materia
`docente_documento`, `docente_nombres`, `docente_apellidos`, `docente_email`, `materia_codigo`, `materia_nombre`, `periodo`, `codigo_grupo`.

**Consejo:** siempre descargue la plantilla desde la aplicación antes de cada carga — las cabeceras se validan de forma estricta.

---

## 9. Créditos y soporte

- Institución: **IU Digital de Antioquia**
- Superadmin del sistema: `lcorreaq@gmail.com`
- Documentación técnica interna: `/app/memory/PRD.md`, `/app/CHECKLIST_ADMIN_INSTITUCIONAL.md`
- Guía de despliegue en Google Cloud: `/app/MIGRACION_GOOGLE_CLOUD.md`

---

*Este manual describe la funcionalidad de la plataforma al corte de Feb 2026. Los módulos, endpoints y reglas de negocio pueden evolucionar; consulte la última versión antes de tomar decisiones institucionales.*
