# Guía: ver el equipo jugando en tu PC con Booster Studio

Para Laureano. Necesitás Booster Studio y Docker instalados y abiertos (Docker Desktop corriendo en Windows/macOS).

## 1. Bajar el equipo

1. Entrá a <https://github.com/Laumonteros/booster-studio-s2>, botón verde **Code → Download ZIP** (o `git clone` si usás git).
2. Descomprimí el ZIP. La carpeta del equipo es **`team/`** (adentro están `agent.toml`, `src/` y `.booster-studio/`).

## 2. Abrir el proyecto en Booster Studio

1. Abrí Booster Studio y elegí **abrir carpeta / Open Project**, seleccionando la carpeta **`team`** (no la raíz del repo).
2. Studio reconoce el proyecto como partido 3v3 (escena `football3v3`, modo `soccer-match`) y prepara el entorno virtual. La primera vez descarga imágenes de Docker de varios GB: esperá a que termine.
3. Cuando aparezca, **seleccioná el robot virtual** (Virtual Robot).

## 3. Jugar un partido completo

1. La primera vez tocá el **martillo** arriba para compilar (Build).
2. Tocá **Activate, build, deploy and run agent** (o **Start** en el entorno de partido). Se abre el simulador con la cancha; tu equipo controla 3 robots y, según la guía oficial, los 3 robots rivales aparecen solos. Si Studio te deja elegir el rival, elegí el ejemplo oficial (Soccer Tournament).
3. Dejalo correr hasta el final: son **10 minutos de tiempo simulado**, sin entretiempo.
4. Qué mirar:
   - Sobre cada robot aparece `id:acción`; arriba `phase=... state=... set=...`.
   - Estrategia: **un arquero fijo** cerca del arco propio y **dos jugadores que van a la pelota y al arco rival**.
   - Si un robot se cae o es penalizado, lo indica la etiqueta; el registro del árbitro y del agente se ve en la interfaz de Studio.

## 4. Archivo para mandar al torneo

1. En Studio, con el proyecto `team` abierto, tocá **Build Agent Only** (arriba a la derecha).
2. Se genera **`team/build/laumonteros_team_v1-1.0.0.agent`**. Ese es el archivo.
3. En <https://champion.booster.tech/my-team?lang=en>: **My Team → Submit Code**, respondé las 5 preguntas de reglas y subí ese `.agent`. Un mensaje de éxito confirma el envío. Fecha límite de estrategia: antes del 28 de noviembre.

### Sobre la firma

- La [Guía oficial de envío](https://booster.feishu.cn/wiki/FJMtwUFtIiQkS3kMmTpc8If7nQg) no pide ninguna firma ni certificado del evento: solo **Build Agent Only** y subir el `.agent`.
- El `.agent` que armé en mi máquina está firmado con un **certificado local de prueba** (autofirmado); sirve para probar, pero conviene **subir el que genere tu propio Studio** con Build Agent Only.
- Si al compilar Studio muestra `Missing sign config`, avisame.

Actualizar el equipo después: bajá de nuevo el repo y repetí los pasos 2 a 4; el torneo usa siempre el último `.agent` enviado para los partidos siguientes.
