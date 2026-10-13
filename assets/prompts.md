# Image requests

30 images requested, 0 delivered. Regenerate this file with `make interim` after adding files.

These are design-time assets. Save each file at the path given and it is picked up on the next request: anything in `assets/generated` wins over the code-drawn file of the same name in `assets/interim`, one file at a time. Both the API (stamps and postmark, composited into postcards) and the web app (`/art/...`) follow that rule.

The postcard pictures themselves are not in this list. They are made at runtime, once per postcard, by the image provider (the built-in painter unless `IMAGE_PROVIDER` says otherwise). All lettering on a postcard is set by the template in code.

**Style bible:** vintage travel postcard, gouache look, a stamp in the corner and a postmark with the date and city name.

**Palette:** `#e2583a` `#1d2440` `#f6f0e1` `#73b6cf` `#2f86a8` `#559b82` `#e6c684` `#f8d368`

## SP-001 rain stamp

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** Vintage travel postcard illustration painted in gouache: flat opaque colour, visible dry-brush texture, soft uneven edges, matte finish, simple bold shapes, mid-century travel poster composition. Limited palette: vermilion #e2583a, ink navy #1d2440, cream #f6f0e1, sky blue #73b6cf, teal #2f86a8, sage #559b82, ochre #e6c684, warm yellow #f8d368. No text, no lettering, no numbers, no watermark. A postage stamp with a perforated edge and a cream paper margin, seen flat from the front. Inside its thin navy frame: a small figure in a dark coat under a red umbrella, light rain streaks, one flat grey cloud. Leave a blank cream band along the bottom tenth of the stamp, inside the perforations: the app prints the stamp's value there.
- **Spec:** 300x372 px, about 4:5, transparent outside the perforated edge, PNG.
- **Save to:** `assets/generated/stamps/rain.png`
- **Used for:** The stamp on every postcard whose strongest sound is "Rain". Without it the code-drawn stamp is used.

## SP-002 thunder stamp

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** Vintage travel postcard illustration painted in gouache: flat opaque colour, visible dry-brush texture, soft uneven edges, matte finish, simple bold shapes, mid-century travel poster composition. Limited palette: vermilion #e2583a, ink navy #1d2440, cream #f6f0e1, sky blue #73b6cf, teal #2f86a8, sage #559b82, ochre #e6c684, warm yellow #f8d368. No text, no lettering, no numbers, no watermark. A postage stamp with a perforated edge and a cream paper margin, seen flat from the front. Inside its thin navy frame: a dark flat-bottomed cloud with one yellow lightning bolt over a low horizon. Leave a blank cream band along the bottom tenth of the stamp, inside the perforations: the app prints the stamp's value there.
- **Spec:** 300x372 px, about 4:5, transparent outside the perforated edge, PNG.
- **Save to:** `assets/generated/stamps/storm.png`
- **Used for:** The stamp on every postcard whose strongest sound is "Thunder". Without it the code-drawn stamp is used.

## SP-003 running water stamp

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** Vintage travel postcard illustration painted in gouache: flat opaque colour, visible dry-brush texture, soft uneven edges, matte finish, simple bold shapes, mid-century travel poster composition. Limited palette: vermilion #e2583a, ink navy #1d2440, cream #f6f0e1, sky blue #73b6cf, teal #2f86a8, sage #559b82, ochre #e6c684, warm yellow #f8d368. No text, no lettering, no numbers, no watermark. A postage stamp with a perforated edge and a cream paper margin, seen flat from the front. Inside its thin navy frame: a stone fountain with two arcs of water falling into a round basin. Leave a blank cream band along the bottom tenth of the stamp, inside the perforations: the app prints the stamp's value there.
- **Spec:** 300x372 px, about 4:5, transparent outside the perforated edge, PNG.
- **Save to:** `assets/generated/stamps/water.png`
- **Used for:** The stamp on every postcard whose strongest sound is "Running water". Without it the code-drawn stamp is used.

## SP-004 waves stamp

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** Vintage travel postcard illustration painted in gouache: flat opaque colour, visible dry-brush texture, soft uneven edges, matte finish, simple bold shapes, mid-century travel poster composition. Limited palette: vermilion #e2583a, ink navy #1d2440, cream #f6f0e1, sky blue #73b6cf, teal #2f86a8, sage #559b82, ochre #e6c684, warm yellow #f8d368. No text, no lettering, no numbers, no watermark. A postage stamp with a perforated edge and a cream paper margin, seen flat from the front. Inside its thin navy frame: a small sailboat with one red and one white sail on a blue sea with white wave strokes. Leave a blank cream band along the bottom tenth of the stamp, inside the perforations: the app prints the stamp's value there.
- **Spec:** 300x372 px, about 4:5, transparent outside the perforated edge, PNG.
- **Save to:** `assets/generated/stamps/waves.png`
- **Used for:** The stamp on every postcard whose strongest sound is "Waves". Without it the code-drawn stamp is used.

## SP-005 wind stamp

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** Vintage travel postcard illustration painted in gouache: flat opaque colour, visible dry-brush texture, soft uneven edges, matte finish, simple bold shapes, mid-century travel poster composition. Limited palette: vermilion #e2583a, ink navy #1d2440, cream #f6f0e1, sky blue #73b6cf, teal #2f86a8, sage #559b82, ochre #e6c684, warm yellow #f8d368. No text, no lettering, no numbers, no watermark. A postage stamp with a perforated edge and a cream paper margin, seen flat from the front. Inside its thin navy frame: a red and yellow diamond kite with a ribbon tail, one white swirl of wind. Leave a blank cream band along the bottom tenth of the stamp, inside the perforations: the app prints the stamp's value there.
- **Spec:** 300x372 px, about 4:5, transparent outside the perforated edge, PNG.
- **Save to:** `assets/generated/stamps/wind.png`
- **Used for:** The stamp on every postcard whose strongest sound is "Wind". Without it the code-drawn stamp is used.

## SP-006 birdsong stamp

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** Vintage travel postcard illustration painted in gouache: flat opaque colour, visible dry-brush texture, soft uneven edges, matte finish, simple bold shapes, mid-century travel poster composition. Limited palette: vermilion #e2583a, ink navy #1d2440, cream #f6f0e1, sky blue #73b6cf, teal #2f86a8, sage #559b82, ochre #e6c684, warm yellow #f8d368. No text, no lettering, no numbers, no watermark. A postage stamp with a perforated edge and a cream paper margin, seen flat from the front. Inside its thin navy frame: a plump dark bird with a red beak perched on a wire, two small birds flying far off. Leave a blank cream band along the bottom tenth of the stamp, inside the perforations: the app prints the stamp's value there.
- **Spec:** 300x372 px, about 4:5, transparent outside the perforated edge, PNG.
- **Save to:** `assets/generated/stamps/birds.png`
- **Used for:** The stamp on every postcard whose strongest sound is "Birdsong". Without it the code-drawn stamp is used.

## SP-007 insects stamp

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** Vintage travel postcard illustration painted in gouache: flat opaque colour, visible dry-brush texture, soft uneven edges, matte finish, simple bold shapes, mid-century travel poster composition. Limited palette: vermilion #e2583a, ink navy #1d2440, cream #f6f0e1, sky blue #73b6cf, teal #2f86a8, sage #559b82, ochre #e6c684, warm yellow #f8d368. No text, no lettering, no numbers, no watermark. A postage stamp with a perforated edge and a cream paper margin, seen flat from the front. Inside its thin navy frame: tall dark grass at night with five glowing fireflies, deep navy sky. Leave a blank cream band along the bottom tenth of the stamp, inside the perforations: the app prints the stamp's value there.
- **Spec:** 300x372 px, about 4:5, transparent outside the perforated edge, PNG.
- **Save to:** `assets/generated/stamps/insects.png`
- **Used for:** The stamp on every postcard whose strongest sound is "Insects". Without it the code-drawn stamp is used.

## SP-008 animals stamp

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** Vintage travel postcard illustration painted in gouache: flat opaque colour, visible dry-brush texture, soft uneven edges, matte finish, simple bold shapes, mid-century travel poster composition. Limited palette: vermilion #e2583a, ink navy #1d2440, cream #f6f0e1, sky blue #73b6cf, teal #2f86a8, sage #559b82, ochre #e6c684, warm yellow #f8d368. No text, no lettering, no numbers, no watermark. A postage stamp with a perforated edge and a cream paper margin, seen flat from the front. Inside its thin navy frame: one white woolly sheep with a dark face standing on a field. Leave a blank cream band along the bottom tenth of the stamp, inside the perforations: the app prints the stamp's value there.
- **Spec:** 300x372 px, about 4:5, transparent outside the perforated edge, PNG.
- **Save to:** `assets/generated/stamps/animals.png`
- **Used for:** The stamp on every postcard whose strongest sound is "Animals". Without it the code-drawn stamp is used.

## SP-009 traffic stamp

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** Vintage travel postcard illustration painted in gouache: flat opaque colour, visible dry-brush texture, soft uneven edges, matte finish, simple bold shapes, mid-century travel poster composition. Limited palette: vermilion #e2583a, ink navy #1d2440, cream #f6f0e1, sky blue #73b6cf, teal #2f86a8, sage #559b82, ochre #e6c684, warm yellow #f8d368. No text, no lettering, no numbers, no watermark. A postage stamp with a perforated edge and a cream paper margin, seen flat from the front. Inside its thin navy frame: a small rounded red car seen from the side on a dark road. Leave a blank cream band along the bottom tenth of the stamp, inside the perforations: the app prints the stamp's value there.
- **Spec:** 300x372 px, about 4:5, transparent outside the perforated edge, PNG.
- **Save to:** `assets/generated/stamps/traffic.png`
- **Used for:** The stamp on every postcard whose strongest sound is "Traffic". Without it the code-drawn stamp is used.

## SP-010 trains stamp

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** Vintage travel postcard illustration painted in gouache: flat opaque colour, visible dry-brush texture, soft uneven edges, matte finish, simple bold shapes, mid-century travel poster composition. Limited palette: vermilion #e2583a, ink navy #1d2440, cream #f6f0e1, sky blue #73b6cf, teal #2f86a8, sage #559b82, ochre #e6c684, warm yellow #f8d368. No text, no lettering, no numbers, no watermark. A postage stamp with a perforated edge and a cream paper margin, seen flat from the front. Inside its thin navy frame: a small steam locomotive pulling red carriages, puffs of white smoke. Leave a blank cream band along the bottom tenth of the stamp, inside the perforations: the app prints the stamp's value there.
- **Spec:** 300x372 px, about 4:5, transparent outside the perforated edge, PNG.
- **Save to:** `assets/generated/stamps/train.png`
- **Used for:** The stamp on every postcard whose strongest sound is "Trains". Without it the code-drawn stamp is used.

## SP-011 aircraft stamp

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** Vintage travel postcard illustration painted in gouache: flat opaque colour, visible dry-brush texture, soft uneven edges, matte finish, simple bold shapes, mid-century travel poster composition. Limited palette: vermilion #e2583a, ink navy #1d2440, cream #f6f0e1, sky blue #73b6cf, teal #2f86a8, sage #559b82, ochre #e6c684, warm yellow #f8d368. No text, no lettering, no numbers, no watermark. A postage stamp with a perforated edge and a cream paper margin, seen flat from the front. Inside its thin navy frame: a white airliner with a red tail climbing to the right, two thin contrails. Leave a blank cream band along the bottom tenth of the stamp, inside the perforations: the app prints the stamp's value there.
- **Spec:** 300x372 px, about 4:5, transparent outside the perforated edge, PNG.
- **Save to:** `assets/generated/stamps/aircraft.png`
- **Used for:** The stamp on every postcard whose strongest sound is "Aircraft". Without it the code-drawn stamp is used.

## SP-012 bells stamp

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** Vintage travel postcard illustration painted in gouache: flat opaque colour, visible dry-brush texture, soft uneven edges, matte finish, simple bold shapes, mid-century travel poster composition. Limited palette: vermilion #e2583a, ink navy #1d2440, cream #f6f0e1, sky blue #73b6cf, teal #2f86a8, sage #559b82, ochre #e6c684, warm yellow #f8d368. No text, no lettering, no numbers, no watermark. A postage stamp with a perforated edge and a cream paper margin, seen flat from the front. Inside its thin navy frame: a single large golden bell with a clapper, curved lines of sound either side, dusk sky. Leave a blank cream band along the bottom tenth of the stamp, inside the perforations: the app prints the stamp's value there.
- **Spec:** 300x372 px, about 4:5, transparent outside the perforated edge, PNG.
- **Save to:** `assets/generated/stamps/bells.png`
- **Used for:** The stamp on every postcard whose strongest sound is "Bells". Without it the code-drawn stamp is used.

## SP-013 music stamp

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** Vintage travel postcard illustration painted in gouache: flat opaque colour, visible dry-brush texture, soft uneven edges, matte finish, simple bold shapes, mid-century travel poster composition. Limited palette: vermilion #e2583a, ink navy #1d2440, cream #f6f0e1, sky blue #73b6cf, teal #2f86a8, sage #559b82, ochre #e6c684, warm yellow #f8d368. No text, no lettering, no numbers, no watermark. A postage stamp with a perforated edge and a cream paper margin, seen flat from the front. Inside its thin navy frame: two joined musical quavers in cream on a dusk sky of purple and orange bands. Leave a blank cream band along the bottom tenth of the stamp, inside the perforations: the app prints the stamp's value there.
- **Spec:** 300x372 px, about 4:5, transparent outside the perforated edge, PNG.
- **Save to:** `assets/generated/stamps/music.png`
- **Used for:** The stamp on every postcard whose strongest sound is "Music". Without it the code-drawn stamp is used.

## SP-014 bustle stamp

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** Vintage travel postcard illustration painted in gouache: flat opaque colour, visible dry-brush texture, soft uneven edges, matte finish, simple bold shapes, mid-century travel poster composition. Limited palette: vermilion #e2583a, ink navy #1d2440, cream #f6f0e1, sky blue #73b6cf, teal #2f86a8, sage #559b82, ochre #e6c684, warm yellow #f8d368. No text, no lettering, no numbers, no watermark. A postage stamp with a perforated edge and a cream paper margin, seen flat from the front. Inside its thin navy frame: a market stall with a red and cream striped awning and a counter heaped with fruit. Leave a blank cream band along the bottom tenth of the stamp, inside the perforations: the app prints the stamp's value there.
- **Spec:** 300x372 px, about 4:5, transparent outside the perforated edge, PNG.
- **Save to:** `assets/generated/stamps/market.png`
- **Used for:** The stamp on every postcard whose strongest sound is "Bustle". Without it the code-drawn stamp is used.

## SP-015 cafe clatter stamp

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** Vintage travel postcard illustration painted in gouache: flat opaque colour, visible dry-brush texture, soft uneven edges, matte finish, simple bold shapes, mid-century travel poster composition. Limited palette: vermilion #e2583a, ink navy #1d2440, cream #f6f0e1, sky blue #73b6cf, teal #2f86a8, sage #559b82, ochre #e6c684, warm yellow #f8d368. No text, no lettering, no numbers, no watermark. A postage stamp with a perforated edge and a cream paper margin, seen flat from the front. Inside its thin navy frame: a white coffee cup on a red saucer with two curls of steam. Leave a blank cream band along the bottom tenth of the stamp, inside the perforations: the app prints the stamp's value there.
- **Spec:** 300x372 px, about 4:5, transparent outside the perforated edge, PNG.
- **Save to:** `assets/generated/stamps/cafe.png`
- **Used for:** The stamp on every postcard whose strongest sound is "Cafe clatter". Without it the code-drawn stamp is used.

## SP-016 footsteps stamp

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** Vintage travel postcard illustration painted in gouache: flat opaque colour, visible dry-brush texture, soft uneven edges, matte finish, simple bold shapes, mid-century travel poster composition. Limited palette: vermilion #e2583a, ink navy #1d2440, cream #f6f0e1, sky blue #73b6cf, teal #2f86a8, sage #559b82, ochre #e6c684, warm yellow #f8d368. No text, no lettering, no numbers, no watermark. A postage stamp with a perforated edge and a cream paper margin, seen flat from the front. Inside its thin navy frame: a small figure in a red coat walking, seen from behind, on a pale path. Leave a blank cream band along the bottom tenth of the stamp, inside the perforations: the app prints the stamp's value there.
- **Spec:** 300x372 px, about 4:5, transparent outside the perforated edge, PNG.
- **Save to:** `assets/generated/stamps/footsteps.png`
- **Used for:** The stamp on every postcard whose strongest sound is "Footsteps". Without it the code-drawn stamp is used.

## SP-017 fire stamp

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** Vintage travel postcard illustration painted in gouache: flat opaque colour, visible dry-brush texture, soft uneven edges, matte finish, simple bold shapes, mid-century travel poster composition. Limited palette: vermilion #e2583a, ink navy #1d2440, cream #f6f0e1, sky blue #73b6cf, teal #2f86a8, sage #559b82, ochre #e6c684, warm yellow #f8d368. No text, no lettering, no numbers, no watermark. A postage stamp with a perforated edge and a cream paper margin, seen flat from the front. Inside its thin navy frame: a campfire of crossed logs with red, yellow and cream flames and sparks at night. Leave a blank cream band along the bottom tenth of the stamp, inside the perforations: the app prints the stamp's value there.
- **Spec:** 300x372 px, about 4:5, transparent outside the perforated edge, PNG.
- **Save to:** `assets/generated/stamps/fire.png`
- **Used for:** The stamp on every postcard whose strongest sound is "Fire". Without it the code-drawn stamp is used.

## SP-018 fireworks stamp

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** Vintage travel postcard illustration painted in gouache: flat opaque colour, visible dry-brush texture, soft uneven edges, matte finish, simple bold shapes, mid-century travel poster composition. Limited palette: vermilion #e2583a, ink navy #1d2440, cream #f6f0e1, sky blue #73b6cf, teal #2f86a8, sage #559b82, ochre #e6c684, warm yellow #f8d368. No text, no lettering, no numbers, no watermark. A postage stamp with a perforated edge and a cream paper margin, seen flat from the front. Inside its thin navy frame: one large firework burst of gold and red rays in a navy night sky. Leave a blank cream band along the bottom tenth of the stamp, inside the perforations: the app prints the stamp's value there.
- **Spec:** 300x372 px, about 4:5, transparent outside the perforated edge, PNG.
- **Save to:** `assets/generated/stamps/fireworks.png`
- **Used for:** The stamp on every postcard whose strongest sound is "Fireworks". Without it the code-drawn stamp is used.

## SP-019 works stamp

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** Vintage travel postcard illustration painted in gouache: flat opaque colour, visible dry-brush texture, soft uneven edges, matte finish, simple bold shapes, mid-century travel poster composition. Limited palette: vermilion #e2583a, ink navy #1d2440, cream #f6f0e1, sky blue #73b6cf, teal #2f86a8, sage #559b82, ochre #e6c684, warm yellow #f8d368. No text, no lettering, no numbers, no watermark. A postage stamp with a perforated edge and a cream paper margin, seen flat from the front. Inside its thin navy frame: a red tower crane with a hook and a hanging load against a blue sky. Leave a blank cream band along the bottom tenth of the stamp, inside the perforations: the app prints the stamp's value there.
- **Spec:** 300x372 px, about 4:5, transparent outside the perforated edge, PNG.
- **Save to:** `assets/generated/stamps/works.png`
- **Used for:** The stamp on every postcard whose strongest sound is "Works". Without it the code-drawn stamp is used.

## SP-020 hum stamp

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** Vintage travel postcard illustration painted in gouache: flat opaque colour, visible dry-brush texture, soft uneven edges, matte finish, simple bold shapes, mid-century travel poster composition. Limited palette: vermilion #e2583a, ink navy #1d2440, cream #f6f0e1, sky blue #73b6cf, teal #2f86a8, sage #559b82, ochre #e6c684, warm yellow #f8d368. No text, no lettering, no numbers, no watermark. A postage stamp with a perforated edge and a cream paper margin, seen flat from the front. Inside its thin navy frame: a pale yellow sun over two calm rolling hills, nothing else. Leave a blank cream band along the bottom tenth of the stamp, inside the perforations: the app prints the stamp's value there.
- **Spec:** 300x372 px, about 4:5, transparent outside the perforated edge, PNG.
- **Save to:** `assets/generated/stamps/hum.png`
- **Used for:** The stamp on every postcard whose strongest sound is "Hum". Without it the code-drawn stamp is used.

## SP-021 blank postmark

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** A blank rubber-stamp postmark in black ink on a transparent background, seen flat. On the left, two concentric circles: a heavy outer ring and a thinner inner ring with a clear gap between them. On the right, six parallel wavy cancellation lines running away from the circles. The ink is uneven and slightly worn, as a real hand stamp prints. Nothing inside the rings and no lettering anywhere: the app sets the city and date itself.
- **Spec:** 760x400 px, 19:10, transparent background, single colour (black or #1d2440), PNG. Outer ring about 368 px across, centred 200 px from the left edge.
- **Save to:** `assets/generated/postmark/ring.png`
- **Used for:** Printed over the top right of every postcard, under the city, date and time of day that the template adds.

## SP-022 logo

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** App mark, flat vector look with a faint gouache grain: a vermilion #e2583a postage stamp with a perforated edge. Inside a thin cream #f6f0e1 rounded frame, seven vertical cream bars of different heights form a sound waveform, tallest in the middle. No text.
- **Spec:** 512x512 px, 1:1, transparent background, PNG.
- **Save to:** `assets/generated/brand/logo.png`
- **Used for:** The mark next to the name in the header of every page.

## SP-023 app icon 192

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** The same mark as SP-022 (vermilion perforated stamp, cream frame, seven-bar waveform), centred, no text.
- **Spec:** 192x192 px, 1:1, transparent background, PNG.
- **Save to:** `assets/generated/brand/icon-192.png`
- **Used for:** Favicon, Apple touch icon and installed app icon.

## SP-024 app icon 512

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** The same mark as SP-022 (vermilion perforated stamp, cream frame, seven-bar waveform), centred, no text.
- **Spec:** 512x512 px, 1:1, transparent background, PNG.
- **Save to:** `assets/generated/brand/icon-512.png`
- **Used for:** Favicon, Apple touch icon and installed app icon.

## SP-025 maskable app icon

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** The waveform and cream frame of SP-022 on a full-bleed vermilion #e2583a square with no perforations, the frame kept inside the middle 60% so that a circular mask does not cut it. No text.
- **Spec:** 512x512 px, 1:1, opaque, PNG.
- **Save to:** `assets/generated/brand/icon-maskable-512.png`
- **Used for:** Android adaptive icon.

## SP-026 onboarding: listen

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** Vintage travel postcard illustration painted in gouache: flat opaque colour, visible dry-brush texture, soft uneven edges, matte finish, simple bold shapes, mid-century travel poster composition. Limited palette: vermilion #e2583a, ink navy #1d2440, cream #f6f0e1, sky blue #73b6cf, teal #2f86a8, sage #559b82, ochre #e6c684, warm yellow #f8d368. No text, no lettering, no numbers, no watermark. A sunny meadow path with a cafe table under a striped red and cream parasol, a few small birds on a fence and a flock in a bright blue sky. Calm, inviting, daytime.
- **Spec:** 720x540 px, 4:3, arched top (a rounded arch window shape) on a transparent background, PNG.
- **Save to:** `assets/generated/onboarding/listen.png`
- **Used for:** First step of the welcome sheet and the About page: listen for ten seconds.

## SP-027 onboarding: place

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** Vintage travel postcard illustration painted in gouache: flat opaque colour, visible dry-brush texture, soft uneven edges, matte finish, simple bold shapes, mid-century travel poster composition. Limited palette: vermilion #e2583a, ink navy #1d2440, cream #f6f0e1, sky blue #73b6cf, teal #2f86a8, sage #559b82, ochre #e6c684, warm yellow #f8d368. No text, no lettering, no numbers, no watermark. A calm bay at dawn with a rising sun, two small sailboats, a striped lighthouse on a headland and a sandy beach. A large vermilion map pin with a cream dot stands in the middle of the water.
- **Spec:** 720x540 px, 4:3, arched top on a transparent background, PNG.
- **Save to:** `assets/generated/onboarding/place.png`
- **Used for:** Second step: pin it, roughly. Also the empty state of the Nearby tab before a location is shared.

## SP-028 onboarding: send

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** Vintage travel postcard illustration painted in gouache: flat opaque colour, visible dry-brush texture, soft uneven edges, matte finish, simple bold shapes, mid-century travel poster composition. Limited palette: vermilion #e2583a, ink navy #1d2440, cream #f6f0e1, sky blue #73b6cf, teal #2f86a8, sage #559b82, ochre #e6c684, warm yellow #f8d368. No text, no lettering, no numbers, no watermark. A steam train crossing a stone viaduct at dusk, orange and purple sky, a low sun, white swirls of wind and a few falling leaves.
- **Spec:** 720x540 px, 4:3, arched top on a transparent background, PNG.
- **Save to:** `assets/generated/onboarding/send.png`
- **Used for:** Third step: get a postcard back.

## SP-029 empty state: quiet

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** Vintage travel postcard illustration painted in gouache: flat opaque colour, visible dry-brush texture, soft uneven edges, matte finish, simple bold shapes, mid-century travel poster composition. Limited palette: vermilion #e2583a, ink navy #1d2440, cream #f6f0e1, sky blue #73b6cf, teal #2f86a8, sage #559b82, ochre #e6c684, warm yellow #f8d368. No text, no lettering, no numbers, no watermark. A still night landscape of dark blue rolling hills, a crescent moon, one flat cloud, a few stars, a fence and a winding path. Nobody about.
- **Spec:** 560x360 px, 14:9, rounded corners (36 px) on a transparent background, PNG.
- **Save to:** `assets/generated/empty/quiet.png`
- **Used for:** Shown when there are no postcards nearby, when a postcard link is dead, and on the offline page.

## SP-030 empty state: hush

- **Status:** requested (code-drawn interim file in use)
- **Prompt:** Vintage travel postcard illustration painted in gouache: flat opaque colour, visible dry-brush texture, soft uneven edges, matte finish, simple bold shapes, mid-century travel poster composition. Limited palette: vermilion #e2583a, ink navy #1d2440, cream #f6f0e1, sky blue #73b6cf, teal #2f86a8, sage #559b82, ochre #e6c684, warm yellow #f8d368. No text, no lettering, no numbers, no watermark. A town square at dusk with lit windows, striped awnings, a cafe table under a parasol and a market stall. Two tiny distant figures, no faces.
- **Spec:** 560x360 px, 14:9, rounded corners (36 px) on a transparent background, PNG.
- **Save to:** `assets/generated/empty/hush.png`
- **Used for:** Shown next to the message when a clip is refused for being mostly speech.
