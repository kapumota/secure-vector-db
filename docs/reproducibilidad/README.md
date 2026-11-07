# Reproducibilidad de SecureVectorDB

## Alcance

Este directorio contiene el informe de reproducción
experimental de G0, G0.1 y P0.

Se verificaron los resultados de G0 y G0.1 frente a
sus expedientes históricos. La campaña P0 se reprodujo
con PostgreSQL/pgvector y Qdrant mediante Docker.

## Evidencias

El archivo MANIFEST_SHA256_RESULTADOS.txt contiene
los hashes de 31 archivos generados durante la
reproducción.

Las rutas del manifiesto son relativas al directorio:

experiments/_local/reproducciones/

Los archivos originales permanecen almacenados
localmente y no se incluyen en este repositorio.

Por tanto, el manifiesto permite verificar su
integridad cuando se dispone de los archivos,
pero no constituye por sí solo un depósito público
completo de los resultados.

## Limitaciones

La campaña P0 presenta variación en los identificadores
recuperados por ANN respecto de la referencia original.

La coincidencia de los controles no demuestra una nueva
técnica de detección de defectos ni superioridad
experimental frente al baseline versionado.

La redistribución de datasets de terceros requiere
verificar previamente sus condiciones de licencia.
