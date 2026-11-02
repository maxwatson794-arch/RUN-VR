# Turn RUN into an APK for your Quest

An APK is just a wrapper that opens your hosted game, so first do the hosting steps in README.md
(your game must be live on an https link, e.g. https://something.onrender.com).

## A. One-time headset setup (needed to install any APK)
1. Make a free Meta developer account at developers.meta.com and join/create an organization.
2. On your phone, open the **Meta Horizon** app -> Devices -> your headset -> **Developer Mode** -> turn on.
3. Restart the headset. (Menu names change between versions; search "enable developer mode Quest" if they differ.)

## B. Build the APK (no coding, runs in your browser)
1. Go to **pwabuilder.com** and paste your https link, press **Start**.
2. Wait for the report. This package already has the manifest, icons (including a maskable one),
   and a service worker, so it should pass.
3. Press **Package for Stores** -> choose **Meta Quest** -> fill the form (keep the defaults, package ID like
   `com.yourname.runvr`) -> **Generate** -> download the zip.
4. Inside the zip is the `.apk` and a signing key file. **Keep the key safe** – you need it for updates.

## C. Install it on the headset
1. On a PC, install **SideQuest** (sidequestvr.com) and connect the Quest with a USB-C cable.
   Allow USB debugging inside the headset when it asks.
2. In SideQuest, drag the `.apk` onto the window (or use the install-APK button).
3. In the headset: Library -> filter **Unknown Sources** -> open **RUN**.

## D. Share it
- **itch.io:** create a project, upload the `.apk` as a download file and tick Android. Friends must
  sideload it the same way as in step C (they also need developer mode).
- Friends who don't want to sideload can just open your https link in the Quest Browser.

## Good to know
- The APK loads your hosted site, so the Render server must be running for multiplayer. Changes you
  upload to the site show up in the app without rebuilding it.
- Render's free plan sleeps when idle; the first launch after a while can take up to a minute to connect.
- I (Claude) can't build the APK myself – it needs Android build tools that PWABuilder runs for you.
