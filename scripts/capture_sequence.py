"""Read-only time-lapse of one full match; run inside the simulator container."""
import asyncio
import json
import shutil
import time
import urllib.request
from pathlib import Path

import mujoco
import websockets
from PIL import Image, ImageDraw, ImageFont

from transport.websocket.message_protocol import (
    MessageType, deserialize_physics_state, unpack_message,
)


async def main():
    output = Path('/match/results/evidence')
    frames_dir = output / 'frames'
    frames_dir.mkdir(parents=True, exist_ok=True)
    model = mujoco.MjModel.from_xml_path('mjcf/football_match_pitch_6_K1.xml')
    model.vis.global_.offwidth = 960
    model.vis.global_.offheight = 540
    data = mujoco.MjData(model)
    camera = mujoco.MjvCamera()
    camera.lookat[:] = [0, 0, 0]
    camera.distance, camera.azimuth, camera.elevation = 19, 90, -65
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 16)
    except OSError:
        font = ImageFont.load_default()
    previous_clock = None
    next_status_check = 0
    paths = []
    captions = []
    with mujoco.Renderer(model, height=540, width=960) as renderer:
        async with websockets.connect('ws://127.0.0.1:8788', max_size=16 * 1024 * 1024, max_queue=1) as ws:
            await ws.send('subscribe:physics_state')
            async for message in ws:
                if not isinstance(message, bytes):
                    continue
                kind, payload = unpack_message(message)
                if kind != MessageType.PHYSICS_STATE:
                    continue
                state = deserialize_physics_state(payload)
                if time.monotonic() < next_status_check:
                    continue
                next_status_check = time.monotonic() + 1
                with urllib.request.urlopen('http://127.0.0.1:38383/status', timeout=10) as response:
                    game = json.load(response)['game']
                clock = game['timeRemaining']
                final = game['state'] == 'finished'
                if game['state'] != 'playing' and not final:
                    continue
                if previous_clock is not None and previous_clock - clock < 45 and not final:
                    continue
                data.qpos[:] = state['qpos']
                mujoco.mj_forward(model, data)
                renderer.update_scene(data, camera=camera)
                frame = Image.fromarray(renderer.render())
                draw = ImageDraw.Draw(frame)
                home, away = game['teams']['home'], game['teams']['away']
                caption = f"{home['name']} {home['score']} - {away['score']} {away['name']} | {game['state']} | {max(0, clock):.1f}s"
                draw.rectangle([0, 0, 960, 49], fill='black')
                draw.text((10, 4), caption, font=font, fill='white')
                draw.text((10, 27), 'CPU-rendered actual physics | time-lapse: one frame per ~45 simulation seconds', font=font, fill='white')
                path = frames_dir / f'frame-{len(paths):03}.png'
                frame.save(path)
                paths.append(path)
                captions.append({'file': path.name, 'physics_time': state['time'], 'remaining': clock, 'caption': caption})
                previous_clock = clock
                print(caption, flush=True)
                if final:
                    break
    if len(paths) < 3:
        raise RuntimeError('Not enough actual frames for match evidence')
    frames = [Image.open(path).convert('RGB') for path in paths]
    animation = output / 'match-timelapse.webp'
    frames[0].save(animation, save_all=True, append_images=frames[1:], duration=900, loop=0, quality=75, method=4)
    for label, index in [('start', 0), ('middle', len(paths) // 2), ('final', len(paths) - 1)]:
        shutil.copyfile(paths[index], output / f'snapshot-{label}.png')
    (output / 'frames.json').write_text(json.dumps(captions, indent=2))
    if animation.stat().st_size > 10 * 1024 * 1024 or len(frames) * .9 > 30:
        raise RuntimeError('Animation exceeds requested size/duration budget')
    print(f'Saved {len(frames)} frames, {len(frames) * .9:.1f}s, {animation.stat().st_size} bytes: {animation}', flush=True)


if __name__ == '__main__':
    asyncio.run(main())
