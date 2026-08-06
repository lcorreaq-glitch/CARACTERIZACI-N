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

## Últimos ajustes (2026-08 · última iteración)
- ✅ **Georreferenciación por departamento arreglada** — bug: el backend consultaba `departamento_residencia` (no existe) → corregido a `departamento`. Ahora muestra 15 departamentos: Antioquia (10.143), Magdalena (1.315), Nariño (642), Valle del Cauca (535), Cundinamarca (406), La Guajira, Bolívar, Bogotá D.C., etc.
- ✅ **Rangos de edad numéricos añadidos**: Menor 18 (288), 18-22 (3.368), 23-27 (4.434), 28-32 (3.589), 33-40 (3.113), 41-50 (1.403), 51+ (266). Complementa el chart de "Grupos etarios" cualitativos.
- ✅ **Departamentos normalizados**: Nariño (antes Narinio/Narino), Bolívar (Bolivar), Bogotá D.C. (Bogota D.c.), Atlántico, Córdoba, Chocó, Boyacá, Vaupés, Guainía, San Andrés y Providencia.
- ✅ **"Víctimas" plural** consolidado a "Víctima del Conflicto Armado" (117 registros).
- ✅ **Charts con etiquetas de valor** al final de cada barra (LabelList).
- ✅ **Tipo de ubicación viene del "Tipo de vivienda"** del archivo real: Urbana 12.455, Rural 3.261, Semiurbana 306, Semirural 143, Sin dato 296.
- ✅ **Grupo etario del campo "Gruopo etario"** del archivo. Grupos etarios cronológicos (Adolescencia → Persona mayor).
- ✅ **399 docentes reales** con `documento`, `iddoc`, `correo_personal`, `correo_institucional` completos.
- ✅ **737 relaciones docente-materia** consolidadas.
- ✅ **Textos en Title Case español**: "Administración de Empresas", "Ingeniería de Software y Datos", "Víctima del Conflicto Armado", "Bogotá D.C.".
- ✅ **Consolidación de vulnerabilidad**: 15+ variantes ortográficas fusionadas en 9-10 categorías canónicas.

## Datos reales cargados (2026-08 · única fuente de verdad)
- **16.461 estudiantes** (CARACTERIZACION_2026.xlsx)
- **1.311 grupos** activos periodo 2026-2 (ASIGNACION_GRUPO_2026_2)
- **92.439 matrículas** · **737 relaciones docente-materia**
- **169.376 notas** — 2025-2 (84.871, prom 3.45) + **2026-1** (84.505, prom 3.12) · Promedio ponderado: **3.29**
- **399 docentes** reales + demo = 400
- **5 facultades**, **59 programas** SNIES (21 con estudiantes activos)
- **KPIs auditados**: Vivienda rural 20.7% · Vulnerables 17.3% · Víctimas 8.5% · Discapacidad 1.2%
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
