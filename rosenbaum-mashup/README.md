# Rosenbaum Jumble

One chaotic browser toy that mashes up the public repos on
[github.com/ericrosenbaum](https://github.com/ericrosenbaum) into a single shared
canvas and sound engine. It's a single file (`index.html`) with no build step and no dependencies.

## Run it

Open `index.html` in Chrome, or serve the folder so the mic and speech features work:

```bash
npx http-server rosenbaum-mashup
```

Press **Start the sound**, then:

- **Tap the floor** to drop a bell (pitch comes from its height). Drag to retune. Double-tap to remove.
- **Q–U** and **Z–M** play the mirrored duet pads.
- **Arrow keys / Space** play the sampler (record 2 s, load a file, or use the robot burble).
- **K** plays the color under the cursor as a chord. **L** launches the laser ship. **P** transmogrifies.

## What came from where

| Repo | Became |
|---|---|
| experiments (assemble) | Charged wedge molecules in a heat bath that bond into rings; each bond plays a note |
| melodymorph | Bells you place on the canvas, pitch by height |
| MK-1 | 2-second sampler with a waveform strip |
| wonderkey | Each key triggers a random slice of the sample at one pitch |
| duet-instrument, together-apart | Two mirrored rows of seven pentatonic pads, panned left/right |
| tone-synth-extension | Synth settings + bouncing synth balls that drop in now and then |
| scratch-extensions (BeetleBlocks) | A swarm of bugs (beetles, ladybugs, fireflies that blink notes, stag beetles that shove molecules) that leave blocks and lay bells |
| color-key | Colors → chords |
| user-count-extension | "Bonded right now" counter + a rare airhorn on big bond milestones |
| spotify-extension | Its examples were cowbell remixes → a beat stepper that runs as the backdrop, with **More cowbell** |
| freesound-extension | Load any sound file into the sampler |
| makeymakey-midi | MIDI out for every note |
| makeymakey-capsense-keyboard | Hovering a bell rings it (touch without ground) |
| list-app, do-today | The "Do today" checklist (checking one off spawns molecules) |
| Space-battle | Laser ships that fly by every several seconds and blow up molecules in their path |
| Transmogrifier | One button that remixes every setting |
| wordcloud (this repo) | Typed/spoken words float in and grow with repetition |

Left out on purpose: `stars-and-stories` (a private archive of family bedtime
stories), and the Arduino/CircuitPython/iOS code, which can't run in a browser. Those
projects show up as ideas, not code.

All code here is newly written. None of it is copied from those repos, most of which have no license.
