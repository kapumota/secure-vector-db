### Politica de errores

#### Objetivo

Este documento define una politica minima de errores para SecureVectorDB.

El objetivo es que API, CLI y pruebas usen errores previsibles, sin ocultar fallos importantes ni exponer detalles innecesarios.

#### Codigos HTTP

```text
200: operacion exitosa
201: recurso creado si el endpoint lo usa
400: entrada invalida o rango invalido
401: falta X-API-Key o la clave no es valida
404: registro o recurso no encontrado
409: conflicto de estado si aplica
422: validacion de esquema FastAPI
429: limite de tasa excedido
500: error interno no esperado
```

#### Errores de dominio

```text
validation_error: entrada invalida
not_found: recurso no encontrado
auth_error: autenticacion fallida
rate_limited: limite de tasa excedido
integrity_error: verificacion de integridad fallida
persistence_error: inconsistencia de persistencia
learned_index_disabled: indice aprendido no activo
learned_index_needs_retrain: indice aprendido requiere reentrenamiento
```

#### Politica para CLI

Los comandos CLI deben:

```text
- imprimir JSON cuando el comando sea de diagnostico;
- usar mensajes en español;
- devolver codigo de salida no cero ante errores no recuperables;
- no escribir archivos de prueba dentro del repositorio sin que el usuario lo pida;
- no ocultar errores de validacion.
```

#### Politica para API

La API debe:

```text
- devolver errores JSON;
- no exponer stack traces en respuestas normales;
- conservar nombres de campos documentados;
- usar codigos HTTP coherentes con el tipo de error;
- mantener `X-API-Key` para endpoints protegidos.
```

#### Alcance

Esta politica no implementa un sistema completo de codigos de error versionados. Define una base minima para un release serio y puede evolucionar en versiones posteriores.
