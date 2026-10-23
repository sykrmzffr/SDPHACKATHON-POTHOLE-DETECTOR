# Pitching video: about 3 minutes

Format: slides plus screen recording, with all 3 members on camera for at least a few seconds.
Record with OBS, Zoom or Google Meet ("record"), or a phone. Upload to YouTube as **Unlisted**.

| Time | Who | On screen | Say |
|---|---|---|---|
| 0:00–0:20 | Faris | Title slide, all 3 faces | "Hi, we're Zeeq, Syakir and Faris from UiTM. Our idea is JalanSense: it turns the vehicles a township already runs into road inspectors that find potholes before residents do." |
| 0:20–0:50 | Faris | Problem slides | "In growing townships like Elmina, construction traffic and heavy rain wear roads down fast. Today, defects are found when someone complains or when an inspector happens to pass. Nationally, MyJalan received more than 40,000 road complaints in two years, and about 70% had to be redirected to other road owners. Township roads need their own early-warning loop." |
| 0:50–1:20 | Syakir | Hardware close-up: press BOOT, LED blinks, serial monitor shows `[pothole]` | "Each shuttle, patrol car or waste truck gets this node. It's an ESP32, a motion sensor and GPS, for under RM110. It samples vibration 50 times a second. An on-device ML model decides whether a jolt was a pothole, a speed bump or a rough road. Only real potholes are sent." |
| 1:20–2:10 | Zeeq | Dashboard: click *Simulate fleet drive*, show the feed, click a hotspot, *Raise work order*, *Mark repaired* | "Here's the estate dashboard for Elmina. A shuttle drives its route, and potholes appear live with severity scores. Hits within 15 metres merge into one hotspot, and two different vehicles confirm it. The team gets a ranked repair queue. They raise a work order and mark it repaired, and if our vehicles hit the same spot again, it re-opens automatically. That's evidence that the repair failed." |
| 2:10–2:25 | Zeeq | Phone drive mode, *Test: pothole* and *Test: speed bump* | "Residents can join too. Any phone becomes a sensor, and speed bumps are filtered out." |
| 2:25–2:50 | Faris | Impact and pilot slide | "Our pilot is 5 to 10 Elmina fleet vehicles for 8 weeks. We'll measure accuracy against manual inspection, time from detection to repair, and complaint volume. Because it rides on existing fleets, it scales to every SDP township with no new infrastructure." |
| 2:50–3:00 | All | Closing slide | "JalanSense: safer roads, found first. Thank you!" |

Tips: record the dashboard at 1080p with browser zoom at 90%. Do one dry run, then record. Don't try for a perfect take. A clear take submitted on time beats a polished one submitted late.
