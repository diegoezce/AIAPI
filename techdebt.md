# Tech Debt

## Seguridad

### [x] Autenticación por API Key
Agregar middleware en `main.py` que valide un header `X-API-Key` antes de procesar cualquier request.
Necesario antes de exponer la API públicamente a internet.

Ejemplo de uso esperado:
```
X-API-Key: tu-clave-secreta
```

---

## Infraestructura

### [ ] Correr la API como servicio de Windows
Registrar `python run.py` como Windows Service usando NSSM o Task Scheduler para que arranque automáticamente con la máquina y se reinicie si falla.

### [ ] Correr Cloudflare Tunnel como servicio de Windows
Registrar `cloudflared tunnel` como servicio para que el túnel arranque automáticamente con la máquina. Cloudflare tiene soporte nativo: `cloudflared service install`.

### [ ] URL fija para Cloudflare Tunnel
La URL actual (`trycloudflare.com`) cambia en cada reinicio. Configurar un túnel nombrado con dominio propio en Cloudflare Zero Trust para tener una URL permanente.
