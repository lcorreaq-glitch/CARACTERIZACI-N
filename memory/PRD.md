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
- ✅ **Fix carga real de docentes**: `load_real_data.py` ahora persiste `documento`, `cedula`, `iddoc`, `correo_personal` y `correo_institucional` separadamente para los 398 docentes
- ✅ **Fix asignatura_codigo**: se extrae automáticamente del sufijo del nombre de la asignatura cuando el campo directo viene vacío en el CSV (antes 1.311 grupos → ahora 0 grupos sin código de asignatura)
- ✅ **Fix cross-periodo notas ↔ grupos**: notas de `notas_26_2.xlsx` se cargan como periodo real `2026-1` (leyendo ANO/PERIODO del archivo, no del nombre); grupos siguen en `2026-2`
- ✅ **Fix dashboard KPIs**:
  - Promedio ponderado real desde `historico_notas` (3.29)
  - Vulnerables corregido: 2.853 (17.3%) — antes marcaba 100% al incluir "Sin dato"
  - Discapacidad corregida: 202 (1.2%) — antes 70% por no filtrar "Ninguno" masculino
  - Periodo 2026-1 con 84.505 notas y prom 3.12 (antes mostraba 0)
- ✅ **Nueva pestaña Admin → Docentes**: tabla enriquecida (documento, correo institucional, correo personal, grupos, materias, estudiantes, programas) con buscador, exportación CSV y modal de detalle con histórico académico por grupo
- ✅ Endpoints: `GET /api/admin/docentes`, `GET /api/admin/docentes/{id}/grupos`
- ✅ **Vista /grupos NUEVA**: 1.311 grupos filtrables por código/asignatura/docente/programa + modal detalle con estudiantes, notas históricas por periodo y KPIs
- ✅ Endpoints: `GET /api/admin/grupos` (con conteos), `GET /api/admin/grupos/{codigo}` (detalle), `PUT /api/admin/programas/{id}` (editar), `GET /api/admin/facultades-stats`
- ✅ Vista rica de **Programas** con ojo/modal, buscador, filtro por nivel, badges coloreados
- ✅ Datos limpios: nombres Title Case, códigos SNIES sin `.0`, nivel/modalidad rellenados

## Datos reales cargados (2026-08)
- ✅ **16.461 estudiantes** reales (CARACTERIZACION_2026.xlsx) — homologados con schema institucional
- ✅ **1.311 grupos** activos periodo 2026-2 (ASIGNACION_GRUPO_CONSOLIDADO_2026_2)
- ✅ **92.439 matrículas** (cédula × codigo_grupo × periodo)
- ✅ **169.376 notas** — 2025-2 (84.871) + **2026-1** (84.505)
- ✅ **398 docentes** con documento, correo institucional, correo personal y IDDOC completos
- ✅ **5 facultades**, **59 programas** desde catálogo SNIES oficial
- ✅ **Panel docente restringido**: cada docente ve solo sus grupos + estudiantes matriculados
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
