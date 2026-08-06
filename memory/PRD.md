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

## Latest session (2026-08-06)
- ✅ **Ingreso familiar** formateado en pesos colombianos (COP) — antes mostraba "$1.4M" ambiguo, ahora "$1,7 M COP".
- ✅ **Descarga por grupo (cruce Asignación × Caracterización × Notas)** — nuevo endpoint `GET /api/exports/grupo/{codigo}` que retorna un Excel con 3 hojas (Grupo, Estudiantes, Notas). Botón por curso en el panel "Docente seleccionado".
- ✅ **Permiso de descarga configurable** — nuevo campo `download_enabled` por usuario. Los docentes NO pueden descargar por defecto; el superadmin habilita caso a caso o globalmente.
- ✅ **System settings globales** (colección `system_settings`) — 4 toggles: `docente_downloads_globally_enabled`, `docente_ai_insights_enabled`, `docente_can_see_all_periods`, `allow_public_landing`. Endpoints `GET/PATCH /api/admin/system-settings`.
- ✅ **Admin → Usuarios & Roles** rediseñado con: KPI strip (Total/Activos/Inactivos/Roles), búsqueda + filtros por rol y estado, switches en línea para Estado y Descargas, edición completa (rol, nombre, active, download_enabled), reset de contraseña con vuelta a `must_change_password=true`, badges de rol coloreados, protección contra auto-desactivación/eliminación.
- ✅ **Admin → Permisos globales** (nueva pestaña) con toggles descritos y matriz de permisos por rol.
- ✅ **Enforcement en backend**: `/api/exports/students`, `/api/exports/notas`, `/api/exports/grupo/{}` bloquean 403 si el docente no tiene permiso; además fuerzan scope al propio docente (no puede exportar grupos ajenos).
- ✅ **Startup backfill** idempotente: `download_enabled=true` para superadmin/admin existentes; `false` para docentes/viewers sin el campo.


- ✅ **Dashboard académico rediseñado desde cero** — 100% derivado de `historico_notas` (2025-2 + 2026-1, 169.376 notas) y el campo `nivel` de students. Sin datos inventados ni antiguos.
  - **KPIs**: En riesgo (1.418), Excelencia (3.017), Tasa aprobación global (76.5%), Habilitación exitosa (72.8%).
  - **Sección 1 — Comparativo periodos**: Estados de notas apilados (Aprobada/Reprobada/Cancelada/Habilitada/Matriculada/Prematriculada/Homologada), distribución de notas por rangos 2025-2 vs 2026-1, tabla bloques × periodo con promedio y % aprobación.
  - **Sección 2 — Materias críticas**: Top 10 asignaturas con mayor reprobación (Pensamiento Algorítmico 63.7%, Cálculo 62.6%…), Top 10 con mejor rendimiento (Ética 4.85, Desarrollo Vivienda 4.80…), rendimiento por área de formación (Ing. y Cs. Agropecuarias 72.7%, Educación 76.6%, Cs. Básicas y Humanidades 67.7%), promedio por programa ponderado desde notas reales.
  - **Sección 3 — Trayectoria estudiantil (nivel 2026-2)**: Estudiantes por semestre (Pre-grado 630, Sem 1 5.738, Sem 2 1.455…), créditos aprobados vs reprobados por periodo (2025-2: 161.415 aprob vs 39.417 reprob), habilitaciones con % éxito, avance curricular por programa.
- ✅ Endpoint `GET /api/dashboards/academic` completamente refactorizado con 10 nuevas agregaciones.
- ✅ **Georreferenciación por departamento arreglada** — bug: consultaba campo inexistente. Ahora muestra Antioquia (10.143), Magdalena (1.315), Nariño (642), Valle del Cauca, Cundinamarca, La Guajira, Bolívar, Bogotá D.C., Cauca, Córdoba, Sucre, Atlántico, Cesar, Tolima, Boyacá.
- ✅ **Rangos de edad numéricos añadidos** (Menor 18, 18-22, 23-27, 28-32, 33-40, 41-50, 51+) junto con "Grupos etarios" cualitativos.
- ✅ **Charts con etiquetas de valor** (LabelList) en programas, departamentos, grupos etarios, avance, etc.
- ✅ **Departamentos y "Víctimas" plural normalizados** (Nariño/Narinio, Bolívar/Bolivar, Bogotá D.C., etc.).

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

## Backlog (actualizado)
- P0: **Alertas tempranas con IA** (OpenAI GPT-5.4 + Emergent LLM Key) para estudiantes en riesgo (promedio < 3.0 + factores de vulnerabilidad). PENDIENTE.
- P0: Edit funcional de "Grupos" (más allá de solo lectura).
- P0: Detalle y edición rica de "Facultades" (similar a Programas).
- P1: Exportación PDF profesional con marca institucional.
- P1: Histórico académico real (notas multi-periodo).
- P2: Auditoría/logs de acceso (logins, uploads, exports).
- P2: Geocoding con API DANE para municipios no mapeados.
- P2: Materias críticas con alertas automáticas.
- P2: PostgreSQL + PostGIS migration (si requerido).

## Test Credentials
Ver `/app/memory/test_credentials.md`

## Últimos ajustes (2026-08 · iteración previa)
