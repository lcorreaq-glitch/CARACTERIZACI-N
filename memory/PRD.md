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
