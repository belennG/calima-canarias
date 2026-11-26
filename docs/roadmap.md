# Calima Canarias – Hoja de ruta del MVP

Nov 24, 2026 · @Belén

Los pasos desde el final del spike hasta el MVP publicado. El detalle del spike está en el [Diario del spike](https://claude.ai/artifact/8oHprY9DtWXYQtV3i5t4N6).

## Cómo se ordena: esqueleto andante

No conviene construir capa por capa (toda la base, después toda la API, después todo el front). Conviene armar primero un **esqueleto andante** (*walking skeleton*): una versión fea pero completa de punta a punta, publicada en internet, y después ir engordándola. Así los problemas de integración (Docker, CORS, deploy) aparecen la primera semana y no al final, y siempre hay un link para mostrar.

## Los pasos

| Paso | Qué | Qué incluye | Días aprox. |
| --- | --- | --- | --- |
| 0 | **Cerrar el spike** | Terminar la EEA (121 archivos, coordenadas, febrero de 2020), hacer CAMS y escribir `docs/data-sources.md` con las 8 respuestas y un veredicto: "se puede" o "cambiamos X" | 2–3 |
| 1 | **Diseño** | Tablas (estaciones, mediciones, pronósticos CAMS, episodios, métricas), definición de episodio v1 y primeras decisiones en `docs/decisions.md`. Vos proponés, Claude corrige | 1 |
| 2 | **Esqueleto andante** | Docker Compose con Postgres + PostGIS, FastAPI con `/health` y `/stations`, app Angular con la lista de estaciones, CI en GitHub Actions y deploy público | 2–3 |
| 3 | **Ingesta EEA** | Comando `ingest eea` (Typer): baja, concatena por estación, pasa las horas a UTC, filtra por validez y guarda en la base. Idempotente, con migraciones de Alembic y tests | 2–3 |
| 4 | **Ingesta CAMS** | Bajar mes por mes desde 2015, tomar la celda de la grilla más cercana a cada estación y guardar el pronóstico por plazo (0–72 h). Es la descarga más pesada | 3–4 |
| 5 | **Análisis** | Medias diarias, detección de episodios y métricas de verificación (sesgo, MAE, POD, FAR) por plazo y por año. Lo escribís vos primero. Test obligatorio: el episodio de febrero de 2020 tiene que aparecer | 3–4 |
| 6 | **API** | Endpoints para Ahora, historial, episodios y precisión del pronóstico | 1–2 |
| 7 | **Frontend** | Las 5 páginas: Ahora, Historial, Episodio, Precisión del pronóstico y Metodología. Mapa con ArcGIS Maps SDK, gráficos con Vega-Lite, textos en ES/EN/DE | 5–7 |
| 8 | **GeoServer** | Estaciones y episodios como capas WMS/WFS desde PostGIS. Es la parte que habla el idioma de Telespazio | 1–2 |
| 9 | **Actualización diaria** | Job programado que baja los datos nuevos y el pronóstico del día, para que "Ahora" no quede congelado | 1–2 |
| 10 | **README y pulido** | Capturas, diagrama de arquitectura, la nota sobre por qué 13 años no alcanzan para hablar de clima y `docs/ai-workflow.md`. Recién ahí se muestra a Alan y a los institutos | 1–2 |
|  | **Total** |  | **22–33** |

Cada paso es una rama y un PR con el CI en verde.

El total equivale a unas 5–7 semanas a tiempo completo, y algo más si cada parte se va aprendiendo. Son estimaciones gruesas: el spike va a decir si CAMS es más fácil o más difícil de lo que parece.

## Pendiente para el spike: los datos de hoy

La página "Ahora" necesita datos recientes, pero el dataset 2 (verificado) llega solo hasta 2025. Para los datos de hoy hace falta el dataset 1 (sin verificar). Hay que comprobar que trae Canarias y con cuánto retraso se publica.

## Hito para Lluís (Telespazio)

El seguimiento con Lluís está pensado para el 12–15 de diciembre. Si para entonces está hecho hasta el paso 3, más una página del episodio de febrero de 2020 con los datos de las estaciones (todavía sin CAMS), se le puede mandar un link a algo que funciona en vez de "estoy haciendo un proyecto". Es ajustado, pero posible.

## Costos del deploy

GeoServer es Java y usa bastante memoria, así que los planes gratuitos de hosting probablemente no alcancen. Lo razonable es un servidor chico (VPS) con Docker Compose. Se decide en el paso 2.
