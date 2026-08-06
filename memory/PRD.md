# PRD — Sistema de Caracterización y Analítica Académica IU Digital de Antioquia

## Problem Statement
Aplicación web institucional moderna para gestión, caracterización, analítica académica y georreferenciación de estudiantes de educación superior. Procesos: caracterización estudiantil, permanencia, alertas tempranas, analítica territorial, seguimiento académico, apoyo a acreditación y dashboards ejecutivos.

## Stack
- Backend: FastAPI + MongoDB (motor) + JWT + pandas + emergentintegrations (GPT-5.4)
- Frontend: React 19 + shadcn/ui + Tailwind + Recharts + react-leaflet + lucide-react
- Fonts: Cabinet Grotesk (headings/KPIs) + IBM Plex Sans (body)
- Palette: IU Digital (Azul #0033A0, Rojo #E3000F, Amarillo #FFCD00)

## User Personas
1. Superadministrador — acceso total, gestión de usuarios y catálogos
2. Administrador — dashboards globales + carga de archivos
3. Docente — vista restringida a sus materias/estudiantes
4. Viewer — solo lectura de dashboards

## Core Requirements
- Auth JWT + cambio obligatorio de contraseña al primer login
- Carga Excel con validación, previsualización, versionado
- Dashboards: Ejecutivo, Académico, Territorial, Histórico, Docente
- Filtros globales: periodo, facultad, programa, materia, género, estrato, SISBEN, etnia, discapacidad, víctima, ruralidad, municipio
- Georreferenciación automática (DIVIPOLA local)
- IA: resúmenes automáticos vía OpenAI GPT-5.4 (Emergent LLM Key)
- Exportación PDF/Excel

## Últimos ajustes (2026-08)
- ✅ **Fix crítico de mapeo de datos vs archivo real**:
  - **Víctimas conflicto**: 1.427 (8.7%) — antes 4.852 (falso). Ahora deriva solo de "Grupo vulnerable" con palabras clave víctima/desplazado/conflicto. Ya no del campo "Ubicación de conflicto" (que solo indica lugar geográfico).
  - **Estudiantes rurales**: 7.551 (45.9%) — antes 0. Heurística basada en lista de 130 ciudades urbanas de Colombia (todas las capitales + área metro + ciudades intermedias > 100k hab).
  - **Vulnerables**: 2.853 (17.3%) — antes 100% al no filtrar "Sin dato".
  - **Discapacidad**: 202 (1.2%) — antes 70% por no filtrar "Ninguno" (masculino).
  - **Tipo vulnerabilidad**: "SIN DATO" en vez de "NINGUNO" para no vulnerables (mejor claridad en gráfico).
- ✅ **Chart programas mejorado**: nombres completos visibles (260px de ancho), altura dinámica según cantidad de programas, etiquetas de valor al final de cada barra.
- ✅ **Docentes con datos completos**: 398 docentes con `documento`, `cedula`, `iddoc`, `correo_institucional` y `correo_personal` separados. `asignatura_codigo` extraído automáticamente del nombre.
- ✅ **Periodos coherentes**: notas del archivo `notas_26_2.xlsx` se cargan como periodo real `2026-1` (leído de ANO/PERIODO en el propio archivo). Dashboard muestra 2025-2 (3.45, 84.871 notas) y 2026-1 (3.12, 84.505 notas).
- ✅ **Nueva pestaña Admin → Docentes**: tabla enriquecida con documento, correos, grupos, materias, estudiantes, programas + buscador + exportación CSV + modal detalle con histórico académico. Endpoints `/api/admin/docentes` y `/api/admin/docentes/{id}/grupos`.
- ✅ **Vista /grupos**: 1.311 grupos filtrables + modal detalle con estudiantes y notas históricas.

## Datos reales cargados (2026-08 · última verificación)
- **16.461 estudiantes** reales
- **1.311 grupos** activos periodo 2026-2
- **92.439 matrículas**
- **169.376 notas** — 2025-2 (84.871, prom 3.45) + **2026-1** (84.505, prom 3.12) · Promedio ponderado general: **3.29**
- **398 docentes** con documento, correo institucional, correo personal, IDDOC
- **5 facultades**, **59 programas** (21 con estudiantes activos)
- **KPIs verificados**: Rurales 45.9% · Vulnerables 17.3% · Víctimas 8.7% · Discapacidad 1.2%
- ✅ **Endpoint /en-riesgo**: score de riesgo combinado (nota bajo + factores vulnerabilidad)

## Implemented (2026-02)
- ✅ JWT auth con superadmin seed (lcorreaq@gmail.com)
- ✅ Modelo Student + carga Excel del diccionario de datos
- ✅ Dashboard Ejecutivo + Académico + Territorial (Leaflet) + Histórico + Caracterización
- ✅ Administración usuarios + catálogos (facultades/programas/materias/periodos)
- ✅ Relación docente-materia con carga (manual + **masiva por Excel**)
- ✅ Filtros globales reactivos con **cascada** (facultad→programa→materia) + **Docente** y **Materia**
- ✅ IA insights (GPT-5.4)
- ✅ DIVIPOLA precargado: **480 municipios** (220 Colombia DANE + 260 extra/internacionales)
- ✅ SISBEN por **niveles (A1-A5, B1-B7, C1-C18, D1-D21) y grupos (A/B/C/D)**
- ✅ Datos demo precargados (12.927 estudiantes con datos limpios)
- ✅ Dark/Light mode
- ✅ Limpieza de placeholders inválidos ('SELECCIONE...', 'NO REGISTRA') en agregaciones
- ✅ **Página `/cargas` rediseñada con 4 tabs**: Estudiantes, Notas históricas, Docente-Materia, Descargas/Backup
- ✅ **Plantillas Excel descargables** para los 3 tipos de carga
- ✅ **Carga masiva de notas históricas** con auto-creación de docentes/materias
- ✅ **Carga masiva docente-materia** con auto-creación de usuarios docentes (pwd inicial IUDigital2026!)
- ✅ **Exportaciones nuevas**: /api/exports/notas y /api/exports/docente-materia
- ✅ **Filtro por docente/materia** resuelve cédulas vía historico_notas en dashboards/caracterizacion/exports

## Backlog
- P1: Dashboard Docente con vista filtrada por materia/periodo
- P1: Exportación PDF profesional con marca institucional
- P1: Histórico académico real (notas multi-periodo)
- P2: Auditoría/logs de acceso
- P2: Geocoding con API DANE para municipios no mapeados
- P2: Materias críticas con alertas automáticas
- P2: PostgreSQL + PostGIS migration (si requerido)

## Test Credentials
Ver `/app/memory/test_credentials.md`
