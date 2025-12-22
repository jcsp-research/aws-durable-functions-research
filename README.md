# AWS Durable Functions Workshop 2025  
Evaluación práctica del nuevo servicio de AWS Lambda con estado.  
**Autor:** TuNombre  
**Objetivo:** Artículo de 6 páginas para workshop.  

## Estructura
- `docs/` → resúmenes y observaciones  
- `infra/` → plantilla SAM (vacia por ahora)  
- `notebooks/` → análisis de métricas  
- `paper/` → esqueleto LaTeX  
- `src/` → código de contador y pipeline  
- `tests/` → pruebas pytest  

## Uso (cuando tengamos cuenta AWS)
```bash
sam build && sam deploy --guided
pytest
make paper
