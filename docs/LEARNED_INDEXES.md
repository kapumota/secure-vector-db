### Indices aprendidos

#### Objetivo

La Fase 1 agrega un indice aprendido lineal por segmentos para claves enteras ordenadas.

El componente es experimental y no reemplaza al B+ Tree. En esta fase se mantiene aislado para validar su comportamiento antes de conectarlo al flujo de busqueda por `record_id`.

#### Diseno

`LearnedPiecewiseIndex` aproxima la posicion de una clave dentro de una lista ordenada.

El flujo interno es:

```text
clave
prediccion lineal por segmento
posicion aproximada
ventana local de busqueda
```

Cada segmento guarda:

```text
clave inicial
clave final
posicion inicial
posicion final
pendiente
intercepto
error maximo local
error promedio local
```

#### Garantias de esta fase

El indice aprendido cumple estas reglas:

```text
- Solo acepta claves enteras estrictamente ordenadas.
- No acepta claves duplicadas.
- No predice posiciones fuera del rango entrenado.
- Mantiene el error observado dentro del umbral cuando el entrenamiento lo permite.
- Devuelve una ventana inclusiva alrededor de la prediccion.
- No intercepta todavia las busquedas reales de SecureVectorDB.
```

#### Alcance

Esta fase no modifica `SecureVectorDB.search_by_id`.

El B+ Tree sigue siendo el indice exacto del sistema. La integracion hibrida con fallback corresponde a una fase posterior.

#### Validacion

```bash
ruff check .
mypy secure_vector_db
python -m pytest -q
```

#### Siguiente fase

La Fase 2 debe agregar un enrutador de indice ordenado que use el indice aprendido como acelerador y el B+ Tree como fallback exacto.
