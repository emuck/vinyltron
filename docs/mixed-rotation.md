# Mixed Rotation

Select **Mixed Rotation** under **Idle Mode** and save. In the **Mixed Rotation**
section, enable the categories you want and choose a **Slot Duration** (minimum five
seconds) and **Order**, then save.

- **Photos:** one random image from Idle Folder per slot; default image if empty.
- **Screensavers:** the engine and palette selected in Screensaver settings. Their
  Random options pick new choices whenever a screensaver slot starts.
- **Weather:** the display configured in Weather settings.
- **Current Album Art:** eligible only during active playback with available artwork.
  This can participate even with Volumio Artwork disabled, which disables the initial
  artwork interruption rather than the category switch.

Sequential follows the order above, skipping disabled or unavailable categories.
Shuffle visits each available category once per round in random order and avoids
immediate repeats across rounds when possible. Newly available artwork joins the next
round. A single eligible category may repeat. If nothing is eligible, show the default
image until a category becomes available.

The slot duration owns all mixed-mode transitions. Photo Interval and Screensaver Reset
Interval still apply in their fixed modes, but do not run inside Mixed Rotation.
Weather and screensaver animation speeds remain independent of slot duration.

With Volumio Artwork enabled, a new album interrupts rotation for **Album Art Duration**,
then rotation resumes with the next category and a fresh slot. Tracks from the same
album do not interrupt or extend the window. Set duration greater than zero to rotate
during playback; `0` retains continuous album art while playing or paused. Pausing or
stopping playback ends an album-art rotation slot immediately. Unavailable art is skipped.

The master Display On switch and daily schedule still apply. Only active playback with
Volumio Artwork enabled overrides the schedule; paused and stopped playback obey it.

Run scheduler regression checks with `python3 tools/test-mixed-rotation.py` (Python 3.11+,
Pillow, and requests). Tests substitute hardware, networking, and timers; they do not
connect to the Pi or change its settings.
Run `node tools/test-mixed-rotation.js` to verify settings persistence and UI hydration
against in-memory files and configuration.
