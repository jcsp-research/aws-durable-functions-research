# AWS Durable Functions Workshop 2025

Evaluación práctica del nuevo servicio de AWS Lambda con estado,
incluyendo implementación local, comparación con baseline explícito
y análisis conceptual basado en el modelo de actores.

Autor: Julio Sigüenza Pacheco  
Objetivo: Artículo de 6 páginas para workshop.

## Estructura
- `docs/` → resúmenes y observaciones (Phases 1–3)
- `infra/` → plantilla SAM (preparada para despliegue en AWS)
- `notebooks/` → análisis de métricas y simulaciones
- `paper/` → esqueleto LaTeX del artículo
- `src/` → código del contador y pipeline de vídeo
- `tests/` → pruebas automatizadas (pytest)

## Uso (cuando tengamos cuenta AWS)
```bash
sam build && sam deploy --guided
pytest
make paper

