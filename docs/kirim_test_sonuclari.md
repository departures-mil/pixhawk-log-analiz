# Gerçek kırım logları ile teşhis doğruluğu

Kaynak: discuss.ardupilot.org kamuya açık konular · Tarih: 2026-11-24 14:19 · Log sayısı: 323 (+3 okunamayan)

Etiket kaynağı: **uzman etiketleri** — her konudaki deneyimli/ekip üyelerinin yanıtları elle okunarak kırım/normal ve kök neden belirlendi (tools_data/crashbench/labels.json). Kök neden puanı yalnız uzmanların bir nedende birleştiği kırımlar üzerinden hesaplanır.

| Ölçüt | Değer |
|---|---|
| Genel doğruluk (kırım/olay ↔ normal) | %81 |
| Kırımı yakalama oranı (duyarlılık) | %89 (193/217) |
| Normal uçuşu doğru tanıma (özgüllük) | %66 (70/106) |
| Kesin 'kırım' kararı verilen kırım logları | 112/217 |
| Normal logda yanlış 'kırım' kararı | 1 |
| Kök neden uyumu (ana neden) | %52 (93/178) |
| Kök neden uyumu (ana veya ikincil nedenlerde) | %67 (120/178) |

## Sürüm geçmişi

| Tarih | Sürüm / etiket | Log | Doğruluk | Duyarlılık | Özgüllük | Kök neden |
|---|---|---|---|---|---|---|
| 2026-11-23 17:08 | v1.0.4 · forum başlığı | 65 | %77 | %85 | %56 | %21 |
| 2026-11-24 04:55 | v1.0.5 · uzman | 114 | %79 | %87 | %59 | %35 |
| 2026-11-24 05:03 | v1.0.6 · uzman | 117 | %80 | %87 | %59 | %51 |
| 2026-11-24 14:19 | v1.0.8 · uzman | 323 | %81 | %89 | %66 | %52 |

## Öğrenen ikinci görüş (ML)

Aynı uzman etiketli 323 log üzerinde, her log dışarıda bırakılarak (leave-one-out) eğitilip ölçüldü. Model **kullanımda**: yalnız sınırdaki kararları düzeltir (kanıtsız 'sorunlu' → normal, model çok eminse normal → sorunlu); kesin kırım kanıtına dokunmaz.

| | Doğruluk | Duyarlılık | Özgüllük |
|---|---|---|---|
| Yalnız kurallar | %81 | %89 | %66 |
| Kurallar + model | %86 | %87 | %85 |

## Log listesi

| Konu | Araç | Etiket | Program | Kök neden (program) | Kök neden (uzman) | Süre |
|---|---|---|---|---|---|---|
| [Crash on first flight after mayor crash](https://discuss.ardupilot.org/t/crash-on-first-flight-after-mayor-crash/10063) | Copter | crash | ✅ crash | control | compass | 89 sn |
| [Crash Inspection](https://discuss.ardupilot.org/t/crash-inspection/100654) | Copter | crash | ✅ crash | motor | motor | 1127 sn |
| [*SOLVED* Agricultural Quad Crash Analysis](https://discuss.ardupilot.org/t/solved-agricultural-quad-crash-analysis/101517) | Copter | crash | ✅ crash | motor | motor | 417 sn |
| [Arducopter initial tuning and setup - Oscillation issue](https://discuss.ardupilot.org/t/arducopter-initial-tuning-and-setup-oscillation-issue/103213) | Copter | crash | ✅ crash | unknown | control | 332 sn |
| [AutoTune: failing to level](https://discuss.ardupilot.org/t/autotune-failing-to-level/104302) | Copter | crash | ✅ crash | unknown | - | 1189 sn |
| [VTOL Plane Crashed](https://discuss.ardupilot.org/t/vtol-plane-crashed/107364) | Plane | crash | ✅ crash | stall | control | 45 sn |
| [Coptor automatically begins hovering in a roughly elliptical orbit aro](https://discuss.ardupilot.org/t/coptor-automatically-begins-hovering-in-a-roughly-elliptical-orbit-around-the-takeoff-location-in-loiter-mode/107868) | Copter | crash | ✅ crash | motor | compass | 36 sn |
| [Drone Crashed - Would like to ask for assistance in analyzing the logs](https://discuss.ardupilot.org/t/drone-crashed-would-like-to-ask-for-assistance-in-analyzing-the-logs/109490) | Copter | crash | ✅ crash | motor | motor | 1123 sn |
| [Challenge: root-cause ID of crash](https://discuss.ardupilot.org/t/challenge-root-cause-id-of-crash/11603) | Copter | crash | ✅ crash | power | motor | 163 sn |
| [Quad crashed after 3.5 minutes flight. Can't figure out why](https://discuss.ardupilot.org/t/quad-crashed-after-3-5-minutes-flight-cant-figure-out-why/117102) | Copter | crash | ✅ crash | motor | motor | 608 sn |
| [Pixhawk crash after switched flight mode](https://discuss.ardupilot.org/t/pixhawk-crash-after-switched-flight-mode/11772) | Copter | crash | ✅ crash | control | motor | 67 sn |
| [Desired Pitch ignored - crashing at launch](https://discuss.ardupilot.org/t/desired-pitch-ignored-crashing-at-launch/117787) | Plane | crash | ✅ crash | control | control | 13 sn |
| [First crash with ardupilot, please help to find reason](https://discuss.ardupilot.org/t/first-crash-with-ardupilot-please-help-to-find-reason/118894) | Copter | crash | ✅ crash | gps | motor | 524 sn |
| [Sudden change in Pitch leading to a crash](https://discuss.ardupilot.org/t/sudden-change-in-pitch-leading-to-a-crash/119495) | Copter | crash | ✅ crash | motor | - | 261 sn |
| [Satellite count dropped to zero, drone crashed](https://discuss.ardupilot.org/t/satellite-count-dropped-to-zero-drone-crashed/120824) | Copter | crash | ✅ crash | motor | motor | 123 sn |
| [GPS Loss and Crash in Loiter](https://discuss.ardupilot.org/t/gps-loss-and-crash-in-loiter/121336) | Copter | crash | ✅ crash | gps | motor | 269 sn |
| [Hexacopter Crash Log Analysis Request](https://discuss.ardupilot.org/t/hexacopter-crash-log-analysis-request/121620) | Copter | crash | ✅ crash | motor | motor | 1658 sn |
| [Multi-rotor crashed suddenly while in air](https://discuss.ardupilot.org/t/multi-rotor-crashed-suddenly-while-in-air/121766) | Copter | crash | ✅ crash | control | control | 180 sn |
| [Drone logs from our third crash](https://discuss.ardupilot.org/t/drone-logs-from-our-third-crash/125310) | Copter | crash | ✅ crash | motor | compass | 1708 sn |
| [Strange erroneous position measurement causing crash](https://discuss.ardupilot.org/t/strange-erroneous-position-measurement-causing-crash/127381) | Copter | crash | ✅ crash | control | - | 532 sn |
| [Copter crash - Request for help](https://discuss.ardupilot.org/t/copter-crash-request-for-help/12771) | Copter | crash | ✅ crash | control | - | 155 sn |
| [X Quad 3.4.2 Crash - Sudden motors cut off command](https://discuss.ardupilot.org/t/x-quad-3-4-2-crash-sudden-motors-cut-off-command/13139) | Copter | crash | ✅ crash | radio | - | 1554 sn |
| [Copter flip on takeoff](https://discuss.ardupilot.org/t/copter-flip-on-takeoff/131783) | Copter | crash | ✅ crash | motor | motor | 99 sn |
| [Crash after two motors suddenly stopped](https://discuss.ardupilot.org/t/crash-after-two-motors-suddenly-stopped/132001) | Copter | crash | ✅ crash | motor | motor | 391 sn |
| [Help me analyze the logs of the Crash](https://discuss.ardupilot.org/t/help-me-analyze-the-logs-of-the-crash/132485) | Copter | crash | ✅ crash | control | control | 82 sn |
| [Correct tuning response to manual tuning charts](https://discuss.ardupilot.org/t/correct-tuning-response-to-manual-tuning-charts/133895) | Copter | crash | ✅ crash | control | - | 151 sn |
| [Crash Analysis Help - EKF Failures, Compass Inconsistent, GPS Dropouts](https://discuss.ardupilot.org/t/crash-analysis-help-ekf-failures-compass-inconsistent-gps-dropouts-arducopter-4-5-7/135472) | Copter | crash | ✅ crash | motor | motor | 180 sn |
| [Copter Fell out of the sky](https://discuss.ardupilot.org/t/copter-fell-out-of-the-sky/137243) | Copter | crash | ✅ crash | control | motor | 251 sn |
| [Crash analysis of hexacopter](https://discuss.ardupilot.org/t/crash-analysis-of-hexacopter/137474) | Copter | crash | ✅ crash | control | motor | 1164 sn |
| [Crashed because of Compass?](https://discuss.ardupilot.org/t/crashed-because-of-compass/137647) | Copter | crash | ✅ crash | motor | control | 414 sn |
| [Drone Crashed, please help me to analyze the log and find the cause of](https://discuss.ardupilot.org/t/drone-crashed-please-help-me-to-analyze-the-log-and-find-the-cause-of-the-crash/138534) | Copter | crash | ✅ crash | motor | motor | 95 sn |
| [2nd crash need help with logs/diagnosis](https://discuss.ardupilot.org/t/2nd-crash-need-help-with-logs-diagnosis/13868) | Copter | crash | ✅ crash | battery | battery | 1417 sn |
| [Crashed – It yawed badly and crashed due to compass anomalies in ArduC](https://discuss.ardupilot.org/t/crashed-it-yawed-badly-and-crashed-due-to-compass-anomalies-in-arducopter-4-6-0-with-micoair-nxt-px4-v2/138968) | Copter | crash | ✅ crash | motor | motor | 899 sn |
| [Tandem Wing Tilt-Hexaplane Crashed during Auto Transition (Rolled Righ](https://discuss.ardupilot.org/t/tandem-wing-tilt-hexaplane-crashed-during-auto-transition-rolled-right-log-attached/140136) | Plane | crash | ✅ crash | compass | - | 53 sn |
| [EKF Fail = Crashed into a tree, Need Help With Logs](https://discuss.ardupilot.org/t/ekf-fail-crashed-into-a-tree-need-help-with-logs/140808) | Copter | crash | ✅ crash | gps | gps | 134 sn |
| [Quadplane failed to complete transition and motors then turned off cau](https://discuss.ardupilot.org/t/quadplane-failed-to-complete-transition-and-motors-then-turned-off-causing-crash/140907) | Plane | crash | ✅ crash | control | motor | 76 sn |
| [Find the cause of robocraft crash](https://discuss.ardupilot.org/t/find-the-cause-of-robocraft-crash/140954) | Copter | crash | ✅ crash | motor | battery | 1205 sn |
| [Crash Analysis - Uncommanded dip in throttle](https://discuss.ardupilot.org/t/crash-analysis-uncommanded-dip-in-throttle/141437) | Copter | crash | ✅ crash | control | radio | 694 sn |
| [Crash after Autotune & "Prearm: ACRO_BAL_ROLL/PITCH" error](https://discuss.ardupilot.org/t/crash-after-autotune-prearm-acro-bal-roll-pitch-error/142188) | Copter | crash | ✅ crash | control | - | 63 sn |
| [Crash During Range Test at 2.6km – Need Help with Log Analysis](https://discuss.ardupilot.org/t/crash-during-range-test-at-2-6km-need-help-with-log-analysis/142364) | Copter | crash | ✅ crash | vibration | motor | 3675218770838 sn |
| [Review CubeOrange 21'' crash log](https://discuss.ardupilot.org/t/review-cubeorange-21-crash-log/142574) | Copter | crash | ✅ crash | control | control | 536 sn |
| [Drone has crashed, log file attached](https://discuss.ardupilot.org/t/drone-has-crashed-log-file-attached/143330) | Copter | crash | ✅ crash | control | control | 235 sn |
| [Cube 2.1,3.4.6,(I think), MP 1.3.48, New to Pixhawk2, Crash, Logs](https://discuss.ardupilot.org/t/cube-2-1-3-4-6-i-think-mp-1-3-48-new-to-pixhawk2-crash-logs/17161) | Copter | crash | ✅ crash | control | - | 314 sn |
| [Copter 3.2.1 on APM sudden drop in Altitude in Alt-Hold up to a crash](https://discuss.ardupilot.org/t/copter-3-2-1-on-apm-sudden-drop-in-altitude-in-alt-hold-up-to-a-crash/17266) | Copter | crash | ✅ crash | power | vibration | 205737 sn |
| [Mysterious behaviour (or not?) leading to crash](https://discuss.ardupilot.org/t/mysterious-behaviour-or-not-leading-to-crash/17679) | Copter | crash | ✅ crash | control | control | 297 sn |
| [Loss of height in AltHold // w/o AutoTune // touchdown of Quad // LOG ](https://discuss.ardupilot.org/t/loss-of-height-in-althold-w-o-autotune-touchdown-of-quad-log-attached/18074) | Copter | crash | ✅ crash | unknown | motor | 98 sn |
| [Pixhawk 1 Octo-Auto takeoff into violent pitch/roll/yaw oscillations a](https://discuss.ardupilot.org/t/pixhawk-1-octo-auto-takeoff-into-violent-pitch-roll-yaw-oscillations-and-bad-9k-crash/18298) | Copter | crash | ✅ crash | motor | compass | 54 sn |
| [Flip on autonomous takeoff](https://discuss.ardupilot.org/t/flip-on-autonomous-takeoff/18927) | Copter | crash | ✅ crash | motor | - | 257 sn |
| [1.4 m quad Copter crashed without any error in log](https://discuss.ardupilot.org/t/1-4-m-quad-copter-crashed-without-any-error-in-log/19550) | Copter | crash | ✅ crash | motor | vibration | 132 sn |
| [Quad Fell out of Sky](https://discuss.ardupilot.org/t/quad-fell-out-of-sky/21885) | Copter | crash | ✅ crash | power | vibration | 201932 sn |
| [Quad Flip at takeoff](https://discuss.ardupilot.org/t/quad-flip-at-takeoff/25187) | Copter | crash | ✅ crash | unknown | motor | 35 sn |
| [Crash multiple times](https://discuss.ardupilot.org/t/crash-multiple-times/25966) | Copter | crash | ✅ crash | vibration | vibration | 29 sn |
| [The helicopter failed at high altitude，crash！](https://discuss.ardupilot.org/t/the-helicopter-failed-at-high-altitude-crash/30377) | Copter | crash | ✅ crash | compass | control | 510 sn |
| [LOG analysis needed // failure in AutoMission // circle & crash at way](https://discuss.ardupilot.org/t/log-analysis-needed-failure-in-automission-circle-crash-at-waypoint/30458) | Plane | crash | ✅ crash | control | control | 3027 sn |
| [Crash when autotune](https://discuss.ardupilot.org/t/crash-when-autotune/30683) | Copter | crash | ✅ crash | motor | motor | 60 sn |
| [Pixhawk 2.1 CRASHED while Auto-Take off](https://discuss.ardupilot.org/t/pixhawk-2-1-crashed-while-auto-take-off/31376) | Copter | crash | ✅ crash | vibration | vibration | 25 sn |
| [Help with log analysis after maiden crash in Autotune](https://discuss.ardupilot.org/t/help-with-log-analysis-after-maiden-crash-in-autotune/34453) | Plane | crash | ✅ crash | control | control | 17 sn |
| [Drone crash Analysis](https://discuss.ardupilot.org/t/drone-crash-analysis/34498) | Copter | crash | ✅ crash | motor | motor | 299 sn |
| [Need help - Plane crashed on turning. No Idea why](https://discuss.ardupilot.org/t/need-help-plane-crashed-on-turning-no-idea-why/34898) | Plane | crash | ✅ crash | control | battery | 1331 sn |
| [Stopped logging for 2.5 seconds and crashed](https://discuss.ardupilot.org/t/stopped-logging-for-2-5-seconds-and-crashed/39265) | Copter | crash | ✅ crash | motor | power | 40 sn |
| [Crash - ALT_HOLD - Drone climbs, no throttle control](https://discuss.ardupilot.org/t/crash-alt-hold-drone-climbs-no-throttle-control/39705) | Copter | crash | ✅ crash | motor | ekf | 15 sn |
| [3.6.7 installed and tested- drone crashed- firmware issue or battery o](https://discuss.ardupilot.org/t/3-6-7-installed-and-tested-drone-crashed-firmware-issue-or-battery-or-something-else-unable-to-find-out/39722) | Copter | crash | ✅ crash | control | motor | 81 sn |
| [Log Review Request - QUAD](https://discuss.ardupilot.org/t/log-review-request-quad/40392) | Copter | crash | ✅ crash | unknown | radio | 429 sn |
| [Drone flipped. Motor balance-Fail, Test Compass-Fail, Test GPS-Fail](https://discuss.ardupilot.org/t/drone-flipped-motor-balance-fail-test-compass-fail-test-gps-fail/40515) | Copter | crash | ✅ crash | motor | - | 35 sn |
| [[solved] Strange Crash and Prearm IOMCU error on cube?](https://discuss.ardupilot.org/t/solved-strange-crash-and-prearm-iomcu-error-on-cube/41509) | Copter | crash | ✅ crash | control | - | 667 sn |
| [Crash on a X8 after starting AutoTune](https://discuss.ardupilot.org/t/crash-on-a-x8-after-starting-autotune/42085) | Copter | crash | ✅ crash | motor | motor | 642 sn |
| [Crashed in Autotune in Copter 3.6 seems like ESC problem?](https://discuss.ardupilot.org/t/crashed-in-autotune-in-copter-3-6-seems-like-esc-problem/42115) | Copter | crash | ✅ crash | motor | control | 836 sn |
| [Kakute F7 6 inch - Flip & Crash - Need help with logs](https://discuss.ardupilot.org/t/kakute-f7-6-inch-flip-crash-need-help-with-logs/42527) | Copter | crash | ✅ crash | motor | motor | 80 sn |
| [Quadplane suddenly pitched down at high angle and crash in FBW-A](https://discuss.ardupilot.org/t/quadplane-suddenly-pitched-down-at-high-angle-and-crash-in-fbw-a/43621) | Plane | crash | ✅ crash | control | control | 124 sn |
| [Arducopter 3.6.9 made sudden crash from 10 meters](https://discuss.ardupilot.org/t/arducopter-3-6-9-made-sudden-crash-from-10-meters/43660) | Copter | crash | ✅ crash | power | radio | 129 sn |
| [Crashed Log Analysis](https://discuss.ardupilot.org/t/crashed-log-analysis/44903) | Copter | crash | ✅ crash | motor | motor | 369 sn |
| [Help in analyzing the log file,arducopter v 3.6.9 -copter crash](https://discuss.ardupilot.org/t/help-in-analyzing-the-log-file-arducopter-v-3-6-9-copter-crash/44912) | Copter | crash | ✅ crash | vibration | vibration | 68 sn |
| [HELP with the log analysis for drone crash](https://discuss.ardupilot.org/t/help-with-the-log-analysis-for-drone-crash/44973) | Copter | crash | ✅ crash | motor | - | 14 sn |
| [Copter crashed! Could you please help me?](https://discuss.ardupilot.org/t/copter-crashed-could-you-please-help-me/46644) | Copter | crash | ✅ crash | control | motor | 40 sn |
| [[solved]Help in Autotune crash - what went wrong](https://discuss.ardupilot.org/t/solved-help-in-autotune-crash-what-went-wrong/47298) | Copter | crash | ✅ crash | control | motor | 96 sn |
| [Crashed! Crashed into a tower while do the mission! Deviate from sched](https://discuss.ardupilot.org/t/crashed-crashed-into-a-tower-while-do-the-mission-deviate-from-scheduled-course/48069) | Copter | crash | ✅ crash | motor | control | 735 sn |
| [Second flight... and second crash :(](https://discuss.ardupilot.org/t/second-flight-and-second-crash/48763) | Copter | crash | ✅ crash | power | battery | 602860 sn |
| [Copter crashed after successful autotune](https://discuss.ardupilot.org/t/copter-crashed-after-successful-autotune/54470) | Copter | crash | ✅ crash | control | control | 1304 sn |
| [AltHold crash, need help for log analyze](https://discuss.ardupilot.org/t/althold-crash-need-help-for-log-analyze/54829) | Copter | crash | ✅ crash | motor | motor | 31 sn |
| [Quad falls out of sky on yaw](https://discuss.ardupilot.org/t/quad-falls-out-of-sky-on-yaw/55193) | Copter | crash | ✅ crash | motor | - | 60 sn |
| [Crash Analysis - QuadCopter](https://discuss.ardupilot.org/t/crash-analysis-quadcopter/55749) | Copter | crash | ✅ crash | motor | motor | 251 sn |
| [CRASH: Hexacopter / PX4 - Please, help me find the cause](https://discuss.ardupilot.org/t/crash-hexacopter-px4-please-help-me-find-the-cause/56949) | Copter | crash | ✅ crash | motor | control | 255 sn |
| [Review my crash analysis](https://discuss.ardupilot.org/t/review-my-crash-analysis/56960) | Copter | crash | ✅ crash | motor | motor | 1857 sn |
| [Need help analyzing a crash](https://discuss.ardupilot.org/t/need-help-analyzing-a-crash/57097) | Copter | crash | ✅ crash | motor | compass | 2601 sn |
| [Confirmation that this crash was due to a failed motor](https://discuss.ardupilot.org/t/confirmation-that-this-crash-was-due-to-a-failed-motor/61014) | Copter | crash | ✅ crash | control | motor | 824 sn |
| [Effect of weight on tuning](https://discuss.ardupilot.org/t/effect-of-weight-on-tuning/65725) | Copter | crash | ✅ crash | control | - | 1184 sn |
| [Help in analysis of logs after crashing(autotuning)](https://discuss.ardupilot.org/t/help-in-analysis-of-logs-after-crashing-autotuning/66230) | Copter | crash | ✅ crash | motor | motor | 801 sn |
| [Flip over on Takeoff - Large Copter 30 Inch](https://discuss.ardupilot.org/t/flip-over-on-takeoff-large-copter-30-inch/67267) | Copter | crash | ✅ crash | motor | motor | 39 sn |
| [Need help with crash analysis](https://discuss.ardupilot.org/t/need-help-with-crash-analysis/68371) | Copter | crash | ✅ crash | compass | vibration | 811 sn |
| [Crash ArduCopter 4.0.7 (log attached)](https://discuss.ardupilot.org/t/crash-arducopter-4-0-7-log-attached/69409) | Copter | crash | ✅ crash | motor | radio | 33 sn |
| [Copter wants to flip on takeoff please help](https://discuss.ardupilot.org/t/copter-wants-to-flip-on-takeoff-please-help/70128) | Copter | crash | ✅ crash | control | control | 129 sn |
| [EKF failsafe leads to crash, please help with the log](https://discuss.ardupilot.org/t/ekf-failsafe-leads-to-crash-please-help-with-the-log/72303) | Copter | crash | ✅ crash | gps | ekf | 451 sn |
| [Need help to analyze log - sudden crash](https://discuss.ardupilot.org/t/need-help-to-analyze-log-sudden-crash/74509) | Copter | crash | ✅ crash | motor | motor | 98 sn |
| [Crashed drone due to unknown reasons!](https://discuss.ardupilot.org/t/crashed-drone-due-to-unknown-reasons/75213) | Copter | crash | ✅ crash | motor | control | 460 sn |
| [Help needed in determining cause of crash](https://discuss.ardupilot.org/t/help-needed-in-determining-cause-of-crash/75345) | Copter | crash | ✅ crash | motor | motor | 320 sn |
| [Octocopter multiple crash](https://discuss.ardupilot.org/t/octocopter-multiple-crash/76588) | Copter | crash | ✅ crash | motor | motor | 398 sn |
| [Copter flip on takeoff with fake static GPS](https://discuss.ardupilot.org/t/copter-flip-on-takeoff-with-fake-static-gps/78653) | Copter | crash | ✅ crash | motor | - | 45 sn |
| [Single copter crash log. Could someone analyze it for me?](https://discuss.ardupilot.org/t/single-copter-crash-log-could-someone-analyze-it-for-me/81825) | Copter | crash | ✅ crash | control | control | 34 sn |
| [4.0.7 Sudden crash](https://discuss.ardupilot.org/t/4-0-7-sudden-crash/82430) | Copter | crash | ✅ crash | motor | motor | 1099 sn |
| [[CRASH] Hexacopter suddenly crashed while auto](https://discuss.ardupilot.org/t/crash-hexacopter-suddenly-crashed-while-auto/83521) | Copter | crash | ✅ crash | motor | motor | 339 sn |
| [Sudden crash after takeoff](https://discuss.ardupilot.org/t/sudden-crash-after-takeoff/83626) | Copter | crash | ✅ crash | gps | motor | 558 sn |
| [Need help in finding the cause of a crash](https://discuss.ardupilot.org/t/need-help-in-finding-the-cause-of-a-crash/84217) | Copter | crash | ✅ crash | motor | control | 25 sn |
| [Hexa Crash During Loiter Test](https://discuss.ardupilot.org/t/hexa-crash-during-loiter-test/88767) | Copter | crash | ✅ crash | motor | battery | 96 sn |
| [Help needed to understand crash log please](https://discuss.ardupilot.org/t/help-needed-to-understand-crash-log-please/90207) | Copter | crash | ✅ crash | vibration | vibration | 138 sn |
| [RCin and RCout freezes (becomes flat line) during flight leading to cr](https://discuss.ardupilot.org/t/rcin-and-rcout-freezes-becomes-flat-line-during-flight-leading-to-crash/90287) | Copter | crash | ✅ crash | control | - | 1377 sn |
| [In-Flight Crash Investigation](https://discuss.ardupilot.org/t/in-flight-crash-investigation/94084) | Plane | crash | ✅ crash | control | control | 72 sn |
| [Crash Log File Assistance](https://discuss.ardupilot.org/t/crash-log-file-assistance/96429) | Copter | crash | ✅ crash | motor | motor | 117 sn |
| [Quadrotor crashed caused by rangefinder and motor readings based on da](https://discuss.ardupilot.org/t/quadrotor-crashed-caused-by-rangefinder-and-motor-readings-based-on-datalog-analysis-in-mission-planner/96442) | Copter | crash | ✅ crash | motor | motor | 85 sn |
| [Aggressive flight and Crash: Alt hold mode](https://discuss.ardupilot.org/t/aggressive-flight-and-crash-alt-hold-mode/98640) | Copter | crash | ✅ crash | control | control | 208 sn |
| [Vicious Crash Log 12S X Class](https://discuss.ardupilot.org/t/vicious-crash-log-12s-x-class/98768) | Copter | crash | ✅ crash | motor | motor | 70 sn |
| [12S Violent Crash with X-Class](https://discuss.ardupilot.org/t/12s-violent-crash-with-x-class/98794) | Copter | crash | ✅ crash | motor | motor | 70 sn |
| [Quadcopter Crash Log Analysis Request](https://discuss.ardupilot.org/t/quadcopter-crash-log-analysis-request/99897) | Copter | crash | ✅ crash | motor | motor | 20 sn |
| [VTOL Crash -Quadplane setup](https://discuss.ardupilot.org/t/vtol-crash-quadplane-setup/100406) | Plane | crash | ✅ incident | control | motor | 406 sn |
| [Log Analysis of Crash(Almost)](https://discuss.ardupilot.org/t/log-analysis-of-crash-almost/101181) | Copter | crash | ✅ incident | gps | vibration | 2681 sn |
| [MFE Fighter VTOL crash - suspected IO MCU failure](https://discuss.ardupilot.org/t/mfe-fighter-vtol-crash-suspected-io-mcu-failure/102276) | Plane | crash | ✅ incident | control | - | 460 sn |
| [And it was fly so nice...until it dropped out of the sky](https://discuss.ardupilot.org/t/and-it-was-fly-so-nice-until-it-dropped-out-of-the-sky/102361) | Copter | crash | ✅ incident | radio | motor | 266 sn |
| [Ardupilot Quad-plane unexpected crash](https://discuss.ardupilot.org/t/ardupilot-quad-plane-unexpected-crash/102402) | Plane | crash | ✅ incident | control | control | 23 sn |
| [Crash on takeoff, help with analysis? bin attached](https://discuss.ardupilot.org/t/crash-on-takeoff-help-with-analysis-bin-attached/102892) | Plane | crash | ✅ incident | control | stall | 114 sn |
| [Flight Crash Root Cause](https://discuss.ardupilot.org/t/flight-crash-root-cause/104199) | Copter | crash | ✅ incident | compass | ekf | 232 sn |
| [Thrust Loss Check Error During Autotune](https://discuss.ardupilot.org/t/thrust-loss-check-error-during-autotune/104200) | Copter | crash | ✅ incident | control | motor | 229 sn |
| [Crash due to Err:GPS and Err: EKFCHECK-0](https://discuss.ardupilot.org/t/crash-due-to-err-gps-and-err-ekfcheck-0/104689) | Copter | crash | ✅ incident | gps | motor | 142 sn |
| [Wild ride after successful Auto-tune](https://discuss.ardupilot.org/t/wild-ride-after-successful-auto-tune/113718) | Copter | crash | ✅ incident | control | control | 1008 sn |
| [Crash Pixhawk Arducopter 3.3.3 Help](https://discuss.ardupilot.org/t/crash-pixhawk-arducopter-3-3-3-help/11448) | Copter | crash | ✅ incident | power | vibration | 495898 sn |
| [Quadcopter flips over on takeoff. All usual suspects checked. SOLVED](https://discuss.ardupilot.org/t/quadcopter-flips-over-on-takeoff-all-usual-suspects-checked-solved/116156) | Copter | crash | ✅ incident | control | control | 3320 sn |
| [V-Tail Fixed Wing Crash](https://discuss.ardupilot.org/t/v-tail-fixed-wing-crash/121201) | Plane | crash | ✅ incident | control | control | 11817726897044 sn |
| [Please help analyse a crash log](https://discuss.ardupilot.org/t/please-help-analyse-a-crash-log/121455) | Plane | crash | ✅ incident | power | control | 694 sn |
| [QuadPlane Crashed After FBWA Transition - Unusual Current Drop](https://discuss.ardupilot.org/t/quadplane-crashed-after-fbwa-transition-unusual-current-drop/123223) | Plane | crash | ✅ incident | control | control | 484 sn |
| [AUTOTUNE crash and strange logs](https://discuss.ardupilot.org/t/autotune-crash-and-strange-logs/12677) | Plane | crash | ✅ incident | stall | - | 261 sn |
| [Diagnose Pixhawk crash log](https://discuss.ardupilot.org/t/diagnose-pixhawk-crash-log/12788) | Copter | crash | ✅ incident | power | - | 87 sn |
| [Drone crash suddenly after a stable flight](https://discuss.ardupilot.org/t/drone-crash-suddenly-after-a-stable-flight/129529) | Copter | crash | ✅ incident | motor | motor | 97 sn |
| [Yaw Instability and Crash in Loiter Mode – High Vibrations & Motor Imb](https://discuss.ardupilot.org/t/yaw-instability-and-crash-in-loiter-mode-high-vibrations-motor-imbalance-issues/130060) | Copter | crash | ✅ incident | motor | motor | 97 sn |
| [X Quad Tends to Flip During Takeoff in Stabilize Mode](https://discuss.ardupilot.org/t/x-quad-tends-to-flip-during-takeoff-in-stabilize-mode/131797) | Copter | crash | ✅ incident | unknown | - | 1071 sn |
| [Help on log analisys, Helicopter crashed](https://discuss.ardupilot.org/t/help-on-log-analisys-helicopter-crashed/133637) | Copter | crash | ✅ incident | compass | control | 27 sn |
| [Crash avoided, MAG0 GROUND MAG ANOMALY, YAW-REALIGNED](https://discuss.ardupilot.org/t/crash-avoided-mag0-ground-mag-anomaly-yaw-realigned/134335) | Copter | crash | ✅ incident | compass | compass | 15852952162864 sn |
| [Stabilize is OK but guided loses stability and flips over.](https://discuss.ardupilot.org/t/stabilize-is-ok-but-guided-loses-stability-and-flips-over/134793) | Copter | crash | ✅ incident | compass | control | 143 sn |
| [Arduplane 4.5.7 TAKEOFF crash investigation](https://discuss.ardupilot.org/t/arduplane-4-5-7-takeoff-crash-investigation/135053) | Plane | crash | ✅ incident | compass | - | 188 sn |
| [Copter 4.6.1 Custom Build - Crash Dump](https://discuss.ardupilot.org/t/copter-4-6-1-custom-build-crash-dump/135782) | Copter | crash | ✅ incident | control | motor | 66 sn |
| [Clarify need to rectify Drone Crash](https://discuss.ardupilot.org/t/clarify-need-to-rectify-drone-crash/137712) | Copter | crash | ✅ incident | vibration | control | 1336 sn |
| [Newbie trying Crash Analysis on Vtol Project](https://discuss.ardupilot.org/t/newbie-trying-crash-analysis-on-vtol-project/137901) | Plane | crash | ✅ incident | control | compass | 258 sn |
| [Crash after motor stopped](https://discuss.ardupilot.org/t/crash-after-motor-stopped/139836) | Copter | crash | ✅ incident | motor | motor | 460 sn |
| [After EKF failsafe, the drone just fell from 80 m](https://discuss.ardupilot.org/t/after-ekf-failsafe-the-drone-just-fell-from-80-m/141345) | Copter | crash | ✅ incident | power | gps | 342 sn |
| [The drone suddenly crashed](https://discuss.ardupilot.org/t/the-drone-suddenly-crashed/141765) | Copter | crash | ✅ incident | motor | motor | 198 sn |
| [Quadplane nearly crashed after the transition](https://discuss.ardupilot.org/t/quadplane-nearly-crashed-after-the-transition/142096) | Plane | crash | ✅ incident | vibration | control | 813 sn |
| [4+1 VTOL Crash analysis in Q mode (VTOL motors quit)](https://discuss.ardupilot.org/t/4-1-vtol-crash-analysis-in-q-mode-vtol-motors-quit/142142) | Plane | crash | ✅ incident | unknown | motor | 17798507202233 sn |
| [10inch Drone Crash / Drone falls on RTL](https://discuss.ardupilot.org/t/10inch-drone-crash-drone-falls-on-rtl/142346) | Copter | crash | ✅ incident | motor | motor | 59 sn |
| [Quadcopter (28-inch Props): Motor-3 Stops Mid-Air After ~38 min Hover ](https://discuss.ardupilot.org/t/quadcopter-28-inch-props-motor-3-stops-mid-air-after-38-min-hover-arducopter-4-6-2/142441) | Copter | crash | ✅ incident | motor | motor | 5116370651424 sn |
| [ArduPlane 4.6.3 TAKEOFF mode: climbs ~8 m then nose-down and crash (At](https://discuss.ardupilot.org/t/arduplane-4-6-3-takeoff-mode-climbs-8-m-then-nose-down-and-crash-atomrc-swordfish-v-tail/142491) | Plane | crash | ✅ incident | control | control | 63 sn |
| [Crash Log Analysis - Shutdown during hover](https://discuss.ardupilot.org/t/crash-log-analysis-shutdown-during-hover/142695) | Copter | crash | ✅ incident | control | - | 998 sn |
| [Log analysis Crashed!](https://discuss.ardupilot.org/t/log-analysis-crashed/142836) | Copter | crash | ✅ incident | power | power | 1618 sn |
| [APM quadcopter sudden crash](https://discuss.ardupilot.org/t/apm-quadcopter-sudden-crash/143010) | Copter | crash | ✅ incident | unknown | - | 44752 sn |
| [Crash Analysis Request: Hexa-X / Cube Orange+ / 28" Props / ArduCopter](https://discuss.ardupilot.org/t/crash-analysis-request-hexa-x-cube-orange-28-props-arducopter-4-6-2/143577) | Copter | crash | ✅ incident | motor | motor | 830 sn |
| [Fixedwing VTOL UAV Crash Review](https://discuss.ardupilot.org/t/fixedwing-vtol-uav-crash-review/143642) | Plane | crash | ✅ incident | control | control | 1489 sn |
| [Watchdog after a flight with temporary loss of control. No crash, soft](https://discuss.ardupilot.org/t/watchdog-after-a-flight-with-temporary-loss-of-control-no-crash-soft-landing/145555) | Copter | crash | ✅ incident | control | - | 216 sn |
| [Identifying reason for crash](https://discuss.ardupilot.org/t/identifying-reason-for-crash/145881) | Copter | crash | ✅ incident | power | radio | 378 sn |
| [Crash logs, RTL spiral into ground](https://discuss.ardupilot.org/t/crash-logs-rtl-spiral-into-ground/15863) | Plane | crash | ✅ incident | power | - | 489 sn |
| [Help w/ log analysis - copter flip/crash](https://discuss.ardupilot.org/t/help-w-log-analysis-copter-flip-crash/15940) | Copter | crash | ✅ incident | power | motor | 360 sn |
| [Quad constantly flips during takeoff, motors not spinning the same spe](https://discuss.ardupilot.org/t/quad-constantly-flips-during-takeoff-motors-not-spinning-the-same-speed/16617) | Copter | crash | ✅ incident | power | motor | 138 sn |
| [Testing RF Immunity - Crash Log - What fails?](https://discuss.ardupilot.org/t/testing-rf-immunity-crash-log-what-fails/18540) | Copter | crash | ✅ incident | power | motor | 273810 sn |
| [Crash after Autotune, Pixhawk](https://discuss.ardupilot.org/t/crash-after-autotune-pixhawk/21863) | Copter | crash | ✅ incident | power | vibration | 654 sn |
| [CRASH: Log Review Request](https://discuss.ardupilot.org/t/crash-log-review-request/23148) | Copter | crash | ✅ incident | power | power | 2023 sn |
| [Hexacopter crash](https://discuss.ardupilot.org/t/hexacopter-crash/23543) | Copter | crash | ✅ incident | power | radio | 431 sn |
| [Hexacopter drifting away = crash (log + video)](https://discuss.ardupilot.org/t/hexacopter-drifting-away-crash-log-video/26675) | Copter | crash | ✅ incident | motor | compass | 139 sn |
| [Inconsistent compass error leads to crash when internal compasses swit](https://discuss.ardupilot.org/t/inconsistent-compass-error-leads-to-crash-when-internal-compasses-switched-off/32040) | Copter | crash | ✅ incident | motor | compass | 32 sn |
| [Rtl crash after converting to ppm and new power module](https://discuss.ardupilot.org/t/rtl-crash-after-converting-to-ppm-and-new-power-module/33361) | Copter | crash | ✅ incident | unknown | - | 59038 sn |
| [Log Crash Analysis Help](https://discuss.ardupilot.org/t/log-crash-analysis-help/37003) | Copter | crash | ✅ incident | power | motor | 424325 sn |
| [AC-copter 3.7-dev fell from the sky crash log](https://discuss.ardupilot.org/t/ac-copter-3-7-dev-fell-from-the-sky-crash-log/37800) | Copter | crash | ✅ incident | gps | power | 175 sn |
| [Help diagnosing errant behavior / crash for octocopter](https://discuss.ardupilot.org/t/help-diagnosing-errant-behavior-crash-for-octocopter/39580) | Copter | crash | ✅ incident | compass | battery | 41 sn |
| [Advice on log with crash on takeoff](https://discuss.ardupilot.org/t/advice-on-log-with-crash-on-takeoff/42843) | Plane | crash | ✅ incident | power | control | 1146 sn |
| [Fell/landed to a tree caused by unknown reason](https://discuss.ardupilot.org/t/fell-landed-to-a-tree-caused-by-unknown-reason/43318) | Copter | crash | ✅ incident | power | - | 367690 sn |
| [Pixhawk Crash magically](https://discuss.ardupilot.org/t/pixhawk-crash-magically/50401) | Copter | crash | ✅ incident | motor | battery | 26 sn |
| [Compass variance errors and crash with Skywalker X8 Quadplane](https://discuss.ardupilot.org/t/compass-variance-errors-and-crash-with-skywalker-x8-quadplane/52335) | Plane | crash | ✅ incident | stall | compass | 225 sn |
| [Helicopter lost control in stabilize mode and crashed.Log attached](https://discuss.ardupilot.org/t/helicopter-lost-control-in-stabilize-mode-and-crashed-log-attached/54194) | Copter | crash | ✅ incident | power | ekf | 690 sn |
| [Crash Log analysis and problem diagnosis (potential bug?)](https://discuss.ardupilot.org/t/crash-log-analysis-and-problem-diagnosis-potential-bug/5457) | Copter | crash | ✅ incident | power | - | 301851 sn |
| [Copter suddenly went out of control and crashed severely](https://discuss.ardupilot.org/t/copter-suddenly-went-out-of-control-and-crashed-severely/56145) | Copter | crash | ✅ incident | gps | ekf | 329 sn |
| [Crash first flight: ardupilot 4.0 help!](https://discuss.ardupilot.org/t/crash-first-flight-ardupilot-4-0-help/57299) | Copter | crash | ✅ incident | control | battery | 199 sn |
| [Sudden Fall Down and Crash (Attaching LOGS)](https://discuss.ardupilot.org/t/sudden-fall-down-and-crash-attaching-logs/57400) | Copter | crash | ✅ incident | power | power | 111 sn |
| [Fatal crash on a tried and tested rig. 4.0.5 / omnibus f4pro / r9mm](https://discuss.ardupilot.org/t/fatal-crash-on-a-tried-and-tested-rig-4-0-5-omnibus-f4pro-r9mm/59240) | Plane | crash | ✅ incident | control | stall | 172 sn |
| [Free-fall then crash when flying in Guided Mode (logs attached)](https://discuss.ardupilot.org/t/free-fall-then-crash-when-flying-in-guided-mode-logs-attached/59255) | Copter | crash | ✅ incident | control | radio | 114 sn |
| [Copter fell out of the sky for no reason that I can find - twice!](https://discuss.ardupilot.org/t/copter-fell-out-of-the-sky-for-no-reason-that-i-can-find-twice/63350) | Copter | crash | ✅ incident | power | power | 15 sn |
| [Crash on Auto Mode (Fixed Wing Plane)](https://discuss.ardupilot.org/t/crash-on-auto-mode-fixed-wing-plane/67111) | Plane | crash | ✅ incident | control | stall | 975 sn |
| [Plane crash during Auto TakeOff](https://discuss.ardupilot.org/t/plane-crash-during-auto-takeoff/68125) | Plane | crash | ✅ incident | control | control | 69 sn |
| [VTOL crash analysis!](https://discuss.ardupilot.org/t/vtol-crash-analysis/69983) | Plane | crash | ✅ incident | battery | control | 147 sn |
| [Log analysis please, It suddenly overturned 180 degrees and crashed](https://discuss.ardupilot.org/t/log-analysis-please-it-suddenly-overturned-180-degrees-and-crashed/72851) | Copter | crash | ✅ incident | power | power | 104 sn |
| [Drone crashed - sudden rise in YAW during flying and crash landed](https://discuss.ardupilot.org/t/drone-crashed-sudden-rise-in-yaw-during-flying-and-crash-landed/76391) | Copter | crash | ✅ incident | motor | motor | 657 sn |
| [X Quad 3.2.1 mid flight crash](https://discuss.ardupilot.org/t/x-quad-3-2-1-mid-flight-crash/8079) | Copter | crash | ✅ incident | power | power | 230928 sn |
| [Crash with 4.2.0-beta and 4.3.0-daily (bdshot)](https://discuss.ardupilot.org/t/crash-with-4-2-0-beta-and-4-3-0-daily-bdshot/83297) | Copter | crash | ✅ incident | power | power | 124 sn |
| [New Pilot: Can someone please help me understand my crash?](https://discuss.ardupilot.org/t/new-pilot-can-someone-please-help-me-understand-my-crash/85880) | Plane | crash | ✅ incident | power | ekf | 104 sn |
| [Drone crash on RTL on descend, drone started to tumble (Hobbywing X6 O](https://discuss.ardupilot.org/t/drone-crash-on-rtl-on-descend-drone-started-to-tumble-hobbywing-x6-octo-please-help-to-analyze-log/86761) | Copter | crash | ✅ incident | gps | motor | 390 sn |
| [Need help looking over a log, had an unexpected crash?](https://discuss.ardupilot.org/t/need-help-looking-over-a-log-had-an-unexpected-crash/87171) | Plane | crash | ✅ incident | control | - | 1041 sn |
| [FBWI Mode Takeoff Crashed due to Full Pitch [LOG UPLOADED]](https://discuss.ardupilot.org/t/fbwi-mode-takeoff-crashed-due-to-full-pitch-log-uploaded/88204) | Plane | crash | ✅ incident | stall | control | 64 sn |
| ["EKF Lane Switch 1" and then drone crashes](https://discuss.ardupilot.org/t/ekf-lane-switch-1-and-then-drone-crashes/92394) | Copter | crash | ✅ incident | motor | vibration | 451 sn |
| [Copter crashed with, EKF primary changed:0 EKF primary changed:2 - dea](https://discuss.ardupilot.org/t/copter-crashed-with-ekf-primary-changed-0-ekf-primary-changed-2-deadly-crash/92858) | Copter | crash | ✅ incident | power | vibration | 1034 sn |
| [VTOL plane crash during hover tuning](https://discuss.ardupilot.org/t/vtol-plane-crash-during-hover-tuning/97877) | Plane | crash | ✅ incident | control | motor | 65 sn |
| [Tailless VTOL crash log](https://discuss.ardupilot.org/t/tailless-vtol-crash-log/99978) | Plane | crash | ✅ incident | stall | control | 17 sn |
| [Agro drone trying to flip during takeoff](https://discuss.ardupilot.org/t/agro-drone-trying-to-flip-during-takeoff/105190) | Copter | crash | ❌ noflight | - | - | 1811 sn |
| [Copter crash today / can't run LogAnalyser due to "runner.exe stopped"](https://discuss.ardupilot.org/t/copter-crash-today-cant-run-loganalyser-due-to-runner-exe-stopped-help-to-understand-issue-appreciate/10843) | Copter | crash | ❌ noflight | - | - | 36 sn |
| [QuadCpter/ Crash today / climb up (loiter) till battery run out](https://discuss.ardupilot.org/t/quadcpter-crash-today-climb-up-loiter-till-battery-run-out/10846) | Copter | crash | ❌ noflight | - | - | 36 sn |
| [Large 10KG payload Drone crash on take off! Please help](https://discuss.ardupilot.org/t/large-10kg-payload-drone-crash-on-take-off-please-help/11083) | Copter | crash | ❌ noflight | - | - | 28 sn |
| [PixHawk crashed while ground testing](https://discuss.ardupilot.org/t/pixhawk-crashed-while-ground-testing/11638) | Copter | crash | ❌ noflight | - | - | 155 sn |
| [Drone sudden crash log](https://discuss.ardupilot.org/t/drone-sudden-crash-log/133605) | Copter | crash | ❌ noflight | - | motor | 29 sn |
| [Drone Crash and Instability Issues After Rebuild – Need Help Debugging](https://discuss.ardupilot.org/t/drone-crash-and-instability-issues-after-rebuild-need-help-debugging/139585) | Copter | crash | ❌ noflight | - | control | 167 sn |
| [Copter 4.6.2 Crashed after Takeoff](https://discuss.ardupilot.org/t/copter-4-6-2-crashed-after-takeoff/141037) | Copter | crash | ❌ noflight | - | control | 64 sn |
| [Drone Crashed After Switching to LOITER Mode (Stable in AUTO Mode)](https://discuss.ardupilot.org/t/drone-crashed-after-switching-to-loiter-mode-stable-in-auto-mode/141421) | Copter | crash | ❌ noflight | - | gps | 161 sn |
| [The drone suddenly went out of‑control and crashed!](https://discuss.ardupilot.org/t/the-drone-suddenly-went-out-of-control-and-crashed/144522) | Copter | crash | ❌ noflight | - | motor | 46 sn |
| [Hexa copter crash](https://discuss.ardupilot.org/t/hexa-copter-crash/20162) | Copter | crash | ❌ noflight | - | battery | 109 sn |
| [Copter Falls From Sky after Mission Start Action Excuted](https://discuss.ardupilot.org/t/copter-falls-from-sky-after-mission-start-action-excuted/20552) | Copter | crash | ❌ noflight | - | - | 13 sn |
| [Pixhawk 4 - Copter about to flip forward - RC problem?](https://discuss.ardupilot.org/t/pixhawk-4-copter-about-to-flip-forward-rc-problem/31538) | Copter | crash | ❌ noflight | - | motor | 122 sn |
| [Drone Drops After Hovering Fine for a Few Seconds (Log Analysis Help)](https://discuss.ardupilot.org/t/drone-drops-after-hovering-fine-for-a-few-seconds-log-analysis-help/39146) | Copter | crash | ❌ noflight | - | - | 28 sn |
| [Large X8 disarm/power/logging loss in flight causing crash - Onboard l](https://discuss.ardupilot.org/t/large-x8-disarm-power-logging-loss-in-flight-causing-crash-onboard-log/97192) | Copter | crash | ❌ noflight | - | power | 96 sn |
| [Discrepancy in the Matek F765 log file after a crash](https://discuss.ardupilot.org/t/discrepancy-in-the-matek-f765-log-file-after-a-crash/97318) | Plane | crash | ❌ noflight | - | - | 56 sn |
| [Crash analysis, probable power loss](https://discuss.ardupilot.org/t/crash-analysis-probable-power-loss/118356) | Copter | crash | ❌ normal | - | power | 12033899678709 sn |
| [Crash logs analysis](https://discuss.ardupilot.org/t/crash-logs-analysis/12892) | Copter | crash | ❌ normal | - | - | 173 sn |
| [VTOL crash during RTL - ? power loss](https://discuss.ardupilot.org/t/vtol-crash-during-rtl-power-loss/137162) | Plane | crash | ❌ normal | - | power | 206 sn |
| [VTOL tiltrotor crash in QLOITER – sudden yaw spin, backward movement, ](https://discuss.ardupilot.org/t/vtol-tiltrotor-crash-in-qloiter-sudden-yaw-spin-backward-movement-and-nose-down-rotation/145787) | Plane | crash | ❌ normal | - | - | 946 sn |
| [Hexacopter/Pixhawk2.1 - Crash](https://discuss.ardupilot.org/t/hexacopter-pixhawk2-1-crash/16756) | Copter | crash | ❌ normal | - | motor | 201 sn |
| [Roll/pitch parts from desired roll/pitch, causing crash](https://discuss.ardupilot.org/t/roll-pitch-parts-from-desired-roll-pitch-causing-crash/35095) | Plane | crash | ❌ normal | - | - | 4928 sn |
| [Loss of altitude and crash when engaging LOITER](https://discuss.ardupilot.org/t/loss-of-altitude-and-crash-when-engaging-loiter/44042) | Copter | crash | ❌ normal | - | - | 58 sn |
| [VTOL Unstable & crashed in Qstablized mode](https://discuss.ardupilot.org/t/vtol-unstable-crashed-in-qstablized-mode/82934) | Plane | crash | ❌ normal | - | control | 285 sn |
| [Arducopter Crash, motor suddenly stop when tuning PID](https://discuss.ardupilot.org/t/arducopter-crash-motor-suddenly-stop-when-tuning-pid/91325) | Copter | crash | ❌ normal | - | motor | 670 sn |
| [3DR Iris + Crashed after 3 successful waypoints mission](https://discuss.ardupilot.org/t/3dr-iris-crashed-after-3-successful-waypoints-mission/9269) | Copter | crash | ❌ normal | - | motor | 329868 sn |
| [Help with Log Analysis, Copter "stumbling"](https://discuss.ardupilot.org/t/help-with-log-analysis-copter-stumbling/82334) | Copter | normal | ❌ crash | motor | - | 250 sn |
| [New build, safe for autotune or need filter setup first?](https://discuss.ardupilot.org/t/new-build-safe-for-autotune-or-need-filter-setup-first/100104) | Copter | normal | ❌ incident | compass | - | 274 sn |
| [Tuning issues with plane, successful auto t/o and land maiden - now no](https://discuss.ardupilot.org/t/tuning-issues-with-plane-successful-auto-t-o-and-land-maiden-now-not-so-much/100608) | Plane | normal | ❌ incident | compass | - | 639 sn |
| [Updating from 4.0.7 to 4.3.3 requires new PID tuning?](https://discuss.ardupilot.org/t/updating-from-4-0-7-to-4-3-3-requires-new-pid-tuning/101399) | Copter | normal | ❌ incident | unknown | - | 487 sn |
| [RC Input issues, log review, and questions](https://discuss.ardupilot.org/t/rc-input-issues-log-review-and-questions/101553) | Plane | normal | ❌ incident | power | - | 567 sn |
| [Weird hovering issue - requires 3A to hover then jumps to 6A after a f](https://discuss.ardupilot.org/t/weird-hovering-issue-requires-3a-to-hover-then-jumps-to-6a-after-a-few-and-back-to-3a-and-so-on/110871) | Copter | normal | ❌ incident | compass | - | 1271 sn |
| [Performance review of Quadcopter](https://discuss.ardupilot.org/t/performance-review-of-quadcopter/112001) | Copter | normal | ❌ incident | unknown | - | 575 sn |
| [“AutoTune: failing to level, please tune manually”](https://discuss.ardupilot.org/t/autotune-failing-to-level-please-tune-manually/117575) | Copter | normal | ❌ incident | unknown | - | 729 sn |
| [Autotune makes plane far less responsive](https://discuss.ardupilot.org/t/autotune-makes-plane-far-less-responsive/122215) | Plane | normal | ❌ incident | control | - | 116 sn |
| [Review log for Yaw 1Hz oscillation](https://discuss.ardupilot.org/t/review-log-for-yaw-1hz-oscillation/122473) | Plane | normal | ❌ incident | unknown | - | 92 sn |
| [Racer pitch tuning on fast speeds](https://discuss.ardupilot.org/t/racer-pitch-tuning-on-fast-speeds/123961) | Copter | normal | ❌ incident | unknown | - | 103 sn |
| [Auto tune on yaw not so great?](https://discuss.ardupilot.org/t/auto-tune-on-yaw-not-so-great/124552) | Copter | normal | ❌ incident | unknown | - | 286 sn |
| [Autotune too low ATC_ACCEL_R_MAX value](https://discuss.ardupilot.org/t/autotune-too-low-atc-accel-r-max-value/126196) | Copter | normal | ❌ incident | battery | - | 449 sn |
| [About Pid tuning of 30inch prop quadrotor](https://discuss.ardupilot.org/t/about-pid-tuning-of-30inch-prop-quadrotor/131480) | Copter | normal | ❌ incident | unknown | - | 7133983284583 sn |
| [PITCH oscillations in horizontal flight. Inability to adjust PID in AU](https://discuss.ardupilot.org/t/pitch-oscillations-in-horizontal-flight-inability-to-adjust-pid-in-autotune-mode/132168) | Plane | normal | ❌ incident | control | - | 2545 sn |
| [Tricopter VTOL Tilts Forward During Hover Test — Suspected Inverted Pi](https://discuss.ardupilot.org/t/tricopter-vtol-tilts-forward-during-hover-test-suspected-inverted-pitch/133808) | Plane | normal | ❌ incident | control | - | 13979454718313 sn |
| [Unstable Flight and Sudden Drift After Autotune on 7" Quad – ArduCopte](https://discuss.ardupilot.org/t/unstable-flight-and-sudden-drift-after-autotune-on-7-quad-arducopter-4-5-7/134177) | Copter | normal | ❌ incident | unknown | - | 1059 sn |
| [Autotune doesnt complete, logs cut off](https://discuss.ardupilot.org/t/autotune-doesnt-complete-logs-cut-off/137946) | Copter | normal | ❌ incident | power | - | 170 sn |
| [About PID Tuning, QuickTune, and QAUTOTUNE for Large (13–19 kg) VTOL A](https://discuss.ardupilot.org/t/about-pid-tuning-quicktune-and-qautotune-for-large-13-19-kg-vtol-aircraft/138733) | Plane | normal | ❌ incident | control | - | 354 sn |
| [Hover Learn Results and INS Raw Log Review](https://discuss.ardupilot.org/t/hover-learn-results-and-ins-raw-log-review/141829) | Copter | normal | ❌ incident | unknown | - | 185 sn |
| [Oscillation after autotune of 6inch quadrotor](https://discuss.ardupilot.org/t/oscillation-after-autotune-of-6inch-quadrotor/143931) | Copter | normal | ❌ incident | unknown | - | 736 sn |
| [10inch copter tuning. Throttle notch](https://discuss.ardupilot.org/t/10inch-copter-tuning-throttle-notch/144690) | Copter | normal | ❌ incident | compass | - | 72 sn |
| [Plane enters spiral/toilet-bowl loop during roll in AutoTune (Factory ](https://discuss.ardupilot.org/t/plane-enters-spiral-toilet-bowl-loop-during-roll-in-autotune-factory-pids/144973) | Plane | normal | ❌ incident | control | - | 600 sn |
| [First Flight & some issues with X8. Need help analysing logs!](https://discuss.ardupilot.org/t/first-flight-some-issues-with-x8-need-help-analysing-logs/17024) | Copter | normal | ❌ incident | power | - | 642 sn |
| [Autotune RC5 - concerning observations](https://discuss.ardupilot.org/t/autotune-rc5-concerning-observations/17560) | Copter | normal | ❌ incident | battery | - | 1606 sn |
| [NEED HELP: Couldn't get better tuning](https://discuss.ardupilot.org/t/need-help-couldnt-get-better-tuning/27349) | Copter | normal | ❌ incident | unknown | - | 93 sn |
| [How to improve AutoTune results on big quad coaxial X8 [RESOLVED]](https://discuss.ardupilot.org/t/how-to-improve-autotune-results-on-big-quad-coaxial-x8-resolved/54450) | Copter | normal | ❌ incident | unknown | - | 296 sn |
| [Pitch Wobble - Autotune Didn't Fix](https://discuss.ardupilot.org/t/pitch-wobble-autotune-didnt-fix/69731) | Plane | normal | ❌ incident | control | - | 555 sn |
| [4.1 beta autotune failsafe](https://discuss.ardupilot.org/t/4-1-beta-autotune-failsafe/70698) | Copter | normal | ❌ incident | radio | - | 235 sn |
| [Oscilations when switching to mission from hover](https://discuss.ardupilot.org/t/oscilations-when-switching-to-mission-from-hover/72523) | Copter | normal | ❌ incident | compass | - | 924 sn |
| [Hovering current](https://discuss.ardupilot.org/t/hovering-current/72796) | Copter | normal | ❌ incident | battery | - | 374 sn |
| [Autotune plane: need help > desired Roll and achieved Roll](https://discuss.ardupilot.org/t/autotune-plane-need-help-desired-roll-and-achieved-roll/73304) | Plane | normal | ❌ incident | control | - | 1099392 sn |
| [AUTOTUNE resulted in twitchy control surfaces](https://discuss.ardupilot.org/t/autotune-resulted-in-twitchy-control-surfaces/73403) | Plane | normal | ❌ incident | stall | - | 1789 sn |
| [Trex600 with Pixhawk4 mini and Arducopter 4.1.2 Tuning help](https://discuss.ardupilot.org/t/trex600-with-pixhawk4-mini-and-arducopter-4-1-2-tuning-help/79396) | Copter | normal | ❌ incident | unknown | - | 1296 sn |
| [AutoTune Copter 4.1.2 on 3" Quad [Squirtv2.1] : Roll tuning failed wit](https://discuss.ardupilot.org/t/autotune-copter-4-1-2-on-3-quad-squirtv2-1-roll-tuning-failed-with-autotune-reached-limit/79901) | Copter | normal | ❌ incident | battery | - | 499 sn |
| [Wobbling in hover flight, strong oscillations in servo output](https://discuss.ardupilot.org/t/wobbling-in-hover-flight-strong-oscillations-in-servo-output/89816) | Copter | normal | ❌ incident | radio | - | 68 sn |
| [Autotune won't engage](https://discuss.ardupilot.org/t/autotune-wont-engage/101722) | Copter | normal | ✅ noflight | - | - | 310 sn |
| [Seeking Feedback on Tuning 7-Inch Copter for Improved Stability](https://discuss.ardupilot.org/t/seeking-feedback-on-tuning-7-inch-copter-for-improved-stability/103076) | Copter | normal | ✅ noflight | - | - | 215 sn |
| [FFT based harmonic notch filter for dynamic tuning](https://discuss.ardupilot.org/t/fft-based-harmonic-notch-filter-for-dynamic-tuning/104391) | Copter | normal | ✅ noflight | - | - | 118 sn |
| [Jitter in auto modes, help with log review](https://discuss.ardupilot.org/t/jitter-in-auto-modes-help-with-log-review/108349) | Copter | normal | ✅ noflight | - | - | 27 sn |
| [Recommended logging settings for HNTCH and ACRO PID tuning](https://discuss.ardupilot.org/t/recommended-logging-settings-for-hntch-and-acro-pid-tuning/118420) | Copter | normal | ✅ noflight | - | - | 76 sn |
| [Tuning Pitch/Roll offsets. How to read the Log file data](https://discuss.ardupilot.org/t/tuning-pitch-roll-offsets-how-to-read-the-log-file-data/120372) | Copter | normal | ✅ noflight | - | - | 450 sn |
| [Hot motors, even in gentle hover](https://discuss.ardupilot.org/t/hot-motors-even-in-gentle-hover/122147) | Copter | normal | ✅ noflight | - | - | 207 sn |
| [VTOL Quick Tune First Test Shoulder Button Not Triggering](https://discuss.ardupilot.org/t/vtol-quick-tune-first-test-shoulder-button-not-triggering/129502) | Copter | normal | ✅ noflight | - | - | 71 sn |
| [Notch filter review cross check](https://discuss.ardupilot.org/t/notch-filter-review-cross-check/130954) | Copter | normal | ✅ noflight | - | - | 200 sn |
| [5 inch quad initial tuning](https://discuss.ardupilot.org/t/5-inch-quad-initial-tuning/134726) | Copter | normal | ✅ noflight | - | - | 71 sn |
| [PID review tool - understanding PID Spectrogram and Frequency Domain](https://discuss.ardupilot.org/t/pid-review-tool-understanding-pid-spectrogram-and-frequency-domain/134805) | Copter | normal | ✅ noflight | - | - | 134 sn |
| [My logs (and only my logs) wont open in the PID Review Tool](https://discuss.ardupilot.org/t/my-logs-and-only-my-logs-wont-open-in-the-pid-review-tool/137978) | Copter | normal | ✅ noflight | - | - | 46 sn |
| [Tuning 4" Micro Long Range](https://discuss.ardupilot.org/t/tuning-4-micro-long-range/139094) | Copter | normal | ✅ noflight | - | - | 93 sn |
| [High-frequency vibration during hovering and trembles when descending](https://discuss.ardupilot.org/t/high-frequency-vibration-during-hovering-and-trembles-when-descending/141624) | Copter | normal | ✅ noflight | - | - | 62 sn |
| [Verifying stability & understanding MagFit / AutoTune](https://discuss.ardupilot.org/t/verifying-stability-understanding-magfit-autotune/141817) | Copter | normal | ✅ noflight | - | - | 292 sn |
| [Large Quad tune](https://discuss.ardupilot.org/t/large-quad-tune/143560) | Copter | normal | ✅ noflight | - | - | 143 sn |
| [SpeedyBee Bee35 Copter Tuning](https://discuss.ardupilot.org/t/speedybee-bee35-copter-tuning/145362) | Copter | normal | ✅ noflight | - | - | 111 sn |
| [Indoor position controller tuning](https://discuss.ardupilot.org/t/indoor-position-controller-tuning/32542) | Copter | normal | ✅ noflight | - | - | 214 sn |
| [Compass Inconsistent after the first flight](https://discuss.ardupilot.org/t/compass-inconsistent-after-the-first-flight/55911) | Copter | normal | ✅ noflight | - | - | 249 sn |
| [Hover instability (Althold)](https://discuss.ardupilot.org/t/hover-instability-althold/56452) | Copter | normal | ✅ noflight | - | - | 605 sn |
| [Pid tune help pocketoilot](https://discuss.ardupilot.org/t/pid-tune-help-pocketoilot/61372) | Copter | normal | ✅ noflight | - | - | 49 sn |
| [Maiden Tarot 650 rolls right (tips over) before take off when I increa](https://discuss.ardupilot.org/t/maiden-tarot-650-rolls-right-tips-over-before-take-off-when-i-increased-throttle-log/64684) | Copter | normal | ✅ noflight | - | - | 47 sn |
| [Log review for big hex](https://discuss.ardupilot.org/t/log-review-for-big-hex/78394) | Copter | normal | ✅ noflight | - | - | 87 sn |
| [Maiden TRex 550 flight, massive side-to-side shaking](https://discuss.ardupilot.org/t/maiden-trex-550-flight-massive-side-to-side-shaking/93323) | Copter | normal | ✅ noflight | - | - | 113 sn |
| [No throttle output in FBWA or Autotune mode](https://discuss.ardupilot.org/t/no-throttle-output-in-fbwa-or-autotune-mode/97236) | Plane | normal | ✅ noflight | - | - | 15 sn |
| [Filtering Vibration to Get a Better Tune](https://discuss.ardupilot.org/t/filtering-vibration-to-get-a-better-tune/98578) | Copter | normal | ✅ noflight | - | - | 266 sn |
| [First Maiden Log File](https://discuss.ardupilot.org/t/first-maiden-log-file/99997) | Copter | normal | ✅ noflight | - | - | 175 sn |
| [New tuning needed when change from Lipo to Li-ion](https://discuss.ardupilot.org/t/new-tuning-needed-when-change-from-lipo-to-li-ion/101887) | Copter | normal | ✅ normal | - | - | 879 sn |
| [MOT_THST_EXPO and autotune](https://discuss.ardupilot.org/t/mot-thst-expo-and-autotune/105480) | Copter | normal | ✅ normal | - | - | 262 sn |
| [Some assistance needed for a New tune on a small hexa drone](https://discuss.ardupilot.org/t/some-assistance-needed-for-a-new-tune-on-a-small-hexa-drone/106850) | Copter | normal | ✅ normal | - | - | 116 sn |
| [Need Help tuning large frame hex.](https://discuss.ardupilot.org/t/need-help-tuning-large-frame-hex/107280) | Copter | normal | ✅ normal | - | - | 104 sn |
| [Log Review: AUTO mission stopped in flight](https://discuss.ardupilot.org/t/log-review-auto-mission-stopped-in-flight/110997) | Copter | normal | ✅ normal | - | - | 507 sn |
| [Notch filter review+ tune analysis](https://discuss.ardupilot.org/t/notch-filter-review-tune-analysis/115513) | Plane | normal | ✅ normal | - | - | 134 sn |
| [Log review: autotune, cuav yaw with gps and optical flow](https://discuss.ardupilot.org/t/log-review-autotune-cuav-yaw-with-gps-and-optical-flow/115971) | Copter | normal | ✅ normal | - | - | 707 sn |
| [Help Needed with Tuning Issues on 5L Payload Drone in PosHold Mode](https://discuss.ardupilot.org/t/help-needed-with-tuning-issues-on-5l-payload-drone-in-poshold-mode/119994) | Copter | normal | ✅ normal | - | - | 379 sn |
| [Autotune gives poor tuning values on roll axis and causing vibration o](https://discuss.ardupilot.org/t/autotune-gives-poor-tuning-values-on-roll-axis-and-causing-vibration-on-arms/120018) | Copter | normal | ✅ normal | - | - | 256 sn |
| [VTOL Altitude Fluctuations Between Waypoints in AUTO Mode – PID Tuning](https://discuss.ardupilot.org/t/vtol-altitude-fluctuations-between-waypoints-in-auto-mode-pid-tuning-issue/124305) | Plane | normal | ✅ normal | - | - | 843 sn |
| [Quadcopter aggressive gains after autotune](https://discuss.ardupilot.org/t/quadcopter-aggressive-gains-after-autotune/126920) | Copter | normal | ✅ normal | - | - | 87 sn |
| [Notch Filter & Pids Results Recommendation/Review](https://discuss.ardupilot.org/t/notch-filter-pids-results-recommendation-review/127834) | Copter | normal | ✅ normal | - | - | 341 sn |
| [Tuning the slop and wobble out of an 18" quad](https://discuss.ardupilot.org/t/tuning-the-slop-and-wobble-out-of-an-18-quad/127898) | Copter | normal | ✅ normal | - | - | 117 sn |
| [Autotune is not giving a proper gains for CUAV x7+ and taking long tim](https://discuss.ardupilot.org/t/autotune-is-not-giving-a-proper-gains-for-cuav-x7-and-taking-long-time-for-tuning/128353) | Copter | normal | ✅ normal | - | - | 1431 sn |
| [Help to analyse PID review](https://discuss.ardupilot.org/t/help-to-analyse-pid-review/130716) | Copter | normal | ✅ normal | - | - | 350 sn |
| [Tuning Large drone - General Pixhawk & PID Help](https://discuss.ardupilot.org/t/tuning-large-drone-general-pixhawk-pid-help/133146) | Copter | normal | ✅ normal | - | - | 2100 sn |
| [Quick tune produces poor results compared to basic pid params](https://discuss.ardupilot.org/t/quick-tune-produces-poor-results-compared-to-basic-pid-params/133410) | Copter | normal | ✅ normal | - | - | 227 sn |
| [Help with Harmonic Notch Suggestions - Filter Review Tool](https://discuss.ardupilot.org/t/help-with-harmonic-notch-suggestions-filter-review-tool/137873) | Copter | normal | ✅ normal | - | - | 191 sn |
| [Plane - Yaw autotune not working](https://discuss.ardupilot.org/t/plane-yaw-autotune-not-working/138468) | Plane | normal | ✅ normal | - | - | 623 sn |
| [Filter Review - can't select "post" filter, can't turn off "estimated ](https://discuss.ardupilot.org/t/filter-review-cant-select-post-filter-cant-turn-off-estimated-post-filter/144164) | Copter | normal | ✅ normal | - | - | 4684025087295 sn |
| [Auto tune complete, but quad flies "drunk"](https://discuss.ardupilot.org/t/auto-tune-complete-but-quad-flies-drunk/35405) | Copter | normal | ✅ normal | - | - | 2792 sn |
| [Crash - help with bin analysis](https://discuss.ardupilot.org/t/crash-help-with-bin-analysis/42329) | Copter | normal | ✅ normal | - | - | 701 sn |
| [Autotune failed to save new PID with Copter-4.0.0-rc2](https://discuss.ardupilot.org/t/autotune-failed-to-save-new-pid-with-copter-4-0-0-rc2/49885) | Copter | normal | ✅ normal | - | - | 685 sn |
| [Autotune Roll result sluggish](https://discuss.ardupilot.org/t/autotune-roll-result-sluggish/50812) | Copter | normal | ✅ normal | - | - | 517 sn |
| [PID tuning and overshoot fix](https://discuss.ardupilot.org/t/pid-tuning-and-overshoot-fix/55480) | Copter | normal | ✅ normal | - | - | 359 sn |
| [Large PID's from Autotune](https://discuss.ardupilot.org/t/large-pids-from-autotune/63639) | Copter | normal | ✅ normal | - | - | 954 sn |
| [Pitch commands cause some yaw.🤔 I did not tune the copter](https://discuss.ardupilot.org/t/pitch-commands-cause-some-yaw-i-did-not-tune-the-copter/66822) | Copter | normal | ✅ normal | - | - | 189 sn |
| [Tuning a fleet of large quadrotors](https://discuss.ardupilot.org/t/tuning-a-fleet-of-large-quadrotors/67153) | Copter | normal | ✅ normal | - | - | 241 sn |
| [F450 log review](https://discuss.ardupilot.org/t/f450-log-review/78506) | Copter | normal | ✅ normal | - | - | 167 sn |
| [HELP with a 690 Hex AutoTune 4.1](https://discuss.ardupilot.org/t/help-with-a-690-hex-autotune-4-1/78816) | Copter | normal | ✅ normal | - | - | 533 sn |
| [What data log params to track for PID tuning](https://discuss.ardupilot.org/t/what-data-log-params-to-track-for-pid-tuning/81170) | Plane | normal | ✅ normal | - | - | 74 sn |
| [LOG analysis - sudden instability](https://discuss.ardupilot.org/t/log-analysis-sudden-instability/81354) | Copter | normal | ✅ normal | - | - | 2150 sn |
| [Help tuning large, overpowered quad](https://discuss.ardupilot.org/t/help-tuning-large-overpowered-quad/85103) | Copter | normal | ✅ normal | - | - | 390 sn |
| [AutoTune PID Values didn't Save](https://discuss.ardupilot.org/t/autotune-pid-values-didnt-save/88939) | Copter | normal | ✅ normal | - | - | 416 sn |
| [Low throttle hover, MAG issues, and DSHOT600](https://discuss.ardupilot.org/t/low-throttle-hover-mag-issues-and-dshot600/89501) | Copter | normal | ✅ normal | - | - | 249 sn |
| [Help tuning 14" quad](https://discuss.ardupilot.org/t/help-tuning-14-quad/90984) | Copter | normal | ✅ normal | - | - | 171 sn |
| [Internal error when using Quick Tuning Lua script](https://discuss.ardupilot.org/t/internal-error-when-using-quick-tuning-lua-script/91113) | Plane | normal | ✅ normal | - | - | 233 sn |
| [How is my Autotune result? Seems off](https://discuss.ardupilot.org/t/how-is-my-autotune-result-seems-off/91359) | Copter | normal | ✅ normal | - | - | 668 sn |
| [Autotune failing in 29inch drone](https://discuss.ardupilot.org/t/autotune-failing-in-29inch-drone/94516) | Copter | normal | ✅ normal | - | - | 213 sn |
| [Quadcopter not performing after Autotune](https://discuss.ardupilot.org/t/quadcopter-not-performing-after-autotune/95098) | Copter | normal | ✅ normal | - | - | 1067 sn |
| [Tuning X8 Heavy Lift - Tuning for Payload](https://discuss.ardupilot.org/t/tuning-x8-heavy-lift-tuning-for-payload/95759) | Copter | normal | ✅ normal | - | - | 787 sn |
| [AutoTune is failing. "Failing to level, please tune manually"](https://discuss.ardupilot.org/t/autotune-is-failing-failing-to-level-please-tune-manually/96277) | Copter | normal | ✅ normal | - | - | 218 sn |
| [Oscillations in poshold and land mode after a successful autotune](https://discuss.ardupilot.org/t/oscillations-in-poshold-and-land-mode-after-a-successful-autotune/99685) | Copter | normal | ✅ normal | - | - | 388 sn |
