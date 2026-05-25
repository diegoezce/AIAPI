# Tech Debt

## Seguridad

### [x] Autenticación por API Key
Agregar middleware en `main.py` que valide un header `X-API-Key` antes de procesar cualquier request.
Necesario antes de exponer la API públicamente a internet.

Ejemplo de uso esperado:
```
X-API-Key: tu-clave-secreta
```
