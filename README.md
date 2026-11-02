# RUN – VR Horror (multiplayer server + game)

One tiny Python program (`server.py`, no packages needed) does two jobs:
it serves the game and it connects players who type the same room code.

## Put it online (free, ~10 minutes)
1. Make a free account on github.com and create a new **public** repository (e.g. `run-vr-horror`).
2. Click **Add file → Upload files** and drag in EVERYTHING from this folder
   (`server.py`, `render.yaml`, `requirements.txt`, and the whole `public` folder). Commit.
3. Make a free account on render.com. Click **New → Web Service**, connect GitHub, pick your repo.
   - Runtime: **Python 3**
   - Build command: `echo ok`
   - Start command: `python server.py`
   - Plan: **Free**
   Click **Create Web Service** and wait until it says *Live*.
4. Open your `https://something.onrender.com` link in the Quest Browser and tap **Enter VR**.
   The HUD says "N online" when multiplayer is connected ("solo mode" means it isn't).
5. Friends open the same link. Walk to the computer in the plaza, type the same code on both headsets
   (3-8 letters/numbers), hit **JOIN** – you now see each other and can play tag.

Free Render servers fall asleep after ~15 minutes of nobody using them. The first visit after that
takes up to a minute to wake up; the game keeps retrying by itself.

## Install as an app on the Quest
Open your Render link in the Quest Browser, then use the browser menu → **Add to Home / Install**.

## Make an APK
See **APK-GUIDE.md** (PWABuilder -> Meta Quest -> SideQuest).

## Put it on itch.io instead
1. Open `public/index.html` in a text editor and change `const CONFIG_WS='';` to
   `const CONFIG_WS='wss://YOUR-APP.onrender.com/ws';`
2. Zip the contents of the `public` folder (so `index.html` is at the top of the zip).
3. On itch.io: Create new project → Kind of project: **HTML** → upload the zip → tick
   "This file will be played in the browser". Whether VR mode works inside itch's frame depends on
   its settings, so also test the direct Render link.

## Test on your own computer
`python server.py` then open http://localhost:8080 (game) – open it in two browser tabs to see two players.

## Notes
- Room codes create private rooms of up to 12 players. Anyone who knows a code can join it.
- Tag results are decided on the players' own devices (no cheat protection) – fine for friends.
- Promo codes and coins are stored in each player's browser only.
