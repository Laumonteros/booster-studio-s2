"""Developer-only read-only capture of the running local MuJoCo match."""
import asyncio
import json
import urllib.request
from pathlib import Path

import mujoco
import numpy as np
import websockets
from PIL import Image, ImageDraw

from transport.websocket.message_protocol import (
    MessageType,
    deserialize_physics_state,
    unpack_message,
)


async def snapshot():
    async with websockets.connect("ws://127.0.0.1:8788", max_size=16 * 1024 * 1024) as ws:
        await ws.send("subscribe:physics_state")
        while True:
            message = await asyncio.wait_for(ws.recv(), timeout=20)
            if not isinstance(message, bytes):
                continue
            kind, payload = unpack_message(message)
            if kind == MessageType.PHYSICS_STATE:
                return deserialize_physics_state(payload)


state = asyncio.run(snapshot())
with urllib.request.urlopen("http://127.0.0.1:38383/status", timeout=10) as response:
    status = json.load(response)
out = Path("/match/results")
np.savez(out / "snapshot-state.npz", **state)
(out / "snapshot-status.json").write_text(json.dumps(status, indent=2))
model = mujoco.MjModel.from_xml_path("mjcf/football_match_pitch_6_K1.xml")
model.vis.global_.offwidth = 1280
model.vis.global_.offheight = 720
data = mujoco.MjData(model)
data.qpos[:] = state["qpos"]
mujoco.mj_forward(model, data)
camera = mujoco.MjvCamera()
camera.lookat[:] = [0, 0, 0]
camera.distance = 19
camera.azimuth = 90
camera.elevation = -65
with mujoco.Renderer(model, height=720, width=1280) as renderer:
    renderer.update_scene(data, camera=camera)
    frame = Image.fromarray(renderer.render())
game = status["game"]
home = game["teams"]["home"]["score"]
away = game["teams"]["away"]["score"]
draw = ImageDraw.Draw(frame)
draw.rectangle([0, 0, 1280, 48], fill="black")
draw.text((12, 8), f"Booster K1 3v3 | sample vs sample | {home} - {away} | {game['state']} | {game['timeRemaining']:.1f}s remaining", fill="white")
draw.text((12, 28), "Actual physics snapshot; CPU EGL render (not Studio's GPU camera)", fill="white")
frame.save(out / "match-snapshot.png")
print(f"Saved {out / 'match-snapshot.png'}")
