# Submission form: copy-paste text

## Track
**People.** It covers *Safety and security* and *Getting around (mobility)*.
Choosing People over Planet: our problem is about residents' safety, comfort and their daily trips on township roads. A "less material wasted through preventive repair" angle exists, but it is secondary.

## Project Title
JalanSense: Fleet-Powered Pothole Detection for Safer Township Roads

## Project Description
(about 330 words, paste as is)

Uneven, rough and potholed roads are one of the most visible everyday problems in growing townships like City of Elmina. Heavy construction traffic and tropical rain damage road surfaces quickly. Today, defects are usually found only after a resident complains or during a periodic manual inspection. By then, cars have been damaged, motorcyclists and cyclists have been put at risk, and the estate team is reacting instead of preventing.

JalanSense turns the vehicles a township already operates (shuttle buses, security patrols, waste trucks and landscaping vans) into continuous road inspectors. Each vehicle carries a low-cost IoT node of about RM70–110: an ESP32 microcontroller, an MPU6050 motion sensor and GPS. Residents can also join by using our phone "drive mode", with no extra hardware.

The node samples vibration 50 times per second. When it feels a jolt, an on-device machine-learning model classifies it as a pothole, a speed bump or a rough surface. Speed bumps and normal rough patches are filtered out on the device, so only real potholes are sent, with GPS location and a 1–5 severity score.

In the cloud, events within 15 m are clustered into a single hotspot. A hotspot is marked verified once two different vehicles hit it. Hotspots are ranked by severity, number of hits and age. The estate dashboard shows a live road-condition map and a repair priority queue. Staff raise work orders and mark defects as repaired. If fleet vehicles hit the same spot again, the hotspot automatically re-opens, so a failed repair is caught and can be claimed against the contractor's warranty.

Mechanism: continuous, automatic detection → verified, prioritised repairs → measured repair quality.
Enabler: edge AI on cheap IoT nodes, crowd-verification across the fleet, and a cloud dashboard that scales to every SDP township without new infrastructure.

Pilot: 5–10 Elmina fleet vehicles for 8 weeks. We will measure detection accuracy against manual inspection, time from detection to repair, and resident complaints compared with before the pilot.

## Presentation Slides
Upload the PDF exported from the pitch deck.

## Pitching Video
Upload to YouTube as **Unlisted**, not Private, so judges can open it. Paste the link. See `video-script.md`.

## Prototype Link
https://sykrmzffr.github.io/SDPHACKATHON-POTHOLE-DETECTOR/

## Github Repository
https://github.com/sykrmzffr/SDPHACKATHON-POTHOLE-DETECTOR

## Additional Files (optional)
- `ml/results/confusion_matrix.png`
- Survey summary, if you collect responses tonight
