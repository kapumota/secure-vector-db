# SecureVectorDB: informe de reproducción experimental

## 1. Identificación

- Fecha de cierre: 7 de noviembre de 2026.
- Código histórico: `v1.0.0`.
- Commit histórico: `4b73342887f22d3317ebc3490b1cf5c9253128b3`.
- Commit local de mantenimiento: `4142d8af88d1d46ca5bb4f0c581a4ce67631ea75`.
- Entorno experimental: Linux y Docker.
- Evidencias: `experiments/_local/reproducciones/`.

## 2. Mantenimiento del software

La última ejecución comunicada de pytest finalizó con
276 pruebas aprobadas y una advertencia de Starlette.

Se corrigió la aceptación implícita de la clave API de
desarrollo y se restauraron los puntos de entrada de la CLI.

## 3. Reproducción G0

- Falsación: 8 casos coincidentes.
- Baseline SQLite: 2 casos coincidentes.
- FAISS: resultados coincidentes al excluir el campo
  `faiss_version`.

## 4. Reproducción G0.1

- Contrapruebas: 14 casos coincidentes.

## 5. Reproducción P0

Se completó la campaña sobre PostgreSQL/pgvector y Qdrant.

| Indicador | Original | Reproducción |
|---|---:|---:|
| Consultas ANN | 12000 | 12000 |
| Comprobaciones directas | 24 | 24 |
| Controles | 3750 | 3750 |
| Variación de IDs entre repeticiones | 762 | 849 |
| IDs distintos pgvector | 4578 | 4590 |
| IDs distintos Qdrant | 4764 | 4830 |

Las seis ejecuciones registraron cero desacuerdos con el
baseline versionado. Las trazas fueron coherentes.

La reproducción no fue idéntica a nivel de conjuntos ANN.
Esta variabilidad no constituye por sí misma una violación
de integridad o consistencia.

## 6. Dictamen técnico

Las comprobaciones disponibles respaldan la reproducción
de las propiedades evaluadas en G0, G0.1 y P0.

No se demuestra una ventaja experimental adicional frente
al baseline versionado. Se conserva el dictamen científico
NO GO anterior para esa pretensión de originalidad.

## 7. Limitaciones

- La coincidencia de FAISS excluye únicamente su versión.
- Los conjuntos ANN no son idénticos entre campañas.
- La reproducción no constituye prueba formal de ausencia
  de defectos en todos los estados posibles.
- La redistribución de datasets requiere revisar licencias.
- La aptitud editorial aún no ha sido evaluada.

## 8. Evidencia y trazabilidad

El manifiesto de resultados está en
`experiments/_local/reproducciones/MANIFEST_SHA256.txt`.

Los resultados voluminosos no se incorporan automáticamente
al repositorio Git.
