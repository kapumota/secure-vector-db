### Contrato publico de CLI

#### Objetivo

Este documento define el contrato publico de CLI para SecureVectorDB.

El objetivo es separar comandos estables de comandos compatibles y dejar claro que puede cambiar en versiones futuras.

#### Politica de estabilidad

```text
Los comandos marcados como estable nucleo se consideran estables durante toda la serie 1.x.
estable durante toda la serie 1.x
Los comandos marcados como estable diagnostico se consideran estables para observabilidad, recuperacion y depuracion.
Los comandos marcados como compatible se mantienen como alias o compatibilidad hacia atras.
Los cambios incompatibles deben reservarse para una version mayor.
```

#### Comandos detectados

| Comando | Estado |
| --- | --- |
| `delete` | estable nucleo |
| `demo` | estable nucleo |
| `explain-get` | estable diagnostico |
| `explain-id` | compatible |
| `explain-range` | estable diagnostico |
| `get` | estable nucleo |
| `index-health` | estable diagnostico |
| `index-stats` | estable diagnostico |
| `insert` | estable nucleo |
| `persistence-health` | estable diagnostico |
| `range` | estable nucleo |
| `retrain-learned-index` | estable diagnostico |
| `search` | estable nucleo |
| `train-learned-index` | estable nucleo |
| `verify` | estable nucleo |

#### Reglas de salida

Los comandos que devuelven JSON deben mantener campos principales estables durante la serie 1.x.

Los comandos de diagnostico pueden agregar campos nuevos, pero no deben eliminar campos existentes sin documentarlo.

#### Comandos recomendados para nuevas integraciones

```bash
python -m secure_vector_db.cli --db demo.sqlite index-health
python -m secure_vector_db.cli --db demo.sqlite explain-get 42
python -m secure_vector_db.cli --db demo.sqlite explain-range 10 20
python -m secure_vector_db.cli --db demo.sqlite persistence-health
```

#### Compatibilidad

`explain-id` se conserva como comando compatible. Para nuevas integraciones se recomienda:

```bash
python -m secure_vector_db.cli --db demo.sqlite explain-get 42
```

#### Alcance

Este contrato no promete estabilidad de salidas internas no documentadas ni de comandos auxiliares no listados en este archivo.
