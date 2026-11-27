# Gerçek kırım logları ile teşhis doğruluğu

Kaynak: discuss.ardupilot.org kamuya açık konular · Tarih: 2026-11-27 20:23 · Log sayısı: 659 (+52 okunamayan)

Etiket kaynağı: **uzman etiketleri** — her konudaki deneyimli/ekip üyelerinin yanıtları elle okunarak kırım/normal ve kök neden belirlendi (tools_data/crashbench/labels.json). Kök neden puanı yalnız uzmanların bir nedende birleştiği kırımlar üzerinden hesaplanır.

| Ölçüt | Değer |
|---|---|
| Genel doğruluk (kırım/olay ↔ normal) | %87 |
| Kırımı yakalama oranı (duyarlılık) | %87 (445/513) |
| Normal uçuşu doğru tanıma (özgüllük) | %89 (130/146) |
| Kesin 'kırım' kararı verilen kırım logları | 286/513 |
| Normal logda yanlış 'kırım' kararı | 2 |
| Kök neden uyumu (ana neden) | %48 (196/411) |
| Kök neden uyumu (ana veya ikincil nedenlerde) | %68 (278/411) |

## Sürüm geçmişi

| Tarih | Sürüm / etiket | Log | Doğruluk | Duyarlılık | Özgüllük | Kök neden |
|---|---|---|---|---|---|---|
| 2026-11-23 17:08 | v1.0.4 · forum başlığı | 65 | %77 | %85 | %56 | %21 |
| 2026-11-24 04:55 | v1.0.5 · uzman | 114 | %79 | %87 | %59 | %35 |
| 2026-11-24 05:03 | v1.0.6 · uzman | 117 | %80 | %87 | %59 | %51 |
| 2026-11-24 14:19 | v1.1.1 · uzman | 323 | %81 | %89 | %66 | %52 |
| 2026-11-24 21:20 | v1.1.2 · uzman · yalnız kurallar | 323 | %86 | %92 | %74 | %55 |
| 2026-11-27 14:10 | v1.1.12 | 454 | %89 | %90 | %85 | %52 |
| 2026-11-27 20:23 | dev | 659 | %87 | %87 | %89 | %48 |

## Öğrenen ikinci görüş (ML)

Aynı uzman etiketli 323 log üzerinde, her log dışarıda bırakılarak (leave-one-out) eğitilip ölçüldü. Model henüz kullanılmıyor: yalnız sınırdaki kararları düzeltir (kanıtsız 'sorunlu' → normal, model çok eminse normal → sorunlu); kesin kırım kanıtına dokunmaz.

| | Doğruluk | Duyarlılık | Özgüllük |
|---|---|---|---|
| Yalnız kurallar | %86 | %92 | %74 |
| Kurallar + model | %86 | %92 | %74 |

## Log listesi

| Konu | Araç | Etiket | Program | Kök neden (program) | Kök neden (uzman) | Süre |
|---|---|---|---|---|---|---|
| [MakeFlyEasy Fighter VTOL Crash](https://discuss.ardupilot.org/t/makeflyeasy-fighter-vtol-crash/100621) | Plane | crash | ✅ crash | control | - | 39 sn |
| [Crash on first flight after mayor crash](https://discuss.ardupilot.org/t/crash-on-first-flight-after-mayor-crash/10063) | Copter | crash | ✅ crash | control | compass | 89 sn |
| [Crash Inspection](https://discuss.ardupilot.org/t/crash-inspection/100654) | Copter | crash | ✅ crash | motor | motor | 1127 sn |
| [Quadplane total loss of control in FBWA leads to catastophic crash](https://discuss.ardupilot.org/t/quadplane-total-loss-of-control-in-fbwa-leads-to-catastophic-crash/10124) | Plane | crash | ✅ crash | stall | stall | 549 sn |
| [*SOLVED* Agricultural Quad Crash Analysis](https://discuss.ardupilot.org/t/solved-agricultural-quad-crash-analysis/101517) | Copter | crash | ✅ crash | motor | motor | 417 sn |
| [MFE Fighter VTOL crash - suspected IO MCU failure](https://discuss.ardupilot.org/t/mfe-fighter-vtol-crash-suspected-io-mcu-failure/102276) | Plane | crash | ✅ crash | control | - | 460 sn |
| [Arducopter initial tuning and setup - Oscillation issue](https://discuss.ardupilot.org/t/arducopter-initial-tuning-and-setup-oscillation-issue/103213) | Copter | crash | ✅ crash | unknown | control | 332 sn |
| [Crash when switching from RTL to Loiter](https://discuss.ardupilot.org/t/crash-when-switching-from-rtl-to-loiter/103732) | Copter | crash | ✅ crash | motor | battery | 862 sn |
| [Copter held full throttle after radio failsafe and crashed into tree a](https://discuss.ardupilot.org/t/copter-held-full-throttle-after-radio-failsafe-and-crashed-into-tree-after-several-errors/104106) | Copter | crash | ✅ crash | control | - | 489 sn |
| [Flight Crash Root Cause](https://discuss.ardupilot.org/t/flight-crash-root-cause/104199) | Copter | crash | ✅ crash | compass | ekf | 108 sn |
| [AutoTune: failing to level](https://discuss.ardupilot.org/t/autotune-failing-to-level/104302) | Copter | crash | ✅ crash | unknown | - | 1189 sn |
| [Quadcopter crashed](https://discuss.ardupilot.org/t/quadcopter-crashed/106052) | Copter | crash | ✅ crash | motor | motor | 304 sn |
| [VTOL Plane Crashed](https://discuss.ardupilot.org/t/vtol-plane-crashed/107364) | Plane | crash | ✅ crash | compass | control | 45 sn |
| [Unexpected left roll leading to crash](https://discuss.ardupilot.org/t/unexpected-left-roll-leading-to-crash/107732) | Plane | crash | ✅ crash | control | control | 1112 sn |
| [Coptor automatically begins hovering in a roughly elliptical orbit aro](https://discuss.ardupilot.org/t/coptor-automatically-begins-hovering-in-a-roughly-elliptical-orbit-around-the-takeoff-location-in-loiter-mode/107868) | Copter | crash | ✅ crash | vibration | compass | 36 sn |
| [RTL to QRTL causes spin dive crash...Why?](https://discuss.ardupilot.org/t/rtl-to-qrtl-causes-spin-dive-crash-why/108201) | Plane | crash | ✅ crash | motor | - | 771 sn |
| [1300mm X8 with old pids...flip of death](https://discuss.ardupilot.org/t/1300mm-x8-with-old-pids-flip-of-death/10824) | Copter | crash | ✅ crash | motor | - | 46 sn |
| [Drone Crashed - Would like to ask for assistance in analyzing the logs](https://discuss.ardupilot.org/t/drone-crashed-would-like-to-ask-for-assistance-in-analyzing-the-logs/109490) | Copter | crash | ✅ crash | motor | motor | 1123 sn |
| [Autotune Yaw Crash x 2](https://discuss.ardupilot.org/t/autotune-yaw-crash-x-2/110047) | Copter | crash | ✅ crash | motor | motor | 318 sn |
| [Crash on 550 quad with Pixhawk on 3.3.3](https://discuss.ardupilot.org/t/crash-on-550-quad-with-pixhawk-on-3-3-3/11018) | Copter | crash | ✅ crash | control | control | 100 sn |
| [Aircraft crashed during auto tune](https://discuss.ardupilot.org/t/aircraft-crashed-during-auto-tune/113111) | Plane | crash | ✅ crash | control | - | 415 sn |
| [Challenge: root-cause ID of crash](https://discuss.ardupilot.org/t/challenge-root-cause-id-of-crash/11603) | Copter | crash | ✅ crash | control | motor | 163 sn |
| [Quad crashed after 3.5 minutes flight. Can't figure out why](https://discuss.ardupilot.org/t/quad-crashed-after-3-5-minutes-flight-cant-figure-out-why/117102) | Copter | crash | ✅ crash | motor | motor | 608 sn |
| [Pixhawk crash after switched flight mode](https://discuss.ardupilot.org/t/pixhawk-crash-after-switched-flight-mode/11772) | Copter | crash | ✅ crash | control | motor | 67 sn |
| [Desired Pitch ignored - crashing at launch](https://discuss.ardupilot.org/t/desired-pitch-ignored-crashing-at-launch/117787) | Plane | crash | ✅ crash | control | control | 13 sn |
| [Autotune Crash - Sprung Mass X8 Cinelifter](https://discuss.ardupilot.org/t/autotune-crash-sprung-mass-x8-cinelifter/118077) | Copter | crash | ✅ crash | unknown | motor | 287 sn |
| [First crash with ardupilot, please help to find reason](https://discuss.ardupilot.org/t/first-crash-with-ardupilot-please-help-to-find-reason/118894) | Copter | crash | ✅ crash | motor | motor | 524 sn |
| [Sudden change in Pitch leading to a crash](https://discuss.ardupilot.org/t/sudden-change-in-pitch-leading-to-a-crash/119495) | Copter | crash | ✅ crash | motor | - | 261 sn |
| [Satellite count dropped to zero, drone crashed](https://discuss.ardupilot.org/t/satellite-count-dropped-to-zero-drone-crashed/120824) | Copter | crash | ✅ crash | motor | motor | 123 sn |
| [V-Tail Fixed Wing Crash](https://discuss.ardupilot.org/t/v-tail-fixed-wing-crash/121201) | Plane | crash | ✅ crash | control | control | 43 sn |
| [GPS Loss and Crash in Loiter](https://discuss.ardupilot.org/t/gps-loss-and-crash-in-loiter/121336) | Copter | crash | ✅ crash | control | motor | 269 sn |
| [Hexacopter Crash Log Analysis Request](https://discuss.ardupilot.org/t/hexacopter-crash-log-analysis-request/121620) | Copter | crash | ✅ crash | motor | motor | 1658 sn |
| [Multi-rotor crashed suddenly while in air](https://discuss.ardupilot.org/t/multi-rotor-crashed-suddenly-while-in-air/121766) | Copter | crash | ✅ crash | control | control | 180 sn |
| [Unexpected flyaway on our VTOL tailsitter drone](https://discuss.ardupilot.org/t/unexpected-flyaway-on-our-vtol-tailsitter-drone/122184) | Plane | crash | ✅ crash | motor | motor | 57 sn |
| [Arduplane no aileron input during auto mode resulting in a crash](https://discuss.ardupilot.org/t/arduplane-no-aileron-input-during-auto-mode-resulting-in-a-crash/122360) | Plane | crash | ✅ crash | compass | - | 56 sn |
| [QuadPlane Crashed After FBWA Transition - Unusual Current Drop](https://discuss.ardupilot.org/t/quadplane-crashed-after-fbwa-transition-unusual-current-drop/123223) | Plane | crash | ✅ crash | control | control | 484 sn |
| [Drone logs from our third crash](https://discuss.ardupilot.org/t/drone-logs-from-our-third-crash/125310) | Copter | crash | ✅ crash | motor | compass | 1708 sn |
| [Auto mode crash in skid steering rover](https://discuss.ardupilot.org/t/auto-mode-crash-in-skid-steering-rover/126159) | Rover | crash | ✅ crash | unknown | - | 1455 sn |
| [CRASH No Motor Output After Switching to RTL](https://discuss.ardupilot.org/t/crash-no-motor-output-after-switching-to-rtl/126622) | Copter | crash | ✅ crash | pilot | pilot | 336 sn |
| [Plz let me know the reason why copter had been crashed](https://discuss.ardupilot.org/t/plz-let-me-know-the-reason-why-copter-had-been-crashed/12717) | Copter | crash | ✅ crash | motor | gps | 182 sn |
| [Strange erroneous position measurement causing crash](https://discuss.ardupilot.org/t/strange-erroneous-position-measurement-causing-crash/127381) | Copter | crash | ✅ crash | control | - | 223 sn |
| [Copter crash - Request for help](https://discuss.ardupilot.org/t/copter-crash-request-for-help/12771) | Copter | crash | ✅ crash | control | - | 155 sn |
| [Octo-copter oscillating on takeoff then crash](https://discuss.ardupilot.org/t/octo-copter-oscillating-on-takeoff-then-crash/127808) | Copter | crash | ✅ crash | control | control | 35 sn |
| [Quadcopter crash after EKF error](https://discuss.ardupilot.org/t/quadcopter-crash-after-ekf-error/129116) | Copter | crash | ✅ crash | vibration | vibration | 126 sn |
| [X9 plus motor wobbling while takeoff and crashed](https://discuss.ardupilot.org/t/x9-plus-motor-wobbling-while-takeoff-and-crashed/129532) | Copter | crash | ✅ crash | control | control | 873 sn |
| [Maiden going perfectly then sudden flip over](https://discuss.ardupilot.org/t/maiden-going-perfectly-then-sudden-flip-over/12977) | Copter | crash | ✅ crash | control | - | 85 sn |
| [Crash during test flight](https://discuss.ardupilot.org/t/crash-during-test-flight/130270) | Copter | crash | ✅ crash | motor | - | 10 sn |
| [Drone crashed due to imu sensor issue or EKF primary error](https://discuss.ardupilot.org/t/drone-crashed-due-to-imu-sensor-issue-or-ekf-primary-error/130404) | Copter | crash | ✅ crash | motor | pilot | 71 sn |
| [After takeoff, it flew uncontrollably high and crashed](https://discuss.ardupilot.org/t/after-takeoff-it-flew-uncontrollably-high-and-crashed/131047) | Copter | crash | ✅ crash | motor | control | 39 sn |
| [X Quad 3.4.2 Crash - Sudden motors cut off command](https://discuss.ardupilot.org/t/x-quad-3-4-2-crash-sudden-motors-cut-off-command/13139) | Copter | crash | ✅ crash | radio | - | 1554 sn |
| [Copter flip on takeoff](https://discuss.ardupilot.org/t/copter-flip-on-takeoff/131783) | Copter | crash | ✅ crash | motor | motor | 99 sn |
| [Crash after two motors suddenly stopped](https://discuss.ardupilot.org/t/crash-after-two-motors-suddenly-stopped/132001) | Copter | crash | ✅ crash | motor | motor | 391 sn |
| [Help me analyze the logs of the Crash](https://discuss.ardupilot.org/t/help-me-analyze-the-logs-of-the-crash/132485) | Copter | crash | ✅ crash | pilot | control | 82 sn |
| [DRONE crashed after Notch filter setting](https://discuss.ardupilot.org/t/drone-crashed-after-notch-filter-setting/132566) | Copter | crash | ✅ crash | motor | motor | 322 sn |
| [Copter Crashed in Loiter Mode with Video](https://discuss.ardupilot.org/t/copter-crashed-in-loiter-mode-with-video/132570) | Copter | crash | ✅ crash | motor | motor | 236 sn |
| [Drone sudden crash log](https://discuss.ardupilot.org/t/drone-sudden-crash-log/133605) | Copter | crash | ✅ crash | vibration | motor | 29 sn |
| [Correct tuning response to manual tuning charts](https://discuss.ardupilot.org/t/correct-tuning-response-to-manual-tuning-charts/133895) | Copter | crash | ✅ crash | control | - | 151 sn |
| [Mid flight crash](https://discuss.ardupilot.org/t/mid-flight-crash/134011) | Copter | crash | ✅ crash | vibration | motor | 138 sn |
| [Stabilize is OK but guided loses stability and flips over.](https://discuss.ardupilot.org/t/stabilize-is-ok-but-guided-loses-stability-and-flips-over/134793) | Copter | crash | ✅ crash | motor | control | 143 sn |
| [Drone crashed while testing a GPS jammer](https://discuss.ardupilot.org/t/drone-crashed-while-testing-a-gps-jammer/135297) | Copter | crash | ✅ crash | motor | pilot | 845 sn |
| [700 size heli crashed after unintentional movment](https://discuss.ardupilot.org/t/700-size-heli-crashed-after-unintentional-movment/135314) | Copter | crash | ✅ crash | motor | control | 37 sn |
| [Crash Analysis Help - EKF Failures, Compass Inconsistent, GPS Dropouts](https://discuss.ardupilot.org/t/crash-analysis-help-ekf-failures-compass-inconsistent-gps-dropouts-arducopter-4-5-7/135472) | Copter | crash | ✅ crash | motor | motor | 180 sn |
| [Copter crash from 120m while doing mission](https://discuss.ardupilot.org/t/copter-crash-from-120m-while-doing-mission/135583) | Copter | crash | ✅ crash | motor | motor | 808 sn |
| [Pixhawk flyaway in stabilized mode with complete loss of control?](https://discuss.ardupilot.org/t/pixhawk-flyaway-in-stabilized-mode-with-complete-loss-of-control/13560) | Copter | crash | ✅ crash | control | radio | 774 sn |
| [Drone Crashed(flip) unexpectedly while hovering](https://discuss.ardupilot.org/t/drone-crashed-flip-unexpectedly-while-hovering/135702) | Copter | crash | ✅ crash | control | motor | 496 sn |
| [Hexa crash - One motor failure](https://discuss.ardupilot.org/t/hexa-crash-one-motor-failure/13576) | Copter | crash | ✅ crash | control | motor | 71422085125 sn |
| [Copter 4.6.1 Custom Build - Crash Dump](https://discuss.ardupilot.org/t/copter-4-6-1-custom-build-crash-dump/135782) | Copter | crash | ✅ crash | motor | motor | 66 sn |
| [FC power goes out and crashes in flight](https://discuss.ardupilot.org/t/fc-power-goes-out-and-crashes-in-flight/136727) | Copter | crash | ✅ crash | motor | motor | 121 sn |
| [Copter Fell out of the sky](https://discuss.ardupilot.org/t/copter-fell-out-of-the-sky/137243) | Copter | crash | ✅ crash | control | motor | 251 sn |
| [Crash analysis of hexacopter](https://discuss.ardupilot.org/t/crash-analysis-of-hexacopter/137474) | Copter | crash | ✅ crash | motor | motor | 1164 sn |
| [Crashed because of Compass?](https://discuss.ardupilot.org/t/crashed-because-of-compass/137647) | Copter | crash | ✅ crash | motor | control | 414 sn |
| [Cause of crash confirmation ](https://discuss.ardupilot.org/t/cause-of-crash-confirmation/138209) | Copter | crash | ✅ crash | pilot | pilot | 484 sn |
| [Drone Crashed, please help me to analyze the log and find the cause of](https://discuss.ardupilot.org/t/drone-crashed-please-help-me-to-analyze-the-log-and-find-the-cause-of-the-crash/138534) | Copter | crash | ✅ crash | motor | motor | 95 sn |
| [2nd crash need help with logs/diagnosis](https://discuss.ardupilot.org/t/2nd-crash-need-help-with-logs-diagnosis/13868) | Copter | crash | ✅ crash | battery | battery | 960 sn |
| [Crashed – It yawed badly and crashed due to compass anomalies in ArduC](https://discuss.ardupilot.org/t/crashed-it-yawed-badly-and-crashed-due-to-compass-anomalies-in-arducopter-4-6-0-with-micoair-nxt-px4-v2/138968) | Copter | crash | ✅ crash | motor | motor | 806 sn |
| [Singlecopter crashed after switching to loiter mode](https://discuss.ardupilot.org/t/singlecopter-crashed-after-switching-to-loiter-mode/139430) | Copter | crash | ✅ crash | control | - | 26 sn |
| [Drone Crash and Instability Issues After Rebuild – Need Help Debugging](https://discuss.ardupilot.org/t/drone-crash-and-instability-issues-after-rebuild-need-help-debugging/139585) | Copter | crash | ✅ crash | compass | control | 167 sn |
| [Crash after motor stopped](https://discuss.ardupilot.org/t/crash-after-motor-stopped/139836) | Copter | crash | ✅ crash | motor | motor | 460 sn |
| [Tandem Wing Tilt-Hexaplane Crashed during Auto Transition (Rolled Righ](https://discuss.ardupilot.org/t/tandem-wing-tilt-hexaplane-crashed-during-auto-transition-rolled-right-log-attached/140136) | Plane | crash | ✅ crash | compass | - | 53 sn |
| [EKF Fail = Crashed into a tree, Need Help With Logs](https://discuss.ardupilot.org/t/ekf-fail-crashed-into-a-tree-need-help-with-logs/140808) | Copter | crash | ✅ crash | vibration | gps | 134 sn |
| [Quadplane failed to complete transition and motors then turned off cau](https://discuss.ardupilot.org/t/quadplane-failed-to-complete-transition-and-motors-then-turned-off-causing-crash/140907) | Plane | crash | ✅ crash | control | motor | 76 sn |
| [Loss of Yaw control which led to controlled crash with hexa - Copter 3](https://discuss.ardupilot.org/t/loss-of-yaw-control-which-led-to-controlled-crash-with-hexa-copter-3-4-3/14092) | Copter | crash | ✅ crash | vibration | compass | 29 sn |
| [Find the cause of robocraft crash](https://discuss.ardupilot.org/t/find-the-cause-of-robocraft-crash/140954) | Copter | crash | ✅ crash | motor | battery | 1205 sn |
| [Crash Analysis - Uncommanded dip in throttle](https://discuss.ardupilot.org/t/crash-analysis-uncommanded-dip-in-throttle/141437) | Copter | crash | ✅ crash | control | radio | 694 sn |
| [All 4 Motors Suddenly stop spinning and copter falls to the ground](https://discuss.ardupilot.org/t/all-4-motors-suddenly-stop-spinning-and-copter-falls-to-the-ground/141658) | Copter | crash | ✅ crash | motor | motor | 177 sn |
| [Crashed on Takeoff after rotating Pixhawk 180° Query](https://discuss.ardupilot.org/t/crashed-on-takeoff-after-rotating-pixhawk-180-query/141882) | Copter | crash | ✅ crash | motor | control | 28 sn |
| [Crash after Autotune & "Prearm: ACRO_BAL_ROLL/PITCH" error](https://discuss.ardupilot.org/t/crash-after-autotune-prearm-acro-bal-roll-pitch-error/142188) | Copter | crash | ✅ crash | control | - | 63 sn |
| [Crash During Range Test at 2.6km – Need Help with Log Analysis](https://discuss.ardupilot.org/t/crash-during-range-test-at-2-6km-need-help-with-log-analysis/142364) | Copter | crash | ✅ crash | vibration | motor | 326 sn |
| [Quadcopter (28-inch Props): Motor-3 Stops Mid-Air After ~38 min Hover ](https://discuss.ardupilot.org/t/quadcopter-28-inch-props-motor-3-stops-mid-air-after-38-min-hover-arducopter-4-6-2/142441) | Copter | crash | ✅ crash | motor | motor | 2284 sn |
| [Review CubeOrange 21'' crash log](https://discuss.ardupilot.org/t/review-cubeorange-21-crash-log/142574) | Copter | crash | ✅ crash | motor | control | 536 sn |
| [3.4.2. Crash Quadcopter](https://discuss.ardupilot.org/t/3-4-2-crash-quadcopter/14313) | Copter | crash | ✅ crash | motor | motor | 306 sn |
| [Mid-flight IOMCU processor reset caused vehicle crash](https://discuss.ardupilot.org/t/mid-flight-iomcu-processor-reset-caused-vehicle-crash/143216) | Copter | crash | ✅ crash | control | power | 101 sn |
| [Drone has crashed, log file attached](https://discuss.ardupilot.org/t/drone-has-crashed-log-file-attached/143330) | Copter | crash | ✅ crash | control | control | 235 sn |
| [New beta fly away](https://discuss.ardupilot.org/t/new-beta-fly-away/144128) | Copter | crash | ✅ crash | compass | compass | 52 sn |
| [The drone suddenly went out of‑control and crashed!](https://discuss.ardupilot.org/t/the-drone-suddenly-went-out-of-control-and-crashed/144522) | Copter | crash | ✅ crash | compass | motor | 46 sn |
| [How can explain my crash?](https://discuss.ardupilot.org/t/how-can-explain-my-crash/144992) | Plane | crash | ✅ crash | motor | pilot | 179 sn |
| [Multiple crashes in auto mode quadcopter](https://discuss.ardupilot.org/t/multiple-crashes-in-auto-mode-quadcopter/145465) | Copter | crash | ✅ crash | vibration | control | 1994 sn |
| [Oscillations and crash](https://discuss.ardupilot.org/t/oscillations-and-crash/145571) | Copter | crash | ✅ crash | motor | - | 215 sn |
| [X500 Yaw instability during autotune, crash and takeoff issues](https://discuss.ardupilot.org/t/x500-yaw-instability-during-autotune-crash-and-takeoff-issues/145954) | Copter | crash | ✅ crash | motor | control | 1213 sn |
| [Unexpected flips in LOITER mode](https://discuss.ardupilot.org/t/unexpected-flips-in-loiter-mode/14758) | Copter | crash | ✅ crash | vibration | motor | 31 sn |
| [Violent spinning on maiden flight w/ inverted crash (Loiter)](https://discuss.ardupilot.org/t/violent-spinning-on-maiden-flight-w-inverted-crash-loiter/15027) | Copter | crash | ✅ crash | control | control | 55 sn |
| [V3.4.4 - Quad Flyaway - CTUN.DAlt is NaN](https://discuss.ardupilot.org/t/v3-4-4-quad-flyaway-ctun-dalt-is-nan/15489) | Copter | crash | ✅ crash | motor | - | 731 sn |
| [Almost fly away during hover test](https://discuss.ardupilot.org/t/almost-fly-away-during-hover-test/15681) | Copter | crash | ✅ crash | unknown | radio | 320 sn |
| [Crash When Increase waypoint speed from 5m/s to 8m/s](https://discuss.ardupilot.org/t/crash-when-increase-waypoint-speed-from-5m-s-to-8m-s/15871) | Copter | crash | ✅ crash | control | motor | 77 sn |
| [Pixhawk 2.1 & Here+ Crash; Possible mech failure?](https://discuss.ardupilot.org/t/pixhawk-2-1-here-crash-possible-mech-failure/16117) | Copter | crash | ✅ crash | motor | control | 15 sn |
| [Octocopter Crash](https://discuss.ardupilot.org/t/octocopter-crash/16695) | Copter | crash | ✅ crash | control | motor | 124 sn |
| [Hexacopter crash after EKF Check 2](https://discuss.ardupilot.org/t/hexacopter-crash-after-ekf-check-2/16834) | Copter | crash | ✅ crash | ekf | gps | 122 sn |
| [3.5.0 rc4 user Here+RTK is Crashed](https://discuss.ardupilot.org/t/3-5-0-rc4-user-here-rtk-is-crashed/16846) | Copter | crash | ✅ crash | motor | - | 84 sn |
| [Quadcopter crash at Loiter - magnetometer/accel/gyro or mechanical mot](https://discuss.ardupilot.org/t/quadcopter-crash-at-loiter-magnetometer-accel-gyro-or-mechanical-motor-issue/17053) | Copter | crash | ✅ crash | motor | motor | 122 sn |
| [Cube 2.1,3.4.6,(I think), MP 1.3.48, New to Pixhawk2, Crash, Logs](https://discuss.ardupilot.org/t/cube-2-1-3-4-6-i-think-mp-1-3-48-new-to-pixhawk2-crash-logs/17161) | Copter | crash | ✅ crash | control | - | 314 sn |
| [Copter 3.2.1 on APM sudden drop in Altitude in Alt-Hold up to a crash](https://discuss.ardupilot.org/t/copter-3-2-1-on-apm-sudden-drop-in-altitude-in-alt-hold-up-to-a-crash/17266) | Copter | crash | ✅ crash | power | vibration | 205737 sn |
| [Mysterious behaviour (or not?) leading to crash](https://discuss.ardupilot.org/t/mysterious-behaviour-or-not-leading-to-crash/17679) | Copter | crash | ✅ crash | control | control | 297 sn |
| [A weird crash...So weird](https://discuss.ardupilot.org/t/a-weird-crash-so-weird/17777) | Copter | crash | ✅ crash | compass | gps | 29 sn |
| [Loss of height in AltHold // w/o AutoTune // touchdown of Quad // LOG ](https://discuss.ardupilot.org/t/loss-of-height-in-althold-w-o-autotune-touchdown-of-quad-log-attached/18074) | Copter | crash | ✅ crash | unknown | motor | 98 sn |
| [Pixhawk 1 Octo-Auto takeoff into violent pitch/roll/yaw oscillations a](https://discuss.ardupilot.org/t/pixhawk-1-octo-auto-takeoff-into-violent-pitch-roll-yaw-oscillations-and-bad-9k-crash/18298) | Copter | crash | ✅ crash | motor | compass | 54 sn |
| [Weird Crash after updating to 3.5 RC7](https://discuss.ardupilot.org/t/weird-crash-after-updating-to-3-5-rc7/18300) | Copter | crash | ✅ crash | motor | motor | 62 sn |
| [It just dropped out of the air?](https://discuss.ardupilot.org/t/it-just-dropped-out-of-the-air/18361) | Copter | crash | ✅ crash | motor | motor | 63 sn |
| [3DR X8+ Fly Away due to EKF_CHECK-2, FAILSAFE_EKF-1](https://discuss.ardupilot.org/t/3dr-x8-fly-away-due-to-ekf-check-2-failsafe-ekf-1/18482) | Copter | crash | ✅ crash | vibration | gps | 28 sn |
| [Flip on autonomous takeoff](https://discuss.ardupilot.org/t/flip-on-autonomous-takeoff/18927) | Copter | crash | ✅ crash | motor | - | 257 sn |
| [Automission misses WP2, FlyAway, Crash](https://discuss.ardupilot.org/t/automission-misses-wp2-flyaway-crash/19146) | Copter | crash | ✅ crash | motor | gps | 84 sn |
| [1.4 m quad Copter crashed without any error in log](https://discuss.ardupilot.org/t/1-4-m-quad-copter-crashed-without-any-error-in-log/19550) | Copter | crash | ✅ crash | motor | vibration | 132 sn |
| [Major EK2 Fail and big crash](https://discuss.ardupilot.org/t/major-ek2-fail-and-big-crash/19650) | Copter | crash | ✅ crash | control | ekf | 27 sn |
| [Some troubles about copter crashing, need for help](https://discuss.ardupilot.org/t/some-troubles-about-copter-crashing-need-for-help/21253) | Copter | crash | ✅ crash | control | motor | 23 sn |
| [Pixhawk v2.1 flying great in auto...then bad crash](https://discuss.ardupilot.org/t/pixhawk-v2-1-flying-great-in-auto-then-bad-crash/21879) | Copter | crash | ✅ crash | motor | - | 310 sn |
| [Quad Fell out of Sky](https://discuss.ardupilot.org/t/quad-fell-out-of-sky/21885) | Copter | crash | ✅ crash | power | vibration | 201932 sn |
| [New pilot - New crash](https://discuss.ardupilot.org/t/new-pilot-new-crash/22488) | Copter | crash | ✅ crash | control | motor | 20 sn |
| [Throw mode : crash, motors spin too late](https://discuss.ardupilot.org/t/throw-mode-crash-motors-spin-too-late/22556) | Copter | crash | ✅ crash | motor | pilot | 243 sn |
| [Quad Flip at takeoff](https://discuss.ardupilot.org/t/quad-flip-at-takeoff/25187) | Copter | crash | ✅ crash | control | motor | 35 sn |
| [Crash multiple times](https://discuss.ardupilot.org/t/crash-multiple-times/25966) | Copter | crash | ✅ crash | vibration | vibration | 29 sn |
| [Copter crash in RTL mode](https://discuss.ardupilot.org/t/copter-crash-in-rtl-mode/26036) | Copter | crash | ✅ crash | motor | - | 112 sn |
| [Crashed after switching from FBWA to Manual](https://discuss.ardupilot.org/t/crashed-after-switching-from-fbwa-to-manual/27379) | Plane | crash | ✅ crash | control | - | 596 sn |
| [First flight - first crash](https://discuss.ardupilot.org/t/first-flight-first-crash/28112) | Copter | crash | ✅ crash | control | control | 183 sn |
| [3.8.4 Crash after TAKEOFF](https://discuss.ardupilot.org/t/3-8-4-crash-after-takeoff/28155) | Plane | crash | ✅ crash | control | control | 505 sn |
| [Hexacopter CRASH investigation](https://discuss.ardupilot.org/t/hexacopter-crash-investigation/29778) | Copter | crash | ✅ crash | motor | motor | 760 sn |
| [Maiden Ended In Crash; Wobble Then Drop](https://discuss.ardupilot.org/t/maiden-ended-in-crash-wobble-then-drop/30270) | Copter | crash | ✅ crash | vibration | vibration | 256 sn |
| [The helicopter failed at high altitude，crash！](https://discuss.ardupilot.org/t/the-helicopter-failed-at-high-altitude-crash/30377) | Copter | crash | ✅ crash | motor | control | 179 sn |
| [LOG analysis needed // failure in AutoMission // circle & crash at way](https://discuss.ardupilot.org/t/log-analysis-needed-failure-in-automission-circle-crash-at-waypoint/30458) | Plane | crash | ✅ crash | control | control | 3027 sn |
| [Crash when autotune](https://discuss.ardupilot.org/t/crash-when-autotune/30683) | Copter | crash | ✅ crash | vibration | motor | 60 sn |
| [Pixhawk 2.1 CRASHED while Auto-Take off](https://discuss.ardupilot.org/t/pixhawk-2-1-crashed-while-auto-take-off/31376) | Copter | crash | ✅ crash | vibration | vibration | 25 sn |
| [An AutoTune Puzzle](https://discuss.ardupilot.org/t/an-autotune-puzzle/31770) | Copter | crash | ✅ crash | motor | - | 918 sn |
| [No response to throttle seconds before crash](https://discuss.ardupilot.org/t/no-response-to-throttle-seconds-before-crash/31874) | Copter | crash | ✅ crash | unknown | battery | 586 sn |
| [Arducopter 3.5.7 Crash](https://discuss.ardupilot.org/t/arducopter-3-5-7-crash/32284) | Copter | crash | ✅ crash | motor | motor | 51 sn |
| [Unusual octocopter crash](https://discuss.ardupilot.org/t/unusual-octocopter-crash/33183) | Copter | crash | ✅ crash | motor | vibration | 105 sn |
| [T650 3.6-10 crash during autotune](https://discuss.ardupilot.org/t/t650-3-6-10-crash-during-autotune/33347) | Copter | crash | ✅ crash | motor | motor | 60 sn |
| [Craziest / weirdest crash / runaway - What went wrong?](https://discuss.ardupilot.org/t/craziest-weirdest-crash-runaway-what-went-wrong/33507) | Copter | crash | ✅ crash | control | radio | 835 sn |
| [Why did it crash](https://discuss.ardupilot.org/t/why-did-it-crash/33536) | Copter | crash | ✅ crash | control | motor | 56 sn |
| [HELP! One Drone Flyaway during RTL and 2nd drone Fly away during Takeo](https://discuss.ardupilot.org/t/help-one-drone-flyaway-during-rtl-and-2nd-drone-fly-away-during-takeoff/33546) | Copter | crash | ✅ crash | control | - | 293 sn |
| [Crash due to EKF primary changed after GPS glitch](https://discuss.ardupilot.org/t/crash-due-to-ekf-primary-changed-after-gps-glitch/33955) | Copter | crash | ✅ crash | gps | ekf | 260 sn |
| [Help with log analysis after maiden crash in Autotune](https://discuss.ardupilot.org/t/help-with-log-analysis-after-maiden-crash-in-autotune/34453) | Plane | crash | ✅ crash | control | control | 17 sn |
| [Skid Steer Rover moves backward in GUIDED mode. - FCU Crash: Going to ](https://discuss.ardupilot.org/t/skid-steer-rover-moves-backward-in-guided-mode-fcu-crash-going-to-hold/34492) | Rover | crash | ✅ crash | power | - | 10 sn |
| [Drone crash Analysis](https://discuss.ardupilot.org/t/drone-crash-analysis/34498) | Copter | crash | ✅ crash | motor | motor | 299 sn |
| [Need help - Plane crashed on turning. No Idea why](https://discuss.ardupilot.org/t/need-help-plane-crashed-on-turning-no-idea-why/34898) | Plane | crash | ✅ crash | control | battery | 1331 sn |
| [Pixhawk - Copter 3.6 - Always Tend to fly forward or flips forward](https://discuss.ardupilot.org/t/pixhawk-copter-3-6-always-tend-to-fly-forward-or-flips-forward/35024) | Copter | crash | ✅ crash | battery | control | 481 sn |
| [Roll/pitch parts from desired roll/pitch, causing crash](https://discuss.ardupilot.org/t/roll-pitch-parts-from-desired-roll-pitch-causing-crash/35095) | Plane | crash | ✅ crash | control | - | 4928 sn |
| [Drone crashed during takeoff](https://discuss.ardupilot.org/t/drone-crashed-during-takeoff/36162) | Copter | crash | ✅ crash | motor | vibration | 13 sn |
| [OctoQuad Drone crashed after takeoff](https://discuss.ardupilot.org/t/octoquad-drone-crashed-after-takeoff/38567) | Copter | crash | ✅ crash | gps | - | 956 sn |
| [Crash with 3.6.6 copter](https://discuss.ardupilot.org/t/crash-with-3-6-6-copter/38764) | Copter | crash | ✅ crash | motor | ekf | 2018 sn |
| [Stopped logging for 2.5 seconds and crashed](https://discuss.ardupilot.org/t/stopped-logging-for-2-5-seconds-and-crashed/39265) | Copter | crash | ✅ crash | motor | power | 40 sn |
| [Crash - ALT_HOLD - Drone climbs, no throttle control](https://discuss.ardupilot.org/t/crash-alt-hold-drone-climbs-no-throttle-control/39705) | Copter | crash | ✅ crash | motor | ekf | 15 sn |
| [3.6.7 installed and tested- drone crashed- firmware issue or battery o](https://discuss.ardupilot.org/t/3-6-7-installed-and-tested-drone-crashed-firmware-issue-or-battery-or-something-else-unable-to-find-out/39722) | Copter | crash | ✅ crash | motor | motor | 81 sn |
| [Log Review Request - QUAD](https://discuss.ardupilot.org/t/log-review-request-quad/40392) | Copter | crash | ✅ crash | control | radio | 199 sn |
| [Drone flipped. Motor balance-Fail, Test Compass-Fail, Test GPS-Fail](https://discuss.ardupilot.org/t/drone-flipped-motor-balance-fail-test-compass-fail-test-gps-fail/40515) | Copter | crash | ✅ crash | motor | - | 35 sn |
| [Copter lost stability and crashed immediately after RTL was turned off](https://discuss.ardupilot.org/t/copter-lost-stability-and-crashed-immediately-after-rtl-was-turned-off-and-defaulted-to-loiter-3-6-7/40649) | Copter | crash | ✅ crash | motor | motor | 586 sn |
| [From Stabilize to Loiter Super Simple copter crash](https://discuss.ardupilot.org/t/from-stabilize-to-loiter-super-simple-copter-crash/40664) | Copter | crash | ✅ crash | motor | control | 98 sn |
| [Need help diagnosing a plane crash during AUTO](https://discuss.ardupilot.org/t/need-help-diagnosing-a-plane-crash-during-auto/40986) | Plane | crash | ✅ crash | control | - | 757 sn |
| [[solved] Strange Crash and Prearm IOMCU error on cube?](https://discuss.ardupilot.org/t/solved-strange-crash-and-prearm-iomcu-error-on-cube/41509) | Copter | crash | ✅ crash | motor | - | 667 sn |
| [Crash on a X8 after starting AutoTune](https://discuss.ardupilot.org/t/crash-on-a-x8-after-starting-autotune/42085) | Copter | crash | ✅ crash | motor | motor | 642 sn |
| [Crashed in Autotune in Copter 3.6 seems like ESC problem?](https://discuss.ardupilot.org/t/crashed-in-autotune-in-copter-3-6-seems-like-esc-problem/42115) | Copter | crash | ✅ crash | motor | control | 195 sn |
| [Kakute F7 6 inch - Flip & Crash - Need help with logs](https://discuss.ardupilot.org/t/kakute-f7-6-inch-flip-crash-need-help-with-logs/42527) | Copter | crash | ✅ crash | motor | motor | 80 sn |
| [Autotune crash 3.6.8](https://discuss.ardupilot.org/t/autotune-crash-3-6-8/42652) | Copter | crash | ✅ crash | motor | control | 1165 sn |
| [Switching to auto mode with no mission ever loaded on drone causes los](https://discuss.ardupilot.org/t/switching-to-auto-mode-with-no-mission-ever-loaded-on-drone-causes-loss-of-control/42859) | Copter | crash | ✅ crash | motor | - | 42 sn |
| [X8 flip-over during take-off](https://discuss.ardupilot.org/t/x8-flip-over-during-take-off/42972) | Copter | crash | ✅ crash | control | - | 170 sn |
| [Quadplane suddenly pitched down at high angle and crash in FBW-A](https://discuss.ardupilot.org/t/quadplane-suddenly-pitched-down-at-high-angle-and-crash-in-fbw-a/43621) | Plane | crash | ✅ crash | control | control | 124 sn |
| [Arducopter 3.6.9 made sudden crash from 10 meters](https://discuss.ardupilot.org/t/arducopter-3-6-9-made-sudden-crash-from-10-meters/43660) | Copter | crash | ✅ crash | power | radio | 129 sn |
| [Quadcopter flipped in mid air and crashed after motor outputs with unu](https://discuss.ardupilot.org/t/quadcopter-flipped-in-mid-air-and-crashed-after-motor-outputs-with-unusual-values/44132) | Copter | crash | ✅ crash | control | - | 75 sn |
| [Drone Crash on Min Speed Testing](https://discuss.ardupilot.org/t/drone-crash-on-min-speed-testing/44241) | Plane | crash | ✅ crash | control | power | 793 sn |
| [Arducopter v 3.6.9 with pixhawk+m8n gps first flight crash after selec](https://discuss.ardupilot.org/t/arducopter-v-3-6-9-with-pixhawk-m8n-gps-first-flight-crash-after-selecting-mode-rtl/44792) | Copter | crash | ✅ crash | vibration | vibration | 204 sn |
| [Crashed Log Analysis](https://discuss.ardupilot.org/t/crashed-log-analysis/44903) | Copter | crash | ✅ crash | motor | motor | 369 sn |
| [Help in analyzing the log file,arducopter v 3.6.9 -copter crash](https://discuss.ardupilot.org/t/help-in-analyzing-the-log-file-arducopter-v-3-6-9-copter-crash/44912) | Copter | crash | ✅ crash | vibration | vibration | 68 sn |
| [HELP with the log analysis for drone crash](https://discuss.ardupilot.org/t/help-with-the-log-analysis-for-drone-crash/44973) | Copter | crash | ✅ crash | motor | - | 14 sn |
| [Need expert eyes - Unknown crash!](https://discuss.ardupilot.org/t/need-expert-eyes-unknown-crash/46102) | Copter | crash | ✅ crash | motor | power | 16 sn |
| [Copter crashed! Could you please help me?](https://discuss.ardupilot.org/t/copter-crashed-could-you-please-help-me/46644) | Copter | crash | ✅ crash | control | motor | 40 sn |
| [Copter crashes without error code](https://discuss.ardupilot.org/t/copter-crashes-without-error-code/47139) | Copter | crash | ✅ crash | control | power | 1341 sn |
| [[solved]Help in Autotune crash - what went wrong](https://discuss.ardupilot.org/t/solved-help-in-autotune-crash-what-went-wrong/47298) | Copter | crash | ✅ crash | motor | motor | 96 sn |
| [Crashed! Crashed into a tower while do the mission! Deviate from sched](https://discuss.ardupilot.org/t/crashed-crashed-into-a-tower-while-do-the-mission-deviate-from-scheduled-course/48069) | Copter | crash | ✅ crash | motor | control | 735 sn |
| [Second flight... and second crash :(](https://discuss.ardupilot.org/t/second-flight-and-second-crash/48763) | Copter | crash | ✅ crash | power | battery | 602860 sn |
| [Autotune crash - twice!](https://discuss.ardupilot.org/t/autotune-crash-twice/50541) | Copter | crash | ✅ crash | motor | power | 297 sn |
| [Don't command RTL, Loiter and crash](https://discuss.ardupilot.org/t/dont-command-rtl-loiter-and-crash/52129) | Copter | crash | ✅ crash | vibration | - | 30 sn |
| [Crashed on third flight without wind](https://discuss.ardupilot.org/t/crashed-on-third-flight-without-wind/52164) | Copter | crash | ✅ crash | motor | battery | 353 sn |
| [Quadcopter fly away](https://discuss.ardupilot.org/t/quadcopter-fly-away/52948) | Copter | crash | ✅ crash | gps | vibration | 1332 sn |
| [Impossible takeoff flyaway ended in crash](https://discuss.ardupilot.org/t/impossible-takeoff-flyaway-ended-in-crash/53060) | Copter | crash | ✅ crash | unknown | motor | 76 sn |
| [Octocopter on Pixhawk 2.4.8 loss of control then crash](https://discuss.ardupilot.org/t/octocopter-on-pixhawk-2-4-8-loss-of-control-then-crash/53229) | Copter | crash | ✅ crash | control | vibration | 209 sn |
| [Crash! Drone went up without control, passthrough FrSky telemetry bug?](https://discuss.ardupilot.org/t/crash-drone-went-up-without-control-passthrough-frsky-telemetry-bug/53585) | Copter | crash | ✅ crash | motor | ekf | 36 sn |
| [Wrong crash check](https://discuss.ardupilot.org/t/wrong-crash-check/53734) | Copter | crash | ✅ crash | control | pilot | 527 sn |
| [Copter crashed after successful autotune](https://discuss.ardupilot.org/t/copter-crashed-after-successful-autotune/54470) | Copter | crash | ✅ crash | control | control | 1304 sn |
| [AltHold crash, need help for log analyze](https://discuss.ardupilot.org/t/althold-crash-need-help-for-log-analyze/54829) | Copter | crash | ✅ crash | motor | motor | 31 sn |
| [Quad falls out of sky on yaw](https://discuss.ardupilot.org/t/quad-falls-out-of-sky-on-yaw/55193) | Copter | crash | ✅ crash | motor | - | 60 sn |
| [Crash in PosHold](https://discuss.ardupilot.org/t/crash-in-poshold/55598) | Copter | crash | ✅ crash | control | gps | 52 sn |
| [Crash Analysis - QuadCopter](https://discuss.ardupilot.org/t/crash-analysis-quadcopter/55749) | Copter | crash | ✅ crash | motor | motor | 251 sn |
| [Crash, collision with tower](https://discuss.ardupilot.org/t/crash-collision-with-tower/56621) | Copter | crash | ✅ crash | motor | - | 266 sn |
| [Plane 4.0 had a flyaway in auto, looks like it could be a bug](https://discuss.ardupilot.org/t/plane-4-0-had-a-flyaway-in-auto-looks-like-it-could-be-a-bug/56689) | Plane | crash | ✅ crash | control | stall | 672 sn |
| [OpenSolo 4.0.3 Crash](https://discuss.ardupilot.org/t/opensolo-4-0-3-crash/56806) | Copter | crash | ✅ crash | control | control | 404 sn |
| [A problem about EKF variance and crash](https://discuss.ardupilot.org/t/a-problem-about-ekf-variance-and-crash/56863) | Copter | crash | ✅ crash | vibration | vibration | 107 sn |
| [CRASH: Hexacopter / PX4 - Please, help me find the cause](https://discuss.ardupilot.org/t/crash-hexacopter-px4-please-help-me-find-the-cause/56949) | Copter | crash | ✅ crash | motor | control | 255 sn |
| [Review my crash analysis](https://discuss.ardupilot.org/t/review-my-crash-analysis/56960) | Copter | crash | ✅ crash | motor | motor | 1857 sn |
| [Need help analyzing a crash](https://discuss.ardupilot.org/t/need-help-analyzing-a-crash/57097) | Copter | crash | ✅ crash | motor | compass | 2601 sn |
| [Hexa crash at maiden flight](https://discuss.ardupilot.org/t/hexa-crash-at-maiden-flight/57185) | Copter | crash | ✅ crash | battery | power | 1636 sn |
| [Crash first flight: ardupilot 4.0 help!](https://discuss.ardupilot.org/t/crash-first-flight-ardupilot-4-0-help/57299) | Copter | crash | ✅ crash | vibration | battery | 173 sn |
| [My Pixhawk Cube Orangle flips over when autotunig](https://discuss.ardupilot.org/t/my-pixhawk-cube-orangle-flips-over-when-autotunig/57474) | Copter | crash | ✅ crash | motor | control | 90 sn |
| [CRASH! during AUTOTUNE - with video](https://discuss.ardupilot.org/t/crash-during-autotune-with-video/57546) | Copter | crash | ✅ crash | motor | motor | 480 sn |
| [Bixler QuadPlane Crash after Perfect Transition to FBWA Mode](https://discuss.ardupilot.org/t/bixler-quadplane-crash-after-perfect-transition-to-fbwa-mode/57706) | Plane | crash | ✅ crash | control | stall | 653 sn |
| [Fatal crash on a tried and tested rig. 4.0.5 / omnibus f4pro / r9mm](https://discuss.ardupilot.org/t/fatal-crash-on-a-tried-and-tested-rig-4-0-5-omnibus-f4pro-r9mm/59240) | Plane | crash | ✅ crash | control | stall | 172 sn |
| [Large quad autotune crash](https://discuss.ardupilot.org/t/large-quad-autotune-crash/60455) | Copter | crash | ✅ crash | motor | control | 57 sn |
| [[RESOLVED] Land was not detected and crash detected](https://discuss.ardupilot.org/t/resolved-land-was-not-detected-and-crash-detected/60538) | Copter | crash | ✅ crash | motor | vibration | 691 sn |
| [Copter Crash ALTHOLD](https://discuss.ardupilot.org/t/copter-crash-althold/60815) | Copter | crash | ✅ crash | vibration | vibration | 161 sn |
| [Confirmation that this crash was due to a failed motor](https://discuss.ardupilot.org/t/confirmation-that-this-crash-was-due-to-a-failed-motor/61014) | Copter | crash | ✅ crash | motor | motor | 824 sn |
| [Crash - Death Spiral - Arduplane 4.0.1](https://discuss.ardupilot.org/t/crash-death-spiral-arduplane-4-0-1/61150) | Plane | crash | ✅ crash | control | stall | 2840 sn |
| [Logs help.Copter fly away](https://discuss.ardupilot.org/t/logs-help-copter-fly-away/62240) | Copter | crash | ✅ crash | gps | radio | 1062 sn |
| [The fall of the UAV in automatic mode, search for the cause](https://discuss.ardupilot.org/t/the-fall-of-the-uav-in-automatic-mode-search-for-the-cause/62335) | Copter | crash | ✅ crash | motor | control | 20 sn |
| [After updating to copter 4.0 drone crashes](https://discuss.ardupilot.org/t/after-updating-to-copter-4-0-drone-crashes/62779) | Copter | crash | ✅ crash | control | pilot | 55 sn |
| [Crash when activate autotune](https://discuss.ardupilot.org/t/crash-when-activate-autotune/63238) | Copter | crash | ✅ crash | motor | pilot | 84 sn |
| [Crashed Tarot 680 Pro Pixhawk 2.4.7](https://discuss.ardupilot.org/t/crashed-tarot-680-pro-pixhawk-2-4-7/64557) | Copter | crash | ✅ crash | motor | control | 704 sn |
| [Effect of weight on tuning](https://discuss.ardupilot.org/t/effect-of-weight-on-tuning/65725) | Copter | crash | ✅ crash | control | - | 1184 sn |
| [Quad lifts off and lands (crashes) immediatly [solved: was bad battery](https://discuss.ardupilot.org/t/quad-lifts-off-and-lands-crashes-immediatly-solved-was-bad-battery/65907) | Copter | crash | ✅ crash | motor | battery | 37 sn |
| [Tarot 650 flyaway issues on Loiter and slow response on sticks](https://discuss.ardupilot.org/t/tarot-650-flyaway-issues-on-loiter-and-slow-response-on-sticks/66182) | Copter | crash | ✅ crash | vibration | vibration | 1267 sn |
| [Help in analysis of logs after crashing(autotuning)](https://discuss.ardupilot.org/t/help-in-analysis-of-logs-after-crashing-autotuning/66230) | Copter | crash | ✅ crash | motor | motor | 801 sn |
| [Flip over on Takeoff - Large Copter 30 Inch](https://discuss.ardupilot.org/t/flip-over-on-takeoff-large-copter-30-inch/67267) | Copter | crash | ✅ crash | motor | motor | 39 sn |
| [15" quadcopter crash in wind](https://discuss.ardupilot.org/t/15-quadcopter-crash-in-wind/68114) | Copter | crash | ✅ crash | motor | control | 911 sn |
| [Yet another s800 crash (after a successful flight)](https://discuss.ardupilot.org/t/yet-another-s800-crash-after-a-successful-flight/68348) | Plane | crash | ✅ crash | control | control | 47 sn |
| [Need help with crash analysis](https://discuss.ardupilot.org/t/need-help-with-crash-analysis/68371) | Copter | crash | ✅ crash | compass | vibration | 811 sn |
| [Crash ArduCopter 4.0.7 (log attached)](https://discuss.ardupilot.org/t/crash-arducopter-4-0-7-log-attached/69409) | Copter | crash | ✅ crash | motor | radio | 33 sn |
| [Crash on maiden when switched to FBWA](https://discuss.ardupilot.org/t/crash-on-maiden-when-switched-to-fbwa/70027) | Plane | crash | ✅ crash | control | control | 1525 sn |
| [Copter wants to flip on takeoff please help](https://discuss.ardupilot.org/t/copter-wants-to-flip-on-takeoff-please-help/70128) | Copter | crash | ✅ crash | control | control | 129 sn |
| [Crash due to vibrations](https://discuss.ardupilot.org/t/crash-due-to-vibrations/70240) | Copter | crash | ✅ crash | control | vibration | 566 sn |
| [Mini Talon crash investigation](https://discuss.ardupilot.org/t/mini-talon-crash-investigation/70766) | Plane | crash | ✅ crash | control | radio | 1368 sn |
| [Copter uncontrolled climb and fly away in position hold mode](https://discuss.ardupilot.org/t/copter-uncontrolled-climb-and-fly-away-in-position-hold-mode/72113) | Copter | crash | ✅ crash | pilot | control | 301 sn |
| [EKF failsafe leads to crash, please help with the log](https://discuss.ardupilot.org/t/ekf-failsafe-leads-to-crash-please-help-with-the-log/72303) | Copter | crash | ✅ crash | gps | ekf | 451 sn |
| [Troubleshooting hexarotor oscillation movement until crash](https://discuss.ardupilot.org/t/troubleshooting-hexarotor-oscillation-movement-until-crash/72575) | Copter | crash | ✅ crash | motor | control | 109 sn |
| [RTL Crash using 4.1.0 beta1](https://discuss.ardupilot.org/t/rtl-crash-using-4-1-0-beta1/72983) | Plane | crash | ✅ crash | control | control | 521 sn |
| [Strange crash with copter 4.0.5](https://discuss.ardupilot.org/t/strange-crash-with-copter-4-0-5/73200) | Copter | crash | ✅ crash | motor | motor | 836 sn |
| [Big plane crash](https://discuss.ardupilot.org/t/big-plane-crash/74142) | Plane | crash | ✅ crash | stall | - | 98 sn |
| [Need help to analyze log - sudden crash](https://discuss.ardupilot.org/t/need-help-to-analyze-log-sudden-crash/74509) | Copter | crash | ✅ crash | motor | motor | 98 sn |
| [Crashed drone due to unknown reasons!](https://discuss.ardupilot.org/t/crashed-drone-due-to-unknown-reasons/75213) | Copter | crash | ✅ crash | motor | control | 460 sn |
| [Help needed in determining cause of crash](https://discuss.ardupilot.org/t/help-needed-in-determining-cause-of-crash/75345) | Copter | crash | ✅ crash | motor | motor | 320 sn |
| [Loiter mode climb, drift and crash!](https://discuss.ardupilot.org/t/loiter-mode-climb-drift-and-crash/7594) | Copter | crash | ✅ crash | battery | - | 552 sn |
| [Octocopter multiple crash](https://discuss.ardupilot.org/t/octocopter-multiple-crash/76588) | Copter | crash | ✅ crash | motor | motor | 398 sn |
| [SITL crashes when used with X-plane 11](https://discuss.ardupilot.org/t/sitl-crashes-when-used-with-x-plane-11/77508) | Plane | crash | ✅ crash | control | - | 30 sn |
| [Copter flip on takeoff with fake static GPS](https://discuss.ardupilot.org/t/copter-flip-on-takeoff-with-fake-static-gps/78653) | Copter | crash | ✅ crash | motor | - | 45 sn |
| [Arducopter Crash](https://discuss.ardupilot.org/t/arducopter-crash/78702) | Copter | crash | ✅ crash | motor | motor | 285 sn |
| [Drone crash in loiter mode after GSF converged](https://discuss.ardupilot.org/t/drone-crash-in-loiter-mode-after-gsf-converged/79296) | Copter | crash | ✅ crash | motor | - | 703 sn |
| [Copter hard crash](https://discuss.ardupilot.org/t/copter-hard-crash/79351) | Copter | crash | ✅ crash | motor | motor | 14 sn |
| [Single copter crash log. Could someone analyze it for me?](https://discuss.ardupilot.org/t/single-copter-crash-log-could-someone-analyze-it-for-me/81825) | Copter | crash | ✅ crash | control | control | 34 sn |
| [4.0.7 Sudden crash](https://discuss.ardupilot.org/t/4-0-7-sudden-crash/82430) | Copter | crash | ✅ crash | motor | motor | 1099 sn |
| [[CRASH] Hexacopter suddenly crashed while auto](https://discuss.ardupilot.org/t/crash-hexacopter-suddenly-crashed-while-auto/83521) | Copter | crash | ✅ crash | motor | motor | 339 sn |
| [Sudden crash after takeoff](https://discuss.ardupilot.org/t/sudden-crash-after-takeoff/83626) | Copter | crash | ✅ crash | gps | motor | 558 sn |
| [Big Hex fatal crash](https://discuss.ardupilot.org/t/big-hex-fatal-crash/84027) | Copter | crash | ✅ crash | vibration | control | 700 sn |
| [Need help in finding the cause of a crash](https://discuss.ardupilot.org/t/need-help-in-finding-the-cause-of-a-crash/84217) | Copter | crash | ✅ crash | motor | control | 25 sn |
| [Why did my drone crash? please help in finding out](https://discuss.ardupilot.org/t/why-did-my-drone-crash-please-help-in-finding-out/84274) | Copter | crash | ✅ crash | control | control | 452 sn |
| [Oscillate and flip over after switching FC](https://discuss.ardupilot.org/t/oscillate-and-flip-over-after-switching-fc/85751) | Copter | crash | ✅ crash | motor | control | 16 sn |
| [Drone crash on RTL on descend, drone started to tumble (Hobbywing X6 O](https://discuss.ardupilot.org/t/drone-crash-on-rtl-on-descend-drone-started-to-tumble-hobbywing-x6-octo-please-help-to-analyze-log/86761) | Copter | crash | ✅ crash | gps | motor | 390 sn |
| [Need help looking over a log, had an unexpected crash?](https://discuss.ardupilot.org/t/need-help-looking-over-a-log-had-an-unexpected-crash/87171) | Plane | crash | ✅ crash | control | - | 1041 sn |
| [Big Hexacopter Crash after take off](https://discuss.ardupilot.org/t/big-hexacopter-crash-after-take-off/87523) | Copter | crash | ✅ crash | vibration | control | 34 sn |
| [Crash, need help please](https://discuss.ardupilot.org/t/crash-need-help-please/88407) | Copter | crash | ✅ crash | motor | motor | 1262 sn |
| [Hexa Crash During Loiter Test](https://discuss.ardupilot.org/t/hexa-crash-during-loiter-test/88767) | Copter | crash | ✅ crash | motor | battery | 96 sn |
| [Crash at takeoff investigation help](https://discuss.ardupilot.org/t/crash-at-takeoff-investigation-help/89417) | Copter | crash | ✅ crash | vibration | motor | 16 sn |
| [Xuav Talon Crash](https://discuss.ardupilot.org/t/xuav-talon-crash/89643) | Plane | crash | ✅ crash | control | stall | 1082 sn |
| [Help needed to understand crash log please](https://discuss.ardupilot.org/t/help-needed-to-understand-crash-log-please/90207) | Copter | crash | ✅ crash | vibration | vibration | 138 sn |
| [Hexacopter Crash during takeoff Loiter MODE](https://discuss.ardupilot.org/t/hexacopter-crash-during-takeoff-loiter-mode/90253) | Copter | crash | ✅ crash | motor | control | 33 sn |
| [RCin and RCout freezes (becomes flat line) during flight leading to cr](https://discuss.ardupilot.org/t/rcin-and-rcout-freezes-becomes-flat-line-during-flight-leading-to-crash/90287) | Copter | crash | ✅ crash | control | - | 1377 sn |
| [Crash after simple tuning changes](https://discuss.ardupilot.org/t/crash-after-simple-tuning-changes/91618) | Copter | crash | ✅ crash | motor | control | 1446 sn |
| [Oscillation in Roll and Pitch Resulting in Crash](https://discuss.ardupilot.org/t/oscillation-in-roll-and-pitch-resulting-in-crash/93512) | Copter | crash | ✅ crash | control | motor | 1484 sn |
| [In-Flight Crash Investigation](https://discuss.ardupilot.org/t/in-flight-crash-investigation/94084) | Plane | crash | ✅ crash | control | control | 72 sn |
| [Crash Log File Assistance](https://discuss.ardupilot.org/t/crash-log-file-assistance/96429) | Copter | crash | ✅ crash | motor | motor | 117 sn |
| [Quadrotor crashed caused by rangefinder and motor readings based on da](https://discuss.ardupilot.org/t/quadrotor-crashed-caused-by-rangefinder-and-motor-readings-based-on-datalog-analysis-in-mission-planner/96442) | Copter | crash | ✅ crash | motor | motor | 85 sn |
| [Copter 4.3.4 crashed while gaining altitude](https://discuss.ardupilot.org/t/copter-4-3-4-crashed-while-gaining-altitude/97736) | Copter | crash | ✅ crash | gps | - | 539 sn |
| [Octocopter Crash, Dev 4.4, strange ration in yaw during autotune](https://discuss.ardupilot.org/t/octocopter-crash-dev-4-4-strange-ration-in-yaw-during-autotune/98267) | Copter | crash | ✅ crash | motor | - | 217 sn |
| [Aggressive flight and Crash: Alt hold mode](https://discuss.ardupilot.org/t/aggressive-flight-and-crash-alt-hold-mode/98640) | Copter | crash | ✅ crash | motor | control | 208 sn |
| [Plane crashed during RTL](https://discuss.ardupilot.org/t/plane-crashed-during-rtl/98734) | Plane | crash | ✅ crash | control | stall | 2534 sn |
| [Vicious Crash Log 12S X Class](https://discuss.ardupilot.org/t/vicious-crash-log-12s-x-class/98768) | Copter | crash | ✅ crash | motor | motor | 70 sn |
| [12S Violent Crash with X-Class](https://discuss.ardupilot.org/t/12s-violent-crash-with-x-class/98794) | Copter | crash | ✅ crash | motor | motor | 70 sn |
| [Drone with Custom made Cage went flying until it crashed](https://discuss.ardupilot.org/t/drone-with-custom-made-cage-went-flying-until-it-crashed/98940) | Copter | crash | ✅ crash | motor | - | 303 sn |
| [VTOL Tilt-Rotor crash](https://discuss.ardupilot.org/t/vtol-tilt-rotor-crash/99829) | Plane | crash | ✅ crash | motor | - | 336 sn |
| [Quadcopter Crash Log Analysis Request](https://discuss.ardupilot.org/t/quadcopter-crash-log-analysis-request/99897) | Copter | crash | ✅ crash | motor | motor | 20 sn |
| [Fighter VTOL crash while landing - possible reasons](https://discuss.ardupilot.org/t/fighter-vtol-crash-while-landing-possible-reasons/99924) | Plane | crash | ✅ crash | motor | motor | 1220 sn |
| [Tailless VTOL crash log](https://discuss.ardupilot.org/t/tailless-vtol-crash-log/99978) | Plane | crash | ✅ crash | compass | control | 17 sn |
| [Copter: improve flip so it does not lose altitude](https://github.com/ArduPilot/ardupilot/issues/13811) | Copter | crash | ✅ crash | motor | - | 134 sn |
| [Fail to maintain attitude during Flip mode](https://github.com/ArduPilot/ardupilot/issues/14446) | Copter | crash | ✅ crash | control | - | 78 sn |
| [Arducopter 4.0.4 on Omnibus F4Pro Crash after cancelling from RTL Mode](https://github.com/ArduPilot/ardupilot/issues/15519) | Copter | crash | ✅ crash | control | - | 809 sn |
| [EKF failsafe untriggered on high errors, resulting in a crash #6](https://github.com/ArduPilot/ardupilot/issues/24374) | Copter | crash | ✅ crash | control | - | 509 sn |
| [RTL to QRTL transition caused spin and crash](https://github.com/ArduPilot/ardupilot/issues/25356) | Plane | crash | ✅ crash | motor | control | 771 sn |
| [[Arducopter ] Crash Detection during Flight](https://github.com/ArduPilot/ardupilot/issues/7039) | Copter | crash | ✅ crash | unknown | - | 263 sn |
| [Hexarotor: Crashed in Althold mode with GPS glitch (firmware: Copter 3](https://github.com/ArduPilot/ardupilot/issues/8203) | Copter | crash | ✅ crash | motor | gps | 1800 sn |
| [Quadrotor Crash upon Entering AltHold](https://discuss.ardupilot.org/t/quadrotor-crash-upon-entering-althold/10008) | Copter | crash | ✅ incident | control | - | 257 sn |
| [QUAD slowly descends having no control and crashes three times](https://discuss.ardupilot.org/t/quad-slowly-descends-having-no-control-and-crashes-three-times/10012) | Copter | crash | ✅ incident | power | motor | 484735 sn |
| [VTOL Crash -Quadplane setup](https://discuss.ardupilot.org/t/vtol-crash-quadplane-setup/100406) | Plane | crash | ✅ incident | control | motor | 406 sn |
| [Crash Could use some assistance](https://discuss.ardupilot.org/t/crash-could-use-some-assistance/10085) | Copter | crash | ❌ incident | unknown | - | 234350 sn |
| [Need help in identifying the cause of my copter crash in Loiter mode](https://discuss.ardupilot.org/t/need-help-in-identifying-the-cause-of-my-copter-crash-in-loiter-mode/100868) | Copter | crash | ✅ incident | motor | motor | 70 sn |
| [Log Analysis of Crash(Almost)](https://discuss.ardupilot.org/t/log-analysis-of-crash-almost/101181) | Copter | crash | ❌ incident | gps | vibration | 2621 sn |
| [And it was fly so nice...until it dropped out of the sky](https://discuss.ardupilot.org/t/and-it-was-fly-so-nice-until-it-dropped-out-of-the-sky/102361) | Copter | crash | ✅ incident | motor | motor | 266 sn |
| [Ardupilot Quad-plane unexpected crash](https://discuss.ardupilot.org/t/ardupilot-quad-plane-unexpected-crash/102402) | Plane | crash | ✅ incident | control | control | 23 sn |
| [Ublox F9P dual GPS RTK moving baseline problem](https://discuss.ardupilot.org/t/ublox-f9p-dual-gps-rtk-moving-baseline-problem/102616) | Plane | crash | ❌ incident | unknown | gps | 320 sn |
| [Crash due to signal disconnected between Transmitter and Receiver & Fa](https://discuss.ardupilot.org/t/crash-due-to-signal-disconnected-between-transmitter-and-receiver-failsafe-error-ekf/102748) | Copter | crash | ✅ incident | pilot | pilot | 92 sn |
| [Crash on takeoff, help with analysis? bin attached](https://discuss.ardupilot.org/t/crash-on-takeoff-help-with-analysis-bin-attached/102892) | Plane | crash | ✅ incident | control | stall | 114 sn |
| [Help with Drone Crash in High-Altitude Plateau](https://discuss.ardupilot.org/t/help-with-drone-crash-in-high-altitude-plateau/103096) | Copter | crash | ❌ incident | unknown | control | 161 sn |
| [Unresponsive quad crashed](https://discuss.ardupilot.org/t/unresponsive-quad-crashed/103644) | Copter | crash | ✅ incident | pilot | pilot | 169 sn |
| [Thrust Loss Check Error During Autotune](https://discuss.ardupilot.org/t/thrust-loss-check-error-during-autotune/104200) | Copter | crash | ✅ incident | control | motor | 229 sn |
| [Crash due to Err:GPS and Err: EKFCHECK-0](https://discuss.ardupilot.org/t/crash-due-to-err-gps-and-err-ekfcheck-0/104689) | Copter | crash | ✅ incident | gps | motor | 142 sn |
| [F35B Quadplane Test-Frame Crash](https://discuss.ardupilot.org/t/f35b-quadplane-test-frame-crash/107532) | Plane | crash | ✅ incident | control | - | 37 sn |
| [Copter crash today / can't run LogAnalyser due to "runner.exe stopped"](https://discuss.ardupilot.org/t/copter-crash-today-cant-run-loganalyser-due-to-runner-exe-stopped-help-to-understand-issue-appreciate/10843) | Copter | crash | ✅ incident | motor | - | 36 sn |
| [QuadCpter/ Crash today / climb up (loiter) till battery run out](https://discuss.ardupilot.org/t/quadcpter-crash-today-climb-up-loiter-till-battery-run-out/10846) | Copter | crash | ✅ incident | motor | - | 36 sn |
| [Throttle Failsafe. Why it happend? Could anyone teach me?](https://discuss.ardupilot.org/t/throttle-failsafe-why-it-happend-could-anyone-teach-me/108827) | Plane | crash | ✅ incident | control | radio | 341 sn |
| [Drone crash help](https://discuss.ardupilot.org/t/drone-crash-help/109349) | Copter | crash | ✅ incident | motor | motor | 173 sn |
| [Large hex crash, been working perfectly on 3.4rc1 and rc2?](https://discuss.ardupilot.org/t/large-hex-crash-been-working-perfectly-on-3-4rc1-and-rc2/11101) | Copter | crash | ✅ incident | motor | - | 20 sn |
| [Wild ride after successful Auto-tune](https://discuss.ardupilot.org/t/wild-ride-after-successful-auto-tune/113718) | Copter | crash | ✅ incident | control | control | 1008 sn |
| [Battery failsafe crash from "Land" function [solved]](https://discuss.ardupilot.org/t/battery-failsafe-crash-from-land-function-solved/113798) | Copter | crash | ❌ incident | battery | ekf | 149 sn |
| [Crashed Skywalker Arduplane 3.40 when switched to RTL while the plane ](https://discuss.ardupilot.org/t/crashed-skywalker-arduplane-3-40-when-switched-to-rtl-while-the-plane-was-in-guided-mode-go-to-here/11414) | Plane | crash | ✅ incident | control | - | 1087 sn |
| [Crash Pixhawk Arducopter 3.3.3 Help](https://discuss.ardupilot.org/t/crash-pixhawk-arducopter-3-3-3-help/11448) | Copter | crash | ✅ incident | power | vibration | 495898 sn |
| [Lost control doing traveling Piro](https://discuss.ardupilot.org/t/lost-control-doing-traveling-piro/114623) | Copter | crash | ✅ incident | motor | compass | 205 sn |
| [Sudden flip of 20kg tiltrotor quadcopter](https://discuss.ardupilot.org/t/sudden-flip-of-20kg-tiltrotor-quadcopter/114819) | Plane | crash | ✅ incident | control | motor | 529 sn |
| [Quadcopter flips over on takeoff. All usual suspects checked. SOLVED](https://discuss.ardupilot.org/t/quadcopter-flips-over-on-takeoff-all-usual-suspects-checked-solved/116156) | Copter | crash | ✅ incident | control | control | 3320 sn |
| [First flight and first crash](https://discuss.ardupilot.org/t/first-flight-and-first-crash/116295) | Plane | crash | ✅ incident | control | control | 424 sn |
| [Crash analysis, probable power loss](https://discuss.ardupilot.org/t/crash-analysis-probable-power-loss/118356) | Copter | crash | ✅ incident | power | power | 596 sn |
| [Copter unexpected rapid climb after arming~eventually crashed](https://discuss.ardupilot.org/t/copter-unexpected-rapid-climb-after-arming-eventually-crashed/119799) | Copter | crash | ✅ incident | power | ekf | 19 sn |
| [Copter crashed need help to find the reason](https://discuss.ardupilot.org/t/copter-crashed-need-help-to-find-the-reason/120700) | Copter | crash | ✅ incident | power | battery | 68 sn |
| [Please help analyse a crash log](https://discuss.ardupilot.org/t/please-help-analyse-a-crash-log/121455) | Plane | crash | ✅ incident | power | control | 694 sn |
| [Autotune makes plane far less responsive](https://discuss.ardupilot.org/t/autotune-makes-plane-far-less-responsive/122215) | Plane | crash | ✅ incident | control | stall | 116 sn |
| [High speed crash on maiden flight--design flaw or bad settings?](https://discuss.ardupilot.org/t/high-speed-crash-on-maiden-flight-design-flaw-or-bad-settings/122289) | Plane | crash | ✅ incident | control | control | 54 sn |
| [Copter 3.4.1 - crash because of battery failsafe](https://discuss.ardupilot.org/t/copter-3-4-1-crash-because-of-battery-failsafe/12628) | Copter | crash | ✅ incident | power | battery | 185 sn |
| [AUTOTUNE crash and strange logs](https://discuss.ardupilot.org/t/autotune-crash-and-strange-logs/12677) | Plane | crash | ✅ incident | stall | - | 261 sn |
| [Unexpected Quadcopter Crash in RTL Mode](https://discuss.ardupilot.org/t/unexpected-quadcopter-crash-in-rtl-mode/126969) | Copter | crash | ✅ incident | motor | motor | 1008 sn |
| [Diagnose Pixhawk crash log](https://discuss.ardupilot.org/t/diagnose-pixhawk-crash-log/12788) | Copter | crash | ✅ incident | power | - | 87 sn |
| [Quadcopter crash](https://discuss.ardupilot.org/t/quadcopter-crash/128037) | Copter | crash | ✅ incident | control | - | 186 sn |
| [Drone crash suddenly after a stable flight](https://discuss.ardupilot.org/t/drone-crash-suddenly-after-a-stable-flight/129529) | Copter | crash | ✅ incident | motor | motor | 97 sn |
| [Yaw Instability and Crash in Loiter Mode – High Vibrations & Motor Imb](https://discuss.ardupilot.org/t/yaw-instability-and-crash-in-loiter-mode-high-vibrations-motor-imbalance-issues/130060) | Copter | crash | ✅ incident | motor | motor | 97 sn |
| [Odd crash today - multiple ERR:24-0 and ERR:24-1 messages?](https://discuss.ardupilot.org/t/odd-crash-today-multiple-err-24-0-and-err-24-1-messages/13324) | Copter | crash | ✅ incident | motor | ekf | 201 sn |
| [Help on log analisys, Helicopter crashed](https://discuss.ardupilot.org/t/help-on-log-analisys-helicopter-crashed/133637) | Copter | crash | ✅ incident | motor | control | 27 sn |
| [Crash avoided, MAG0 GROUND MAG ANOMALY, YAW-REALIGNED](https://discuss.ardupilot.org/t/crash-avoided-mag0-ground-mag-anomaly-yaw-realigned/134335) | Copter | crash | ❌ incident | compass | compass | 2807 sn |
| [Which made the mini heli crash](https://discuss.ardupilot.org/t/which-made-the-mini-heli-crash/13479) | Copter | crash | ✅ incident | control | pilot | 428 sn |
| [Arduplane 4.5.7 TAKEOFF crash investigation](https://discuss.ardupilot.org/t/arduplane-4-5-7-takeoff-crash-investigation/135053) | Plane | crash | ✅ incident | compass | - | 188 sn |
| [Crash during auto takeoff v4.6.0 with video](https://discuss.ardupilot.org/t/crash-during-auto-takeoff-v4-6-0-with-video/136852) | Plane | crash | ✅ incident | control | control | 152 sn |
| [Clarify need to rectify Drone Crash](https://discuss.ardupilot.org/t/clarify-need-to-rectify-drone-crash/137712) | Copter | crash | ✅ incident | vibration | control | 1336 sn |
| [Newbie trying Crash Analysis on Vtol Project](https://discuss.ardupilot.org/t/newbie-trying-crash-analysis-on-vtol-project/137901) | Plane | crash | ✅ incident | control | compass | 258 sn |
| [VTOL crash after transition to FBWA](https://discuss.ardupilot.org/t/vtol-crash-after-transition-to-fbwa/138484) | Plane | crash | ✅ incident | control | - | 108 sn |
| [QLOITER hover instability/crash after high Q_A_ANG_PIT_P/RLL_P=9 (15 k](https://discuss.ardupilot.org/t/qloiter-hover-instability-crash-after-high-q-a-ang-pit-p-rll-p-9-15-kg-vtol-22x7-4-rate-r-170-rdes-90/138573) | Plane | crash | ✅ incident | control | control | 354 sn |
| [About PID Tuning, QuickTune, and QAUTOTUNE for Large (13–19 kg) VTOL A](https://discuss.ardupilot.org/t/about-pid-tuning-quicktune-and-qautotune-for-large-13-19-kg-vtol-aircraft/138733) | Plane | crash | ✅ incident | control | control | 354 sn |
| [Copter 4.6.2 Crashed after Takeoff](https://discuss.ardupilot.org/t/copter-4-6-2-crashed-after-takeoff/141037) | Copter | crash | ✅ incident | control | control | 64 sn |
| [After EKF failsafe, the drone just fell from 80 m](https://discuss.ardupilot.org/t/after-ekf-failsafe-the-drone-just-fell-from-80-m/141345) | Copter | crash | ✅ incident | power | gps | 342 sn |
| [Drone Crashed After Switching to LOITER Mode (Stable in AUTO Mode)](https://discuss.ardupilot.org/t/drone-crashed-after-switching-to-loiter-mode-stable-in-auto-mode/141421) | Copter | crash | ❌ incident | unknown | gps | 161 sn |
| [The drone suddenly crashed](https://discuss.ardupilot.org/t/the-drone-suddenly-crashed/141765) | Copter | crash | ❌ incident | motor | motor | 198 sn |
| [Quadplane nearly crashed after the transition](https://discuss.ardupilot.org/t/quadplane-nearly-crashed-after-the-transition/142096) | Plane | crash | ✅ incident | vibration | control | 813 sn |
| [4+1 VTOL Crash analysis in Q mode (VTOL motors quit)](https://discuss.ardupilot.org/t/4-1-vtol-crash-analysis-in-q-mode-vtol-motors-quit/142142) | Plane | crash | ❌ incident | unknown | motor | 554 sn |
| [10inch Drone Crash / Drone falls on RTL](https://discuss.ardupilot.org/t/10inch-drone-crash-drone-falls-on-rtl/142346) | Copter | crash | ✅ incident | motor | motor | 59 sn |
| [ArduPlane 4.6.3 TAKEOFF mode: climbs ~8 m then nose-down and crash (At](https://discuss.ardupilot.org/t/arduplane-4-6-3-takeoff-mode-climbs-8-m-then-nose-down-and-crash-atomrc-swordfish-v-tail/142491) | Plane | crash | ✅ incident | control | control | 63 sn |
| [Crash Log Analysis - Shutdown during hover](https://discuss.ardupilot.org/t/crash-log-analysis-shutdown-during-hover/142695) | Copter | crash | ✅ incident | control | - | 998 sn |
| [Log analysis Crashed!](https://discuss.ardupilot.org/t/log-analysis-crashed/142836) | Copter | crash | ✅ incident | power | power | 1618 sn |
| [APM quadcopter sudden crash](https://discuss.ardupilot.org/t/apm-quadcopter-sudden-crash/143010) | Copter | crash | ✅ incident | unknown | - | 44752 sn |
| [TAKEOFF mode : after few seconds pitch down and crash](https://discuss.ardupilot.org/t/takeoff-mode-after-few-seconds-pitch-down-and-crash/143223) | Plane | crash | ✅ incident | control | control | 92 sn |
| [Crash Analysis Request: Hexa-X / Cube Orange+ / 28" Props / ArduCopter](https://discuss.ardupilot.org/t/crash-analysis-request-hexa-x-cube-orange-28-props-arducopter-4-6-2/143577) | Copter | crash | ✅ incident | motor | motor | 830 sn |
| [Plane crash on auto takeoff due to battery failsafe autoland(?)](https://discuss.ardupilot.org/t/plane-crash-on-auto-takeoff-due-to-battery-failsafe-autoland/143625) | Plane | crash | ✅ incident | control | control | 18 sn |
| [Fixedwing VTOL UAV Crash Review](https://discuss.ardupilot.org/t/fixedwing-vtol-uav-crash-review/143642) | Plane | crash | ✅ incident | control | control | 1489 sn |
| [What was the crash cause?](https://discuss.ardupilot.org/t/what-was-the-crash-cause/143696) | Plane | crash | ✅ incident | stall | control | 621 sn |
| [Fixed wing catapult crash](https://discuss.ardupilot.org/t/fixed-wing-catapult-crash/143710) | Plane | crash | ✅ incident | compass | - | 57 sn |
| [ArduPlane 4.7.0 beta 4 VTOL attitude problem](https://discuss.ardupilot.org/t/arduplane-4-7-0-beta-4-vtol-attitude-problem/144037) | Plane | crash | ✅ incident | power | control | 482 sn |
| [Strange control oscilation causing a crash](https://discuss.ardupilot.org/t/strange-control-oscilation-causing-a-crash/144150) | Copter | crash | ✅ incident | control | vibration | 502 sn |
| [Done flipped after switching from stabalize to ALT_HOLD](https://discuss.ardupilot.org/t/done-flipped-after-switching-from-stabalize-to-alt-hold/144420) | Copter | crash | ✅ incident | gps | power | 40 sn |
| [Range finders out of range values cause crash](https://discuss.ardupilot.org/t/range-finders-out-of-range-values-cause-crash/14474) | Copter | crash | ✅ incident | power | - | 660 sn |
| [Plane enters spiral/toilet-bowl loop during roll in AutoTune (Factory ](https://discuss.ardupilot.org/t/plane-enters-spiral-toilet-bowl-loop-during-roll-in-autotune-factory-pids/144973) | Plane | crash | ✅ incident | control | control | 600 sn |
| [Lost control on landing touch down](https://discuss.ardupilot.org/t/lost-control-on-landing-touch-down/145155) | Copter | crash | ✅ incident | control | ekf | 520 sn |
| [Watchdog after a flight with temporary loss of control. No crash, soft](https://discuss.ardupilot.org/t/watchdog-after-a-flight-with-temporary-loss-of-control-no-crash-soft-landing/145555) | Copter | crash | ✅ incident | control | - | 216 sn |
| [Identifying reason for crash](https://discuss.ardupilot.org/t/identifying-reason-for-crash/145881) | Copter | crash | ✅ incident | power | radio | 378 sn |
| [Y3 Tilt-Rotor VTOL Crashed 12 Seconds After Switching from QSTABILIZE ](https://discuss.ardupilot.org/t/y3-tilt-rotor-vtol-crashed-12-seconds-after-switching-from-qstabilize-to-fbwa-aileron-inputs-not-reflected-in-servo-outputs/146120) | Plane | crash | ✅ incident | control | control | 1719 sn |
| [Copter nearly crashed](https://discuss.ardupilot.org/t/copter-nearly-crashed/15074) | Copter | crash | ❌ incident | ekf | - | 295 sn |
| [Solo flyaway and crash during auto mission](https://discuss.ardupilot.org/t/solo-flyaway-and-crash-during-auto-mission/15265) | Copter | crash | ❌ incident | unknown | compass | 118784 sn |
| [Crash logs, RTL spiral into ground](https://discuss.ardupilot.org/t/crash-logs-rtl-spiral-into-ground/15863) | Plane | crash | ✅ incident | power | - | 489 sn |
| [Help w/ log analysis - copter flip/crash](https://discuss.ardupilot.org/t/help-w-log-analysis-copter-flip-crash/15940) | Copter | crash | ✅ incident | power | motor | 360 sn |
| [Quad constantly flips during takeoff, motors not spinning the same spe](https://discuss.ardupilot.org/t/quad-constantly-flips-during-takeoff-motors-not-spinning-the-same-speed/16617) | Copter | crash | ✅ incident | control | motor | 138 sn |
| [Pixracer accelerometer EKF_CHECK-2. Crash in POSHOLD autotune mode](https://discuss.ardupilot.org/t/pixracer-accelerometer-ekf-check-2-crash-in-poshold-autotune-mode/17875) | Copter | crash | ❌ incident | unknown | vibration | 95 sn |
| [Lost control and almost crash when return to Normal mode](https://discuss.ardupilot.org/t/lost-control-and-almost-crash-when-return-to-normal-mode/17906) | Plane | crash | ✅ incident | stall | - | 379 sn |
| [Quad Crashes after thrusting vertically up](https://discuss.ardupilot.org/t/quad-crashes-after-thrusting-vertically-up/18031) | Copter | crash | ✅ incident | vibration | vibration | 113 sn |
| [Testing RF Immunity - Crash Log - What fails?](https://discuss.ardupilot.org/t/testing-rf-immunity-crash-log-what-fails/18540) | Copter | crash | ✅ incident | power | motor | 273810 sn |
| [Hexa copter crash](https://discuss.ardupilot.org/t/hexa-copter-crash/20162) | Copter | crash | ✅ incident | vibration | battery | 109 sn |
| [Quadplane yaws left in hover](https://discuss.ardupilot.org/t/quadplane-yaws-left-in-hover/20896) | Plane | crash | ❌ incident | unknown | control | 157 sn |
| [Quadplane sudden Flip while in QHOVER](https://discuss.ardupilot.org/t/quadplane-sudden-flip-while-in-qhover/21768) | Plane | crash | ✅ incident | control | battery | 478 sn |
| [Crash after Autotune, Pixhawk](https://discuss.ardupilot.org/t/crash-after-autotune-pixhawk/21863) | Copter | crash | ✅ incident | vibration | vibration | 654 sn |
| [Nasty Crash - Quad Copter Fell of 10' hight into ground](https://discuss.ardupilot.org/t/nasty-crash-quad-copter-fell-of-10-hight-into-ground/22273) | Copter | crash | ❌ incident | unknown | power | 34 sn |
| [Hexacopter Tuning flips on lift off](https://discuss.ardupilot.org/t/hexacopter-tuning-flips-on-lift-off/22461) | Copter | crash | ❌ incident | unknown | control | 76 sn |
| [CRASH: Log Review Request](https://discuss.ardupilot.org/t/crash-log-review-request/23148) | Copter | crash | ✅ incident | power | power | 2023 sn |
| [Hexacopter crash](https://discuss.ardupilot.org/t/hexacopter-crash/23543) | Copter | crash | ✅ incident | power | radio | 431 sn |
| [Hexacopter drifting away = crash (log + video)](https://discuss.ardupilot.org/t/hexacopter-drifting-away-crash-log-video/26675) | Copter | crash | ✅ incident | motor | compass | 139 sn |
| [Crash after Autotune: could someone please take a look at the logfile?](https://discuss.ardupilot.org/t/crash-after-autotune-could-someone-please-take-a-look-at-the-logfile/29310) | Copter | crash | ✅ incident | motor | motor | 219 sn |
| [Pixhawk 4 - Copter about to flip forward - RC problem?](https://discuss.ardupilot.org/t/pixhawk-4-copter-about-to-flip-forward-rc-problem/31538) | Copter | crash | ❌ incident | unknown | motor | 122 sn |
| [Inconsistent compass error leads to crash when internal compasses swit](https://discuss.ardupilot.org/t/inconsistent-compass-error-leads-to-crash-when-internal-compasses-switched-off/32040) | Copter | crash | ✅ incident | vibration | compass | 32 sn |
| [Crashed mid flight in PosHold (just dropped)](https://discuss.ardupilot.org/t/crashed-mid-flight-in-poshold-just-dropped/32115) | Copter | crash | ✅ incident | motor | battery | 544 sn |
| [Qplane crash in Auto VTOL maneuvering](https://discuss.ardupilot.org/t/qplane-crash-in-auto-vtol-maneuvering/32183) | Plane | crash | ✅ incident | compass | control | 662 sn |
| [Rtl crash after converting to ppm and new power module](https://discuss.ardupilot.org/t/rtl-crash-after-converting-to-ppm-and-new-power-module/33361) | Copter | crash | ❌ incident | unknown | - | 59038 sn |
| [Log Crash Analysis Help](https://discuss.ardupilot.org/t/log-crash-analysis-help/37003) | Copter | crash | ✅ incident | power | motor | 424325 sn |
| [Uncontrolled position Problem in Auto mode and Cut motors in Qland](https://discuss.ardupilot.org/t/uncontrolled-position-problem-in-auto-mode-and-cut-motors-in-qland/37006) | Plane | crash | ✅ incident | control | - | 78 sn |
| [AC-copter 3.7-dev fell from the sky crash log](https://discuss.ardupilot.org/t/ac-copter-3-7-dev-fell-from-the-sky-crash-log/37800) | Copter | crash | ✅ incident | control | power | 175 sn |
| [Drone Drops After Hovering Fine for a Few Seconds (Log Analysis Help)](https://discuss.ardupilot.org/t/drone-drops-after-hovering-fine-for-a-few-seconds-log-analysis-help/39146) | Copter | crash | ✅ incident | compass | - | 28 sn |
| [Crash when change mode STABILIZE -> ALTHOLD](https://discuss.ardupilot.org/t/crash-when-change-mode-stabilize-althold/39428) | Copter | crash | ✅ incident | battery | motor | 66 sn |
| [Altitude snapped from baro to GPS alt - tried to crash](https://discuss.ardupilot.org/t/altitude-snapped-from-baro-to-gps-alt-tried-to-crash/39447) | Plane | crash | ✅ incident | stall | gps | 436 sn |
| [Terrible Crash - Strange Behavior in Copter 3.6.6](https://discuss.ardupilot.org/t/terrible-crash-strange-behavior-in-copter-3-6-6/39486) | Copter | crash | ✅ incident | vibration | vibration | 78 sn |
| [Help diagnosing errant behavior / crash for octocopter](https://discuss.ardupilot.org/t/help-diagnosing-errant-behavior-crash-for-octocopter/39580) | Copter | crash | ✅ incident | compass | battery | 41 sn |
| [In-flight yaw realignments causing large yaw errors and crashes](https://discuss.ardupilot.org/t/in-flight-yaw-realignments-causing-large-yaw-errors-and-crashes/39803) | Copter | crash | ❌ incident | compass | compass | 213 sn |
| [Plane 3.9 crash diagnostic](https://discuss.ardupilot.org/t/plane-3-9-crash-diagnostic/39836) | Plane | crash | ✅ incident | control | control | 50 sn |
| [Octa X crash in stabilize](https://discuss.ardupilot.org/t/octa-x-crash-in-stabilize/40563) | Copter | crash | ✅ incident | vibration | - | 2009 sn |
| [X8 almost Crashed trying to level](https://discuss.ardupilot.org/t/x8-almost-crashed-trying-to-level/41190) | Copter | crash | ✅ incident | control | control | 975 sn |
| [Nimbus VTOL LOGS PH 2.1](https://discuss.ardupilot.org/t/nimbus-vtol-logs-ph-2-1/41894) | Plane | crash | ✅ incident | stall | compass | 494 sn |
| [Omnibus F4 V3 loss of control and crash](https://discuss.ardupilot.org/t/omnibus-f4-v3-loss-of-control-and-crash/42534) | Copter | crash | ✅ incident | motor | radio | 42 sn |
| [Advice on log with crash on takeoff](https://discuss.ardupilot.org/t/advice-on-log-with-crash-on-takeoff/42843) | Plane | crash | ✅ incident | power | control | 1146 sn |
| [Fell/landed to a tree caused by unknown reason](https://discuss.ardupilot.org/t/fell-landed-to-a-tree-caused-by-unknown-reason/43318) | Copter | crash | ✅ incident | power | - | 367690 sn |
| [Unwanted yaw drift, caused crash, failed EKF velocity [ RESOLVED ]](https://discuss.ardupilot.org/t/unwanted-yaw-drift-caused-crash-failed-ekf-velocity-resolved/47471) | Copter | crash | ✅ incident | motor | vibration | 18 sn |
| [Crash after initial throw w/Autotune, Compass Learn](https://discuss.ardupilot.org/t/crash-after-initial-throw-w-autotune-compass-learn/48931) | Plane | crash | ✅ incident | control | - | 198 sn |
| [Crash with 4.0.0 RC3](https://discuss.ardupilot.org/t/crash-with-4-0-0-rc3/50267) | Copter | crash | ✅ incident | motor | battery | 59 sn |
| [Plane roll and crash at takeoff (auto)](https://discuss.ardupilot.org/t/plane-roll-and-crash-at-takeoff-auto/50364) | Plane | crash | ✅ incident | control | control | 760 sn |
| [Pixhawk Crash magically](https://discuss.ardupilot.org/t/pixhawk-crash-magically/50401) | Copter | crash | ✅ incident | motor | battery | 26 sn |
| [Compass variance errors and crash with Skywalker X8 Quadplane](https://discuss.ardupilot.org/t/compass-variance-errors-and-crash-with-skywalker-x8-quadplane/52335) | Plane | crash | ✅ incident | stall | compass | 225 sn |
| [Crashed on maiden flight](https://discuss.ardupilot.org/t/crashed-on-maiden-flight/53539) | Copter | crash | ❌ incident | control | - | 198 sn |
| [RTL flyaway, Bad POS (among others)](https://discuss.ardupilot.org/t/rtl-flyaway-bad-pos-among-others/53951) | Copter | crash | ✅ incident | motor | control | 89 sn |
| [Helicopter lost control in stabilize mode and crashed.Log attached](https://discuss.ardupilot.org/t/helicopter-lost-control-in-stabilize-mode-and-crashed-log-attached/54194) | Copter | crash | ✅ incident | motor | ekf | 690 sn |
| [Crash Log analysis and problem diagnosis (potential bug?)](https://discuss.ardupilot.org/t/crash-log-analysis-and-problem-diagnosis-potential-bug/5457) | Copter | crash | ✅ incident | power | - | 301851 sn |
| [Hexa garage hover crash has me losing sleep](https://discuss.ardupilot.org/t/hexa-garage-hover-crash-has-me-losing-sleep/5495) | Copter | crash | ✅ incident | power | radio | 510506 sn |
| [Autotune didn't go well](https://discuss.ardupilot.org/t/autotune-didnt-go-well/55094) | Copter | crash | ✅ incident | power | power | 23 sn |
| [Copter suddenly went out of control and crashed severely](https://discuss.ardupilot.org/t/copter-suddenly-went-out-of-control-and-crashed-severely/56145) | Copter | crash | ✅ incident | gps | ekf | 329 sn |
| [Sudden Fall Down and Crash (Attaching LOGS)](https://discuss.ardupilot.org/t/sudden-fall-down-and-crash-attaching-logs/57400) | Copter | crash | ✅ incident | power | power | 111 sn |
| [Free-fall then crash when flying in Guided Mode (logs attached)](https://discuss.ardupilot.org/t/free-fall-then-crash-when-flying-in-guided-mode-logs-attached/59255) | Copter | crash | ✅ incident | control | radio | 114 sn |
| [Copter fell out of the sky for no reason that I can find - twice!](https://discuss.ardupilot.org/t/copter-fell-out-of-the-sky-for-no-reason-that-i-can-find-twice/63350) | Copter | crash | ✅ incident | power | power | 15 sn |
| [AP 4.0.7 - software induced near crash during autotune flight](https://discuss.ardupilot.org/t/ap-4-0-7-software-induced-near-crash-during-autotune-flight/65423) | Plane | crash | ✅ incident | stall | radio | 361 sn |
| [Crash after land command with Arducopter](https://discuss.ardupilot.org/t/crash-after-land-command-with-arducopter/65445) | Copter | crash | ✅ incident | control | control | 70 sn |
| [Immediate crash after arming fresh quadcopter](https://discuss.ardupilot.org/t/immediate-crash-after-arming-fresh-quadcopter/65833) | Copter | crash | ❌ incident | unknown | pilot | 54 sn |
| [QuadPlane flips during transition](https://discuss.ardupilot.org/t/quadplane-flips-during-transition/65883) | Plane | crash | ✅ incident | control | control | 473 sn |
| [Crash on Auto Mode (Fixed Wing Plane)](https://discuss.ardupilot.org/t/crash-on-auto-mode-fixed-wing-plane/67111) | Plane | crash | ✅ incident | control | stall | 975 sn |
| [Instant pitch backward in stabilizing mode leading to crash](https://discuss.ardupilot.org/t/instant-pitch-backward-in-stabilizing-mode-leading-to-crash/67656) | Copter | crash | ✅ incident | control | - | 947 sn |
| [Unexpected crash after an autotune - loss of all control](https://discuss.ardupilot.org/t/unexpected-crash-after-an-autotune-loss-of-all-control/67713) | Copter | crash | ✅ incident | control | control | 100 sn |
| [RC IN channels ALL zeros -- followed by CRASH!](https://discuss.ardupilot.org/t/rc-in-channels-all-zeros-followed-by-crash/6812) | Copter | crash | ✅ incident | power | - | 411867 sn |
| [Plane crash during Auto TakeOff](https://discuss.ardupilot.org/t/plane-crash-during-auto-takeoff/68125) | Plane | crash | ✅ incident | control | control | 69 sn |
| [Copter in AltHold mode unwanted engine spin-up and crash](https://discuss.ardupilot.org/t/copter-in-althold-mode-unwanted-engine-spin-up-and-crash/68820) | Copter | crash | ✅ incident | control | ekf | 92 sn |
| [Quadcopter Crashed after flight of a minute](https://discuss.ardupilot.org/t/quadcopter-crashed-after-flight-of-a-minute/69639) | Copter | crash | ✅ incident | battery | pilot | 100 sn |
| [Crash - perfect, fast roll rotations to the ground on RTL](https://discuss.ardupilot.org/t/crash-perfect-fast-roll-rotations-to-the-ground-on-rtl/6984) | Copter | crash | ✅ incident | power | - | 247 sn |
| [VTOL crash analysis!](https://discuss.ardupilot.org/t/vtol-crash-analysis/69983) | Plane | crash | ✅ incident | battery | control | 147 sn |
| [Crash in mission - had just updated from 4.0.5 to 4.0.9](https://discuss.ardupilot.org/t/crash-in-mission-had-just-updated-from-4-0-5-to-4-0-9/70227) | Plane | crash | ✅ incident | control | radio | 537 sn |
| [Crash with Hexa - Pixhawk 4 - ArduCopter 4.0.3](https://discuss.ardupilot.org/t/crash-with-hexa-pixhawk-4-arducopter-4-0-3/72521) | Copter | crash | ✅ incident | vibration | motor | 68 sn |
| [Log analysis please, It suddenly overturned 180 degrees and crashed](https://discuss.ardupilot.org/t/log-analysis-please-it-suddenly-overturned-180-degrees-and-crashed/72851) | Copter | crash | ✅ incident | power | power | 104 sn |
| [MFE Fighter VTOL Crashed](https://discuss.ardupilot.org/t/mfe-fighter-vtol-crashed/76554) | Plane | crash | ✅ incident | vibration | - | 97 sn |
| [AR Wing Pro - RTL crash - LIM_ROLL_CD exeeded](https://discuss.ardupilot.org/t/ar-wing-pro-rtl-crash-lim-roll-cd-exeeded/77564) | Plane | crash | ✅ incident | stall | stall | 73 sn |
| [Plane crash in FBWA with standard PID values](https://discuss.ardupilot.org/t/plane-crash-in-fbwa-with-standard-pid-values/77884) | Plane | crash | ✅ incident | control | stall | 42 sn |
| [Unstable flight resulted in a crash - Copter 4.0.7](https://discuss.ardupilot.org/t/unstable-flight-resulted-in-a-crash-copter-4-0-7/78052) | Copter | crash | ✅ incident | motor | gps | 1096 sn |
| [Newbie 20 starts 20 crashed](https://discuss.ardupilot.org/t/newbie-20-starts-20-crashed/78844) | Plane | crash | ✅ incident | control | control | 212 sn |
| [X Quad 3.2.1 mid flight crash](https://discuss.ardupilot.org/t/x-quad-3-2-1-mid-flight-crash/8079) | Copter | crash | ✅ incident | power | power | 230928 sn |
| [Geofence breach RTL after landing = crash](https://discuss.ardupilot.org/t/geofence-breach-rtl-after-landing-crash/83084) | Plane | crash | ✅ incident | control | pilot | 332 sn |
| [Crash with 4.2.0-beta and 4.3.0-daily (bdshot)](https://discuss.ardupilot.org/t/crash-with-4-2-0-beta-and-4-3-0-daily-bdshot/83297) | Copter | crash | ✅ incident | power | power | 124 sn |
| [EKF changed to 1 in flight -> Almost crashed](https://discuss.ardupilot.org/t/ekf-changed-to-1-in-flight-almost-crashed/83360) | Copter | crash | ✅ incident | vibration | vibration | 485 sn |
| [Large change in mag_field, Copter crashes](https://discuss.ardupilot.org/t/large-change-in-mag-field-copter-crashes/83731) | Copter | crash | ✅ incident | motor | compass | 101 sn |
| [Erratic altitude in a downtown flight resulting in minor crash](https://discuss.ardupilot.org/t/erratic-altitude-in-a-downtown-flight-resulting-in-minor-crash/84460) | Copter | crash | ✅ incident | gps | gps | 1604 sn |
| [New Pilot: Can someone please help me understand my crash?](https://discuss.ardupilot.org/t/new-pilot-can-someone-please-help-me-understand-my-crash/85880) | Plane | crash | ✅ incident | compass | ekf | 104 sn |
| [FBWI Mode Takeoff Crashed due to Full Pitch [LOG UPLOADED]](https://discuss.ardupilot.org/t/fbwi-mode-takeoff-crashed-due-to-full-pitch-log-uploaded/88204) | Plane | crash | ✅ incident | stall | control | 64 sn |
| [Grounding issues](https://discuss.ardupilot.org/t/grounding-issues/88454) | Plane | crash | ✅ incident | unknown | motor | 167 sn |
| [Talon VTOL Conversion Crash](https://discuss.ardupilot.org/t/talon-vtol-conversion-crash/88953) | Plane | crash | ✅ incident | control | - | 449 sn |
| [X8 Fly Away... Looking for help analyzing log](https://discuss.ardupilot.org/t/x8-fly-away-looking-for-help-analyzing-log/9001) | Copter | crash | ✅ incident | power | vibration | 39 sn |
| [Crash 16.5kg AUW VTOL](https://discuss.ardupilot.org/t/crash-16-5kg-auw-vtol/90145) | Plane | crash | ✅ incident | control | motor | 560 sn |
| [Crash while hovering in QHOVER mode](https://discuss.ardupilot.org/t/crash-while-hovering-in-qhover-mode/90448) | Plane | crash | ✅ incident | control | - | 75 sn |
| [[Crash] Compass problem](https://discuss.ardupilot.org/t/crash-compass-problem/90547) | Copter | crash | ✅ incident | vibration | control | 95 sn |
| [Wing did a flip and crashed](https://discuss.ardupilot.org/t/wing-did-a-flip-and-crashed/90646) | Plane | crash | ✅ incident | control | control | 463 sn |
| ["EKF Lane Switch 1" and then drone crashes](https://discuss.ardupilot.org/t/ekf-lane-switch-1-and-then-drone-crashes/92394) | Copter | crash | ✅ incident | motor | vibration | 451 sn |
| [Copter crashed with, EKF primary changed:0 EKF primary changed:2 - dea](https://discuss.ardupilot.org/t/copter-crashed-with-ekf-primary-changed-0-ekf-primary-changed-2-deadly-crash/92858) | Copter | crash | ✅ incident | power | vibration | 1034 sn |
| [GPS Compass glitch EKF Lane Switch fly away help](https://discuss.ardupilot.org/t/gps-compass-glitch-ekf-lane-switch-fly-away-help/94323) | Copter | crash | ❌ incident | vibration | vibration | 161 sn |
| [Crash Motor test help please](https://discuss.ardupilot.org/t/crash-motor-test-help-please/94936) | Copter | crash | ✅ incident | control | power | 184 sn |
| [Large X8 disarm/power/logging loss in flight causing crash - Onboard l](https://discuss.ardupilot.org/t/large-x8-disarm-power-logging-loss-in-flight-causing-crash-onboard-log/97192) | Copter | crash | ✅ incident | power | power | 96 sn |
| [Vtol crash due to throttle disarm in mid flight](https://discuss.ardupilot.org/t/vtol-crash-due-to-throttle-disarm-in-mid-flight/97340) | Plane | crash | ✅ incident | pilot | pilot | 1252 sn |
| [Quadplane crashed after EKF3 Lane Switched 2!](https://discuss.ardupilot.org/t/quadplane-crashed-after-ekf3-lane-switched-2/97848) | Plane | crash | ✅ incident | control | motor | 220 sn |
| [VTOL plane crash during hover tuning](https://discuss.ardupilot.org/t/vtol-plane-crash-during-hover-tuning/97877) | Plane | crash | ✅ incident | control | motor | 65 sn |
| [APM mid flight crash](https://discuss.ardupilot.org/t/apm-mid-flight-crash/9801) | Copter | crash | ✅ incident | power | - | 379486 sn |
| [Pixhawk Crash complete shut down](https://discuss.ardupilot.org/t/pixhawk-crash-complete-shut-down/9984) | Copter | crash | ✅ incident | power | battery | 455 sn |
| [Copter locks up in flight, motors stop, crashes vehicle w/ Pixhawk 2](https://github.com/ArduPilot/ardupilot/issues/11642) | Copter | crash | ✅ incident | power | - | 170 sn |
| [Lightware I2C Range Spikes with IR-LOCK (can cause crash)](https://github.com/ArduPilot/ardupilot/issues/15615) | Copter | crash | ❌ incident | unknown | - | 223 sn |
| [Quadplane/Tailsitter: Q_TRIM it creates integral accumulation problems](https://github.com/ArduPilot/ardupilot/issues/15777) | Plane | crash | ✅ incident | control | control | 647 sn |
| [OctaQuad VTOL massive pitch, roll, and yawing problems](https://discuss.ardupilot.org/t/octaquad-vtol-massive-pitch-roll-and-yawing-problems/105908) | Plane | crash | ❌ noflight | - | control | 232 sn |
| [Near Crash in QHover after GPS Loss](https://discuss.ardupilot.org/t/near-crash-in-qhover-after-gps-loss/107723) | Plane | crash | ❌ noflight | - | gps | 309 sn |
| [Fly Away Abnormal: MagX, MAgY, MagZ](https://discuss.ardupilot.org/t/fly-away-abnormal-magx-magy-magz/131585) | Copter | crash | ❌ noflight | - | compass | 458 sn |
| [Trad heli crashing on takeoff](https://discuss.ardupilot.org/t/trad-heli-crashing-on-takeoff/138795) | Copter | crash | ❌ noflight | - | control | 21 sn |
| [Copter-3.5.0-rc7 unexpected crash on ErleBrain](https://discuss.ardupilot.org/t/copter-3-5-0-rc7-unexpected-crash-on-erlebrain/18465) | Copter | crash | ❌ noflight | - | - | 31 sn |
| [Copter crashing while taking off in drone kit](https://discuss.ardupilot.org/t/copter-crashing-while-taking-off-in-drone-kit/95698) | Copter | crash | ❌ noflight | - | control | 15 sn |
| [Discrepancy in the Matek F765 log file after a crash](https://discuss.ardupilot.org/t/discrepancy-in-the-matek-f765-log-file-after-a-crash/97318) | Plane | crash | ❌ noflight | - | - | 56 sn |
| [Quadcopter with V5 CUAV meat crash on its mid fligth](https://discuss.ardupilot.org/t/quadcopter-with-v5-cuav-meat-crash-on-its-mid-fligth/103854) | Copter | crash | ❌ normal | - | control | 282 sn |
| [Agro drone trying to flip during takeoff](https://discuss.ardupilot.org/t/agro-drone-trying-to-flip-during-takeoff/105190) | Copter | crash | ❌ normal | - | - | 1738 sn |
| [EKF Yaw Reset Crash](https://discuss.ardupilot.org/t/ekf-yaw-reset-crash/107273) | Copter | crash | ❌ normal | - | compass | 69 sn |
| [Large 10KG payload Drone crash on take off! Please help](https://discuss.ardupilot.org/t/large-10kg-payload-drone-crash-on-take-off-please-help/11083) | Copter | crash | ❌ normal | - | - | 28 sn |
| [Cube did not respond after the crash](https://discuss.ardupilot.org/t/cube-did-not-respond-after-the-crash/113961) | Copter | crash | ❌ normal | - | - | 998 sn |
| [Unintentional flip after auto-takeoff at 80 m height - nothing damaged](https://discuss.ardupilot.org/t/unintentional-flip-after-auto-takeoff-at-80-m-height-nothing-damaged/114541) | Copter | crash | ❌ normal | - | ekf | 315 sn |
| [Octo Refused Loiter 3 times then crashed](https://discuss.ardupilot.org/t/octo-refused-loiter-3-times-then-crashed/11620) | Copter | crash | ❌ normal | - | compass | 155 sn |
| [PixHawk crashed while ground testing](https://discuss.ardupilot.org/t/pixhawk-crashed-while-ground-testing/11638) | Copter | crash | ❌ normal | - | - | 155 sn |
| [Vcc error reported - crash 3.4rc5](https://discuss.ardupilot.org/t/vcc-error-reported-crash-3-4rc5/11975) | Copter | crash | ❌ normal | - | - | 511 sn |
| [Crashed into a tree, what was the main root cause?](https://discuss.ardupilot.org/t/crashed-into-a-tree-what-was-the-main-root-cause/121433) | Copter | crash | ❌ normal | - | - | 1397 sn |
| [Potential thrust loss(1) while testing TF02 pro lidar and Crashed](https://discuss.ardupilot.org/t/potential-thrust-loss-1-while-testing-tf02-pro-lidar-and-crashed/123719) | Copter | crash | ❌ normal | - | motor | 1588 sn |
| [Crash / Quadcopter Turned Upside Down](https://discuss.ardupilot.org/t/crash-quadcopter-turned-upside-down/124154) | Copter | crash | ❌ normal | - | motor | 173 sn |
| [Crash logs analysis](https://discuss.ardupilot.org/t/crash-logs-analysis/12892) | Copter | crash | ❌ normal | - | - | 173 sn |
| [X Quad Tends to Flip During Takeoff in Stabilize Mode](https://discuss.ardupilot.org/t/x-quad-tends-to-flip-during-takeoff-in-stabilize-mode/131797) | Copter | crash | ❌ normal | - | - | 228 sn |
| [VTOL crash during RTL - ? power loss](https://discuss.ardupilot.org/t/vtol-crash-during-rtl-power-loss/137162) | Plane | crash | ❌ normal | - | power | 206 sn |
| [Quad crash (second time) 3.4.4-rc1](https://discuss.ardupilot.org/t/quad-crash-second-time-3-4-4-rc1/13745) | Copter | crash | ❌ normal | - | - | 147 sn |
| [Copter fall during Autotune](https://discuss.ardupilot.org/t/copter-fall-during-autotune/142220) | Copter | crash | ❌ normal | - | power | 1777 sn |
| [VTOL tiltrotor crash in QLOITER – sudden yaw spin, backward movement, ](https://discuss.ardupilot.org/t/vtol-tiltrotor-crash-in-qloiter-sudden-yaw-spin-backward-movement-and-nose-down-rotation/145787) | Plane | crash | ❌ normal | - | - | 946 sn |
| [PH2.1 + SBF GPS = uncontrolled flyaway](https://discuss.ardupilot.org/t/ph2-1-sbf-gps-uncontrolled-flyaway/15104) | Copter | crash | ❌ normal | - | compass | 124 sn |
| [Copter Crash. Very rapid attitude changes](https://discuss.ardupilot.org/t/copter-crash-very-rapid-attitude-changes/16205) | Plane | crash | ❌ normal | - | - | 431 sn |
| [Hexacopter/Pixhawk2.1 - Crash](https://discuss.ardupilot.org/t/hexacopter-pixhawk2-1-crash/16756) | Copter | crash | ❌ normal | - | motor | 201 sn |
| [Copter Falls From Sky after Mission Start Action Excuted](https://discuss.ardupilot.org/t/copter-falls-from-sky-after-mission-start-action-excuted/20552) | Copter | crash | ❌ normal | - | - | 13 sn |
| [Skipping invalid cmd; No mission; AUTO mode enabled -> Possible crash](https://discuss.ardupilot.org/t/skipping-invalid-cmd-no-mission-auto-mode-enabled-possible-crash/28270) | Copter | crash | ❌ normal | - | - | 843 sn |
| [Loss of control after transition to forward flight [Solved]](https://discuss.ardupilot.org/t/loss-of-control-after-transition-to-forward-flight-solved/31535) | Plane | crash | ❌ normal | - | stall | 173 sn |
| [Possibly a fly away, please take a look at the log](https://discuss.ardupilot.org/t/possibly-a-fly-away-please-take-a-look-at-the-log/41183) | Copter | crash | ❌ normal | - | pilot | 1195 sn |
| [Loss of altitude and crash when engaging LOITER](https://discuss.ardupilot.org/t/loss-of-altitude-and-crash-when-engaging-loiter/44042) | Copter | crash | ❌ normal | - | - | 58 sn |
| [Attitude Oscillations Cause Crash for Large X8 in Autotune](https://discuss.ardupilot.org/t/attitude-oscillations-cause-crash-for-large-x8-in-autotune/45353) | Copter | crash | ❌ normal | - | control | 358 sn |
| [Alt_ Hold OCTA crashed, Am I right? I am not sure](https://discuss.ardupilot.org/t/alt-hold-octa-crashed-am-i-right-i-am-not-sure/50006) | Copter | crash | ❌ normal | - | motor | 284 sn |
| [Copter-3.6.12 Wants to fly away after a few seconds](https://discuss.ardupilot.org/t/copter-3-6-12-wants-to-fly-away-after-a-few-seconds/50593) | Copter | crash | ❌ normal | - | control | 29 sn |
| [Crash when mode Change on copter-4.0.3](https://discuss.ardupilot.org/t/crash-when-mode-change-on-copter-4-0-3/54090) | Copter | crash | ❌ normal | - | - | 69 sn |
| [Stable hover but wobbles and falls on large inputs](https://discuss.ardupilot.org/t/stable-hover-but-wobbles-and-falls-on-large-inputs/55405) | Copter | crash | ❌ normal | - | control | 407 sn |
| [32" oscillations and crash in Loiter just after take off](https://discuss.ardupilot.org/t/32-oscillations-and-crash-in-loiter-just-after-take-off/58933) | Copter | crash | ❌ normal | - | vibration | 34 sn |
| [Copter Flip over when mission engage auto take off](https://discuss.ardupilot.org/t/copter-flip-over-when-mission-engage-auto-take-off/61814) | Copter | crash | ❌ normal | - | control | 20 sn |
| [Bicopter tilt issues](https://discuss.ardupilot.org/t/bicopter-tilt-issues/65290) | Plane | crash | ❌ normal | - | control | 118 sn |
| [Crash multirotor in land mission!](https://discuss.ardupilot.org/t/crash-multirotor-in-land-mission/68887) | Copter | crash | ❌ normal | - | vibration | 649 sn |
| [Quad Flyaway - need analysis](https://discuss.ardupilot.org/t/quad-flyaway-need-analysis/69210) | Copter | crash | ❌ normal | - | control | 106 sn |
| [Drone crashed - sudden rise in YAW during flying and crash landed](https://discuss.ardupilot.org/t/drone-crashed-sudden-rise-in-yaw-during-flying-and-crash-landed/76391) | Copter | crash | ❌ normal | - | motor | 657 sn |
| [Flyaway (indoor !) need help to analyze log](https://discuss.ardupilot.org/t/flyaway-indoor-need-help-to-analyze-log/81234) | Copter | crash | ❌ normal | - | ekf | 51 sn |
| [VTOL Unstable & crashed in Qstablized mode](https://discuss.ardupilot.org/t/vtol-unstable-crashed-in-qstablized-mode/82934) | Plane | crash | ❌ normal | - | control | 285 sn |
| [Arducopter Crash, motor suddenly stop when tuning PID](https://discuss.ardupilot.org/t/arducopter-crash-motor-suddenly-stop-when-tuning-pid/91325) | Copter | crash | ❌ normal | - | motor | 670 sn |
| [3DR Iris + Crashed after 3 successful waypoints mission](https://discuss.ardupilot.org/t/3dr-iris-crashed-after-3-successful-waypoints-mission/9269) | Copter | crash | ❌ normal | - | motor | 329868 sn |
| [Quadcopter Fly Away on second flight of the day](https://discuss.ardupilot.org/t/quadcopter-fly-away-on-second-flight-of-the-day/94668) | Copter | crash | ❌ normal | - | vibration | 531 sn |
| [ Use of "MOT_SLEW_UP_TIME" leads to bad attitude and crash.](https://github.com/ArduPilot/ardupilot/issues/13739) | Copter | crash | ❌ normal | - | control | 204 sn |
| [Auto & Loiter Mode always Losing Altitude - Log Attached](https://discuss.ardupilot.org/t/auto-loiter-mode-always-losing-altitude-log-attached/7535) | Plane | normal | ❌ crash | control | - | 906 sn |
| [Help with Log Analysis, Copter "stumbling"](https://discuss.ardupilot.org/t/help-with-log-analysis-copter-stumbling/82334) | Copter | normal | ❌ crash | motor | - | 250 sn |
| [Accelerometer Loss During Takeoff Causes Crash](https://github.com/ArduPilot/ardupilot/issues/16021) | Copter | normal | ❌ crash | control | - | 46 sn |
| [EKF failsafe untriggered resulting in crash #1](https://github.com/ArduPilot/ardupilot/issues/24262) | Copter | normal | ❌ crash | control | - | 165 sn |
| [EKF failsafe untriggered on high errors, resulting in a crash #2](https://github.com/ArduPilot/ardupilot/issues/24362) | Copter | normal | ❌ crash | gps | - | 654 sn |
| [EKF failsafe untriggered on high errors, resulting in a crash #3](https://github.com/ArduPilot/ardupilot/issues/24371) | Copter | normal | ❌ crash | control | - | 157 sn |
| [EKF failsafe untriggered on high errors, resulting in a crash #4](https://github.com/ArduPilot/ardupilot/issues/24372) | Copter | normal | ❌ crash | control | - | 234 sn |
| [Compromising gyro values to crash the drone, EKF failsafe remains untr](https://github.com/ArduPilot/ardupilot/issues/24383) | Copter | normal | ❌ crash | gps | - | 78 sn |
| [Compromising gyro values to crash the drone, EKF failsafe remains untr](https://github.com/ArduPilot/ardupilot/issues/24384) | Copter | normal | ❌ crash | control | - | 96 sn |
| [Compromising gyro values to crash the drone, EKF failsafe remains untr](https://github.com/ArduPilot/ardupilot/issues/24388) | Copter | normal | ❌ crash | power | - | 96 sn |
| [Compromising gyro values to crash the drone, EKF failsafe remains untr](https://github.com/ArduPilot/ardupilot/issues/24389) | Copter | normal | ❌ crash | motor | - | 97 sn |
| [Compromising gyro values to crash the drone, EKF failsafe remains untr](https://github.com/ArduPilot/ardupilot/issues/24390) | Copter | normal | ❌ crash | motor | - | 129 sn |
| [Compromising gyro values to crash the drone, EKF failsafe remains untr](https://github.com/ArduPilot/ardupilot/issues/24392) | Copter | normal | ❌ crash | motor | - | 153 sn |
| [Compromising gyro values to crash the drone, EKF failsafe remains untr](https://github.com/ArduPilot/ardupilot/issues/24393) | Copter | normal | ❌ crash | motor | - | 275 sn |
| [EKF failsafe untriggered on high errors, resulting in a crash #7](https://github.com/ArduPilot/ardupilot/issues/24441) | Copter | normal | ❌ crash | control | - | 255 sn |
| [EKF failsafe untriggered on high errors, resulting in a crash #8](https://github.com/ArduPilot/ardupilot/issues/24442) | Copter | normal | ❌ crash | motor | - | 254 sn |
| [EKF failsafe untriggered on high errors, resulting in a crash #9](https://github.com/ArduPilot/ardupilot/issues/24443) | Copter | normal | ❌ crash | control | - | 179 sn |
| [Tuning issues with plane, successful auto t/o and land maiden - now no](https://discuss.ardupilot.org/t/tuning-issues-with-plane-successful-auto-t-o-and-land-maiden-now-not-so-much/100608) | Plane | normal | ✅ incident | compass | - | 639 sn |
| [Updating from 4.0.7 to 4.3.3 requires new PID tuning?](https://discuss.ardupilot.org/t/updating-from-4-0-7-to-4-3-3-requires-new-pid-tuning/101399) | Copter | normal | ✅ incident | unknown | - | 487 sn |
| [RC Input issues, log review, and questions](https://discuss.ardupilot.org/t/rc-input-issues-log-review-and-questions/101553) | Plane | normal | ❌ incident | power | - | 567 sn |
| [Seeking Feedback on Tuning 7-Inch Copter for Improved Stability](https://discuss.ardupilot.org/t/seeking-feedback-on-tuning-7-inch-copter-for-improved-stability/103076) | Copter | normal | ❌ incident | control | - | 215 sn |
| [Geo-fence problem - model not loitering in 15m radius circle](https://discuss.ardupilot.org/t/geo-fence-problem-model-not-loitering-in-15m-radius-circle/104226) | Plane | normal | ❌ incident | control | - | 349 sn |
| [Auto takeoff is not fully reliable & Autoland is problematic](https://discuss.ardupilot.org/t/auto-takeoff-is-not-fully-reliable-autoland-is-problematic/108252) | Plane | normal | ✅ incident | compass | - | 465 sn |
| [Jitter in auto modes, help with log review](https://discuss.ardupilot.org/t/jitter-in-auto-modes-help-with-log-review/108349) | Copter | normal | ✅ incident | unknown | - | 27 sn |
| [Weird hovering issue - requires 3A to hover then jumps to 6A after a f](https://discuss.ardupilot.org/t/weird-hovering-issue-requires-3a-to-hover-then-jumps-to-6a-after-a-few-and-back-to-3a-and-so-on/110871) | Copter | normal | ✅ incident | compass | - | 1271 sn |
| [Performance review of Quadcopter](https://discuss.ardupilot.org/t/performance-review-of-quadcopter/112001) | Copter | normal | ✅ incident | unknown | - | 575 sn |
| [“AutoTune: failing to level, please tune manually”](https://discuss.ardupilot.org/t/autotune-failing-to-level-please-tune-manually/117575) | Copter | normal | ✅ incident | unknown | - | 729 sn |
| [Throttle issue in transition](https://discuss.ardupilot.org/t/throttle-issue-in-transition/118790) | Plane | normal | ✅ incident | unknown | - | 155 sn |
| [Review log for Yaw 1Hz oscillation](https://discuss.ardupilot.org/t/review-log-for-yaw-1hz-oscillation/122473) | Plane | normal | ✅ incident | unknown | - | 92 sn |
| [Stabilizing the copter's hover](https://discuss.ardupilot.org/t/stabilizing-the-copters-hover/123701) | Copter | normal | ✅ incident | battery | - | 429 sn |
| [Racer pitch tuning on fast speeds](https://discuss.ardupilot.org/t/racer-pitch-tuning-on-fast-speeds/123961) | Copter | normal | ✅ incident | unknown | - | 103 sn |
| [Auto tune on yaw not so great?](https://discuss.ardupilot.org/t/auto-tune-on-yaw-not-so-great/124552) | Copter | normal | ✅ incident | unknown | - | 286 sn |
| [Autotune too low ATC_ACCEL_R_MAX value](https://discuss.ardupilot.org/t/autotune-too-low-atc-accel-r-max-value/126196) | Copter | normal | ❌ incident | vibration | - | 449 sn |
| [Manual Tuning to auto tune](https://discuss.ardupilot.org/t/manual-tuning-to-auto-tune/126371) | Copter | normal | ✅ incident | unknown | - | 2488 sn |
| [Servo center problem](https://discuss.ardupilot.org/t/servo-center-problem/128690) | Plane | normal | ❌ incident | control | - | 261 sn |
| [Notch filter review cross check](https://discuss.ardupilot.org/t/notch-filter-review-cross-check/130954) | Copter | normal | ✅ incident | unknown | - | 200 sn |
| [Issues with transition between QSTABILIZE and FBWA for tiltrotor plane](https://discuss.ardupilot.org/t/issues-with-transition-between-qstabilize-and-fbwa-for-tiltrotor-plane/131237) | Plane | normal | ✅ incident | unknown | - | 393 sn |
| [About Pid tuning of 30inch prop quadrotor](https://discuss.ardupilot.org/t/about-pid-tuning-of-30inch-prop-quadrotor/131480) | Copter | normal | ✅ incident | unknown | - | 6146 sn |
| [PITCH oscillations in horizontal flight. Inability to adjust PID in AU](https://discuss.ardupilot.org/t/pitch-oscillations-in-horizontal-flight-inability-to-adjust-pid-in-autotune-mode/132168) | Plane | normal | ✅ incident | control | - | 2545 sn |
| [Trajectory issues during automatic flight](https://discuss.ardupilot.org/t/trajectory-issues-during-automatic-flight/133655) | Plane | normal | ✅ incident | control | - | 1221 sn |
| [Tricopter VTOL Tilts Forward During Hover Test — Suspected Inverted Pi](https://discuss.ardupilot.org/t/tricopter-vtol-tilts-forward-during-hover-test-suspected-inverted-pitch/133808) | Plane | normal | ✅ incident | control | - | 305 sn |
| [Unstable Flight and Sudden Drift After Autotune on 7" Quad – ArduCopte](https://discuss.ardupilot.org/t/unstable-flight-and-sudden-drift-after-autotune-on-7-quad-arducopter-4-5-7/134177) | Copter | normal | ❌ incident | pilot | - | 1059 sn |
| [PID review tool - understanding PID Spectrogram and Frequency Domain](https://discuss.ardupilot.org/t/pid-review-tool-understanding-pid-spectrogram-and-frequency-domain/134805) | Copter | normal | ✅ incident | unknown | - | 134 sn |
| [VTOL Position Hold Instability – Suspected Compass Issue (BZGNSS BZ-25](https://discuss.ardupilot.org/t/vtol-position-hold-instability-suspected-compass-issue-bzgnss-bz-251-speedybee-f405-wing-mini/136234) | Plane | normal | ❌ incident | control | - | 1175 sn |
| [Autotune doesnt complete, logs cut off](https://discuss.ardupilot.org/t/autotune-doesnt-complete-logs-cut-off/137946) | Copter | normal | ❌ incident | power | - | 170 sn |
| [My logs (and only my logs) wont open in the PID Review Tool](https://discuss.ardupilot.org/t/my-logs-and-only-my-logs-wont-open-in-the-pid-review-tool/137978) | Copter | normal | ✅ incident | unknown | - | 46 sn |
| [Tuning 4" Micro Long Range](https://discuss.ardupilot.org/t/tuning-4-micro-long-range/139094) | Copter | normal | ✅ incident | compass | - | 93 sn |
| [Hover Learn Results and INS Raw Log Review](https://discuss.ardupilot.org/t/hover-learn-results-and-ins-raw-log-review/141829) | Copter | normal | ✅ incident | unknown | - | 185 sn |
| [Large Quad tune](https://discuss.ardupilot.org/t/large-quad-tune/143560) | Copter | normal | ✅ incident | unknown | - | 143 sn |
| [Turbine plane navigation tuning and throttle control](https://discuss.ardupilot.org/t/turbine-plane-navigation-tuning-and-throttle-control/143682) | Plane | normal | ✅ incident | vibration | - | 1299 sn |
| [10inch copter tuning. Throttle notch](https://discuss.ardupilot.org/t/10inch-copter-tuning-throttle-notch/144690) | Copter | normal | ❌ incident | pilot | - | 72 sn |
| [ArduCopter 4.7.1 7 inch build does not sit put in the air even after a](https://discuss.ardupilot.org/t/arducopter-4-7-1-7-inch-build-does-not-sit-put-in-the-air-even-after-auto-tuning/145679) | Copter | normal | ✅ incident | unknown | - | 77 sn |
| [First Flight & some issues with X8. Need help analysing logs!](https://discuss.ardupilot.org/t/first-flight-some-issues-with-x8-need-help-analysing-logs/17024) | Copter | normal | ❌ incident | vibration | - | 642 sn |
| [Autotune RC5 - concerning observations](https://discuss.ardupilot.org/t/autotune-rc5-concerning-observations/17560) | Copter | normal | ✅ incident | battery | - | 1606 sn |
| [Autotune Copter 3.5](https://discuss.ardupilot.org/t/autotune-copter-3-5/19441) | Copter | normal | ✅ incident | unknown | - | 705 sn |
| [NEED HELP: Couldn't get better tuning](https://discuss.ardupilot.org/t/need-help-couldnt-get-better-tuning/27349) | Copter | normal | ✅ incident | unknown | - | 93 sn |
| [Indoor position controller tuning](https://discuss.ardupilot.org/t/indoor-position-controller-tuning/32542) | Copter | normal | ❌ incident | power | - | 214 sn |
| [Pixracer Arduplane 3.9.8 bad log files](https://discuss.ardupilot.org/t/pixracer-arduplane-3-9-8-bad-log-files/43183) | Plane | normal | ❌ incident | control | - | 75 sn |
| [Motor wobbling in stab-mode after autotune](https://discuss.ardupilot.org/t/motor-wobbling-in-stab-mode-after-autotune/45923) | Copter | normal | ✅ incident | compass | - | 45 sn |
| [Not holding heading during flare? .bin logfiles provided](https://discuss.ardupilot.org/t/not-holding-heading-during-flare-bin-logfiles-provided/50427) | Plane | normal | ✅ incident | control | - | 1854 sn |
| [Tuning an ultra slow rover](https://discuss.ardupilot.org/t/tuning-an-ultra-slow-rover/50732) | Rover | normal | ❌ incident | power | - | 1523 sn |
| [Need help in optimizing the hovering performance](https://discuss.ardupilot.org/t/need-help-in-optimizing-the-hovering-performance/54031) | Copter | normal | ✅ incident | unknown | - | 431 sn |
| [How to improve AutoTune results on big quad coaxial X8 [RESOLVED]](https://discuss.ardupilot.org/t/how-to-improve-autotune-results-on-big-quad-coaxial-x8-resolved/54450) | Copter | normal | ✅ incident | unknown | - | 296 sn |
| [How to force pitch AUTOTUNE?](https://discuss.ardupilot.org/t/how-to-force-pitch-autotune/59957) | Plane | normal | ✅ incident | stall | - | 1289 sn |
| [Pitch Wobble - Autotune Didn't Fix](https://discuss.ardupilot.org/t/pitch-wobble-autotune-didnt-fix/69731) | Plane | normal | ✅ incident | control | - | 555 sn |
| [4.1 beta autotune failsafe](https://discuss.ardupilot.org/t/4-1-beta-autotune-failsafe/70698) | Copter | normal | ✅ incident | radio | - | 235 sn |
| [Oscilations when switching to mission from hover](https://discuss.ardupilot.org/t/oscilations-when-switching-to-mission-from-hover/72523) | Copter | normal | ✅ incident | compass | - | 924 sn |
| [Hovering current](https://discuss.ardupilot.org/t/hovering-current/72796) | Copter | normal | ✅ incident | battery | - | 374 sn |
| [Autotune plane: need help > desired Roll and achieved Roll](https://discuss.ardupilot.org/t/autotune-plane-need-help-desired-roll-and-achieved-roll/73304) | Plane | normal | ❌ incident | power | - | 1438 sn |
| [AUTOTUNE resulted in twitchy control surfaces](https://discuss.ardupilot.org/t/autotune-resulted-in-twitchy-control-surfaces/73403) | Plane | normal | ✅ incident | stall | - | 1789 sn |
| [Trex600 with Pixhawk4 mini and Arducopter 4.1.2 Tuning help](https://discuss.ardupilot.org/t/trex600-with-pixhawk4-mini-and-arducopter-4-1-2-tuning-help/79396) | Copter | normal | ✅ incident | unknown | - | 1296 sn |
| [AutoTune Copter 4.1.2 on 3" Quad [Squirtv2.1] : Roll tuning failed wit](https://discuss.ardupilot.org/t/autotune-copter-4-1-2-on-3-quad-squirtv2-1-roll-tuning-failed-with-autotune-reached-limit/79901) | Copter | normal | ✅ incident | battery | - | 469 sn |
| [Help connecting SITL to RealFlight 9.5S](https://discuss.ardupilot.org/t/help-connecting-sitl-to-realflight-9-5s/82854) | Plane | normal | ❌ incident | control | - | 170 sn |
| [Twitching when hovering and hot motors after flight](https://discuss.ardupilot.org/t/twitching-when-hovering-and-hot-motors-after-flight/85068) | Copter | normal | ❌ incident | motor | - | 214 sn |
| [Wobbling in hover flight, strong oscillations in servo output](https://discuss.ardupilot.org/t/wobbling-in-hover-flight-strong-oscillations-in-servo-output/89816) | Copter | normal | ✅ incident | radio | - | 68 sn |
| [Filtering Vibration to Get a Better Tune](https://discuss.ardupilot.org/t/filtering-vibration-to-get-a-better-tune/98578) | Copter | normal | ✅ incident | compass | - | 266 sn |
| [First Flight Analysis](https://discuss.ardupilot.org/t/first-flight-analysis/99121) | Copter | normal | ❌ incident | motor | - | 32 sn |
| [First Maiden Log File](https://discuss.ardupilot.org/t/first-maiden-log-file/99997) | Copter | normal | ✅ incident | motor | - | 175 sn |
| [[VTOL] LOITER_TIME after a DO_TRANSITION_VTOL at 3 (MC) crashes the SI](https://github.com/ArduPilot/ardupilot/issues/18932) | Plane | normal | ❌ incident | power | - | 80 sn |
| [EKF failsafe untriggered on high errors, resulting in a crash #5](https://github.com/ArduPilot/ardupilot/issues/24373) | Copter | normal | ❌ incident | gps | - | 21 sn |
| [Compromising gyro values to crash the drone, EKF failsafe remains untr](https://github.com/ArduPilot/ardupilot/issues/24387) | Copter | normal | ❌ incident | power | - | 77 sn |
| [Compromising gyro values to crash the drone, EKF failsafe remains untr](https://github.com/ArduPilot/ardupilot/issues/24391) | Copter | normal | ❌ incident | gps | - | 38 sn |
| [EKF failsafe untriggered on high errors - Resulting in crash ](https://github.com/ArduPilot/ardupilot/issues/24445) | Copter | normal | ❌ incident | control | - | 94 sn |
| [Changing SIM_IMU_POS_X/Y causes the Copter to deviate from its origina](https://github.com/ArduPilot/ardupilot/issues/28720) | Copter | normal | ❌ incident | gps | - | 138 sn |
| [Plane: Guided Fly To not safe in steep terrain and SITL doesn't detect](https://github.com/ArduPilot/ardupilot/issues/29914) | Plane | normal | ❌ incident | power | - | 245 sn |
| [Autotune won't engage](https://discuss.ardupilot.org/t/autotune-wont-engage/101722) | Copter | normal | ✅ noflight | - | - | 310 sn |
| [About INS_acc_fillter question! plz help](https://discuss.ardupilot.org/t/about-ins-acc-fillter-question-plz-help/110823) | Plane | normal | ✅ noflight | - | - | 256 sn |
| [Recommended logging settings for HNTCH and ACRO PID tuning](https://discuss.ardupilot.org/t/recommended-logging-settings-for-hntch-and-acro-pid-tuning/118420) | Copter | normal | ✅ noflight | - | - | 76 sn |
| [IMU mask causing log visualization issues](https://discuss.ardupilot.org/t/imu-mask-causing-log-visualization-issues/125817) | Plane | normal | ✅ noflight | - | - | 44 sn |
| [Matek ASPD-AUAV baro problems](https://discuss.ardupilot.org/t/matek-aspd-auav-baro-problems/145628) | Plane | normal | ✅ noflight | - | - | 99 sn |
| [Issues with Pixracer in 3.8.0beta3](https://discuss.ardupilot.org/t/issues-with-pixracer-in-3-8-0beta3/15991) | Plane | normal | ✅ noflight | - | - | 95 sn |
| [Arduplan servo output problem/question [SOLVED]](https://discuss.ardupilot.org/t/arduplan-servo-output-problem-question-solved/33064) | Plane | normal | ✅ noflight | - | - | 16 sn |
| [Issues with logs](https://discuss.ardupilot.org/t/issues-with-logs/48063) | Plane | normal | ✅ noflight | - | - | 15 sn |
| [Maiden Tarot 650 rolls right (tips over) before take off when I increa](https://discuss.ardupilot.org/t/maiden-tarot-650-rolls-right-tips-over-before-take-off-when-i-increased-throttle-log/64684) | Copter | normal | ✅ noflight | - | - | 47 sn |
| [EKF inconsistent problem](https://discuss.ardupilot.org/t/ekf-inconsistent-problem/65521) | Plane | normal | ✅ noflight | - | - | 78 sn |
| [Problem Getting NMEA Strings Out a Serial Port (Location Data Zero)](https://discuss.ardupilot.org/t/problem-getting-nmea-strings-out-a-serial-port-location-data-zero/72341) | Plane | normal | ✅ noflight | - | - | 77 sn |
| [Error Parsing ArduPilot log file](https://discuss.ardupilot.org/t/error-parsing-ardupilot-log-file/89354) | Plane | normal | ✅ noflight | - | - | 6 sn |
| [No throttle output in FBWA or Autotune mode](https://discuss.ardupilot.org/t/no-throttle-output-in-fbwa-or-autotune-mode/97236) | Plane | normal | ✅ noflight | - | - | 15 sn |
| [New build, safe for autotune or need filter setup first?](https://discuss.ardupilot.org/t/new-build-safe-for-autotune-or-need-filter-setup-first/100104) | Copter | normal | ✅ normal | - | - | 274 sn |
| [Tune in auto is very aggressive compared to stabilise](https://discuss.ardupilot.org/t/tune-in-auto-is-very-aggressive-compared-to-stabilise/101115) | Copter | normal | ✅ normal | - | - | 1142 sn |
| [New tuning needed when change from Lipo to Li-ion](https://discuss.ardupilot.org/t/new-tuning-needed-when-change-from-lipo-to-li-ion/101887) | Copter | normal | ✅ normal | - | - | 879 sn |
| [FFT based harmonic notch filter for dynamic tuning](https://discuss.ardupilot.org/t/fft-based-harmonic-notch-filter-for-dynamic-tuning/104391) | Copter | normal | ✅ normal | - | - | 118 sn |
| [MOT_THST_EXPO and autotune](https://discuss.ardupilot.org/t/mot-thst-expo-and-autotune/105480) | Copter | normal | ✅ normal | - | - | 262 sn |
| [Some assistance needed for a New tune on a small hexa drone](https://discuss.ardupilot.org/t/some-assistance-needed-for-a-new-tune-on-a-small-hexa-drone/106850) | Copter | normal | ✅ normal | - | - | 116 sn |
| [Need Help tuning large frame hex.](https://discuss.ardupilot.org/t/need-help-tuning-large-frame-hex/107280) | Copter | normal | ✅ normal | - | - | 104 sn |
| [Quad-Plane Throttle Dropped Out During Transition](https://discuss.ardupilot.org/t/quad-plane-throttle-dropped-out-during-transition/107914) | Plane | normal | ✅ normal | - | - | 3164 sn |
| [Need help getting quadplane off the ground](https://discuss.ardupilot.org/t/need-help-getting-quadplane-off-the-ground/108427) | Plane | normal | ✅ normal | - | - | 51 sn |
| [Log Review: AUTO mission stopped in flight](https://discuss.ardupilot.org/t/log-review-auto-mission-stopped-in-flight/110997) | Copter | normal | ✅ normal | - | - | 507 sn |
| [Flight log data](https://discuss.ardupilot.org/t/flight-log-data/112177) | Plane | normal | ✅ normal | - | - | 656 sn |
| [Copter 4.4 Notch filter Tune for fast dynamic flight](https://discuss.ardupilot.org/t/copter-4-4-notch-filter-tune-for-fast-dynamic-flight/112561) | Copter | normal | ✅ normal | - | - | 286 sn |
| [No tracking data available for Throttle notch when using Filter Review](https://discuss.ardupilot.org/t/no-tracking-data-available-for-throttle-notch-when-using-filter-review-tool/113009) | Copter | normal | ✅ normal | - | - | 133 sn |
| [Notch filter review+ tune analysis](https://discuss.ardupilot.org/t/notch-filter-review-tune-analysis/115513) | Plane | normal | ✅ normal | - | - | 134 sn |
| [Log review: autotune, cuav yaw with gps and optical flow](https://discuss.ardupilot.org/t/log-review-autotune-cuav-yaw-with-gps-and-optical-flow/115971) | Copter | normal | ✅ normal | - | - | 587 sn |
| [Help Needed with Tuning Issues on 5L Payload Drone in PosHold Mode](https://discuss.ardupilot.org/t/help-needed-with-tuning-issues-on-5l-payload-drone-in-poshold-mode/119994) | Copter | normal | ✅ normal | - | - | 379 sn |
| [Autotune gives poor tuning values on roll axis and causing vibration o](https://discuss.ardupilot.org/t/autotune-gives-poor-tuning-values-on-roll-axis-and-causing-vibration-on-arms/120018) | Copter | normal | ✅ normal | - | - | 256 sn |
| [Tuning Pitch/Roll offsets. How to read the Log file data](https://discuss.ardupilot.org/t/tuning-pitch-roll-offsets-how-to-read-the-log-file-data/120372) | Copter | normal | ✅ normal | - | - | 450 sn |
| [Hot motors, even in gentle hover](https://discuss.ardupilot.org/t/hot-motors-even-in-gentle-hover/122147) | Copter | normal | ✅ normal | - | - | 207 sn |
| [VTOL Altitude Fluctuations Between Waypoints in AUTO Mode – PID Tuning](https://discuss.ardupilot.org/t/vtol-altitude-fluctuations-between-waypoints-in-auto-mode-pid-tuning-issue/124305) | Plane | normal | ✅ normal | - | - | 301 sn |
| [VTOL Transition Issue: Unsmooth and Delayed](https://discuss.ardupilot.org/t/vtol-transition-issue-unsmooth-and-delayed/124955) | Plane | normal | ✅ normal | - | - | 210 sn |
| [Quadcopter oscillation and tuning](https://discuss.ardupilot.org/t/quadcopter-oscillation-and-tuning/126151) | Copter | normal | ✅ normal | - | - | 163 sn |
| [Quadcopter aggressive gains after autotune](https://discuss.ardupilot.org/t/quadcopter-aggressive-gains-after-autotune/126920) | Copter | normal | ✅ normal | - | - | 87 sn |
| [Notch Filter & Pids Results Recommendation/Review](https://discuss.ardupilot.org/t/notch-filter-pids-results-recommendation-review/127834) | Copter | normal | ✅ normal | - | - | 341 sn |
| [Tuning the slop and wobble out of an 18" quad](https://discuss.ardupilot.org/t/tuning-the-slop-and-wobble-out-of-an-18-quad/127898) | Copter | normal | ✅ normal | - | - | 117 sn |
| [Autotune is not giving a proper gains for CUAV x7+ and taking long tim](https://discuss.ardupilot.org/t/autotune-is-not-giving-a-proper-gains-for-cuav-x7-and-taking-long-time-for-tuning/128353) | Copter | normal | ✅ normal | - | - | 1431 sn |
| [VTOL Quick Tune First Test Shoulder Button Not Triggering](https://discuss.ardupilot.org/t/vtol-quick-tune-first-test-shoulder-button-not-triggering/129502) | Copter | normal | ✅ normal | - | - | 71 sn |
| [Help to analyse PID review](https://discuss.ardupilot.org/t/help-to-analyse-pid-review/130716) | Copter | normal | ✅ normal | - | - | 350 sn |
| [In-Flight FFT filter tuning issues](https://discuss.ardupilot.org/t/in-flight-fft-filter-tuning-issues/132328) | Copter | normal | ✅ normal | - | - | 92 sn |
| [Tuning Large drone - General Pixhawk & PID Help](https://discuss.ardupilot.org/t/tuning-large-drone-general-pixhawk-pid-help/133146) | Copter | normal | ✅ normal | - | - | 2100 sn |
| [Quick tune produces poor results compared to basic pid params](https://discuss.ardupilot.org/t/quick-tune-produces-poor-results-compared-to-basic-pid-params/133410) | Copter | normal | ✅ normal | - | - | 227 sn |
| [5 inch quad initial tuning](https://discuss.ardupilot.org/t/5-inch-quad-initial-tuning/134726) | Copter | normal | ✅ normal | - | - | 71 sn |
| [Any 'workaround' to improve hover margin?](https://discuss.ardupilot.org/t/any-workaround-to-improve-hover-margin/136346) | Plane | normal | ✅ normal | - | - | 134 sn |
| [Help with Harmonic Notch Suggestions - Filter Review Tool](https://discuss.ardupilot.org/t/help-with-harmonic-notch-suggestions-filter-review-tool/137873) | Copter | normal | ✅ normal | - | - | 191 sn |
| [Plane - Yaw autotune not working](https://discuss.ardupilot.org/t/plane-yaw-autotune-not-working/138468) | Plane | normal | ✅ normal | - | - | 623 sn |
| [Hex drifting in roll in Loiter after Autotune](https://discuss.ardupilot.org/t/hex-drifting-in-roll-in-loiter-after-autotune/140207) | Copter | normal | ✅ normal | - | - | 1374 sn |
| [High-frequency vibration during hovering and trembles when descending](https://discuss.ardupilot.org/t/high-frequency-vibration-during-hovering-and-trembles-when-descending/141624) | Copter | normal | ✅ normal | - | - | 62 sn |
| [Verifying stability & understanding MagFit / AutoTune](https://discuss.ardupilot.org/t/verifying-stability-understanding-magfit-autotune/141817) | Copter | normal | ✅ normal | - | - | 292 sn |
| [Problems with rangefinder assisted flare](https://discuss.ardupilot.org/t/problems-with-rangefinder-assisted-flare/143694) | Plane | normal | ✅ normal | - | - | 1419 sn |
| [Oscillation after autotune of 6inch quadrotor](https://discuss.ardupilot.org/t/oscillation-after-autotune-of-6inch-quadrotor/143931) | Copter | normal | ✅ normal | - | - | 327 sn |
| [Filter Review - can't select "post" filter, can't turn off "estimated ](https://discuss.ardupilot.org/t/filter-review-cant-select-post-filter-cant-turn-off-estimated-post-filter/144164) | Copter | normal | ✅ normal | - | - | 197 sn |
| [Filter review Tool for a Y6 frame](https://discuss.ardupilot.org/t/filter-review-tool-for-a-y6-frame/145027) | Plane | normal | ✅ normal | - | - | 147 sn |
| [AutoTune unsuccessful](https://discuss.ardupilot.org/t/autotune-unsuccessful/145269) | Copter | normal | ✅ normal | - | - | 425 sn |
| [AutoTune: Failed to level, please tune manually](https://discuss.ardupilot.org/t/autotune-failed-to-level-please-tune-manually/145291) | Copter | normal | ✅ normal | - | - | 276 sn |
| [SpeedyBee Bee35 Copter Tuning](https://discuss.ardupilot.org/t/speedybee-bee35-copter-tuning/145362) | Copter | normal | ✅ normal | - | - | 111 sn |
| [Autotune will no longer work](https://discuss.ardupilot.org/t/autotune-will-no-longer-work/17420) | Copter | normal | ✅ normal | - | - | 111 sn |
| [Autotune fails on Y6 3.5RC7](https://discuss.ardupilot.org/t/autotune-fails-on-y6-3-5rc7/18457) | Copter | normal | ✅ normal | - | - | 383 sn |
| [Why does quadplane experience a negative pitch during transition?](https://discuss.ardupilot.org/t/why-does-quadplane-experience-a-negative-pitch-during-transition/27783) | Plane | normal | ✅ normal | - | - | 122 sn |
| [Auto tune complete, but quad flies "drunk"](https://discuss.ardupilot.org/t/auto-tune-complete-but-quad-flies-drunk/35405) | Copter | normal | ✅ normal | - | - | 2792 sn |
| [Crash - help with bin analysis](https://discuss.ardupilot.org/t/crash-help-with-bin-analysis/42329) | Copter | normal | ✅ normal | - | - | 701 sn |
| [AutoTune not working at Copter 3.6.10](https://discuss.ardupilot.org/t/autotune-not-working-at-copter-3-6-10/46511) | Copter | normal | ✅ normal | - | - | 508 sn |
| [Autotune failed to save new PID with Copter-4.0.0-rc2](https://discuss.ardupilot.org/t/autotune-failed-to-save-new-pid-with-copter-4-0-0-rc2/49885) | Copter | normal | ✅ normal | - | - | 685 sn |
| [Autotune Roll result sluggish](https://discuss.ardupilot.org/t/autotune-roll-result-sluggish/50812) | Copter | normal | ✅ normal | - | - | 517 sn |
| [PID tuning and overshoot fix](https://discuss.ardupilot.org/t/pid-tuning-and-overshoot-fix/55480) | Copter | normal | ✅ normal | - | - | 359 sn |
| [Compass Inconsistent after the first flight](https://discuss.ardupilot.org/t/compass-inconsistent-after-the-first-flight/55911) | Copter | normal | ✅ normal | - | - | 249 sn |
| [Tuning Advice for 13" quad](https://discuss.ardupilot.org/t/tuning-advice-for-13-quad/56316) | Copter | normal | ✅ normal | - | - | 198 sn |
| [Hover instability (Althold)](https://discuss.ardupilot.org/t/hover-instability-althold/56452) | Copter | normal | ✅ normal | - | - | 605 sn |
| [Pid tune help pocketoilot](https://discuss.ardupilot.org/t/pid-tune-help-pocketoilot/61372) | Copter | normal | ✅ normal | - | - | 49 sn |
| [Large PID's from Autotune](https://discuss.ardupilot.org/t/large-pids-from-autotune/63639) | Copter | normal | ✅ normal | - | - | 954 sn |
| [Pitch commands cause some yaw.🤔 I did not tune the copter](https://discuss.ardupilot.org/t/pitch-commands-cause-some-yaw-i-did-not-tune-the-copter/66822) | Copter | normal | ✅ normal | - | - | 189 sn |
| [Tuning a fleet of large quadrotors](https://discuss.ardupilot.org/t/tuning-a-fleet-of-large-quadrotors/67153) | Copter | normal | ✅ normal | - | - | 241 sn |
| [Large tricopter QuadPlane Project, tuning problems](https://discuss.ardupilot.org/t/large-tricopter-quadplane-project-tuning-problems/78322) | Plane | normal | ✅ normal | - | - | 1876 sn |
| [Log review for big hex](https://discuss.ardupilot.org/t/log-review-for-big-hex/78394) | Copter | normal | ✅ normal | - | - | 87 sn |
| [F450 log review](https://discuss.ardupilot.org/t/f450-log-review/78506) | Copter | normal | ✅ normal | - | - | 167 sn |
| [HELP with a 690 Hex AutoTune 4.1](https://discuss.ardupilot.org/t/help-with-a-690-hex-autotune-4-1/78816) | Copter | normal | ✅ normal | - | - | 362 sn |
| [What data log params to track for PID tuning](https://discuss.ardupilot.org/t/what-data-log-params-to-track-for-pid-tuning/81170) | Plane | normal | ✅ normal | - | - | 74 sn |
| [LOG analysis - sudden instability](https://discuss.ardupilot.org/t/log-analysis-sudden-instability/81354) | Copter | normal | ✅ normal | - | - | 2150 sn |
| [22", 18Kg, X8 Auto Tune: Failing](https://discuss.ardupilot.org/t/22-18kg-x8-auto-tune-failing/85070) | Copter | normal | ✅ normal | - | - | 702 sn |
| [Help tuning large, overpowered quad](https://discuss.ardupilot.org/t/help-tuning-large-overpowered-quad/85103) | Copter | normal | ✅ normal | - | - | 390 sn |
| [AutoTune PID Values didn't Save](https://discuss.ardupilot.org/t/autotune-pid-values-didnt-save/88939) | Copter | normal | ✅ normal | - | - | 416 sn |
| [Low throttle hover, MAG issues, and DSHOT600](https://discuss.ardupilot.org/t/low-throttle-hover-mag-issues-and-dshot600/89501) | Copter | normal | ✅ normal | - | - | 249 sn |
| [Manual Tuning Help for Large Quadcopter: Why does it overshoot?](https://discuss.ardupilot.org/t/manual-tuning-help-for-large-quadcopter-why-does-it-overshoot/90772) | Copter | normal | ✅ normal | - | - | 725 sn |
| [Help tuning 14" quad](https://discuss.ardupilot.org/t/help-tuning-14-quad/90984) | Copter | normal | ✅ normal | - | - | 171 sn |
| [Internal error when using Quick Tuning Lua script](https://discuss.ardupilot.org/t/internal-error-when-using-quick-tuning-lua-script/91113) | Plane | normal | ✅ normal | - | - | 233 sn |
| [How is my Autotune result? Seems off](https://discuss.ardupilot.org/t/how-is-my-autotune-result-seems-off/91359) | Copter | normal | ✅ normal | - | - | 668 sn |
| [Failed autotune Rate P and D](https://discuss.ardupilot.org/t/failed-autotune-rate-p-and-d/91915) | Copter | normal | ✅ normal | - | - | 153 sn |
| [Maiden TRex 550 flight, massive side-to-side shaking](https://discuss.ardupilot.org/t/maiden-trex-550-flight-massive-side-to-side-shaking/93323) | Copter | normal | ✅ normal | - | - | 113 sn |
| [Requesting feedback on tune of a 6 kg T-motor M1000 UAV](https://discuss.ardupilot.org/t/requesting-feedback-on-tune-of-a-6-kg-t-motor-m1000-uav/94020) | Copter | normal | ✅ normal | - | - | 1123 sn |
| [Autotune failing in 29inch drone](https://discuss.ardupilot.org/t/autotune-failing-in-29inch-drone/94516) | Copter | normal | ✅ normal | - | - | 213 sn |
| [Quadcopter not performing after Autotune](https://discuss.ardupilot.org/t/quadcopter-not-performing-after-autotune/95098) | Copter | normal | ✅ normal | - | - | 1067 sn |
| [Tuning X8 Heavy Lift - Tuning for Payload](https://discuss.ardupilot.org/t/tuning-x8-heavy-lift-tuning-for-payload/95759) | Copter | normal | ✅ normal | - | - | 787 sn |
| [AutoTune is failing. "Failing to level, please tune manually"](https://discuss.ardupilot.org/t/autotune-is-failing-failing-to-level-please-tune-manually/96277) | Copter | normal | ✅ normal | - | - | 218 sn |
| [Oscillations in poshold and land mode after a successful autotune](https://discuss.ardupilot.org/t/oscillations-in-poshold-and-land-mode-after-a-successful-autotune/99685) | Copter | normal | ✅ normal | - | - | 233 sn |
| [Copter crashes in AUTO mode after PSC_ACCZ_D accepts a negative out-of](https://github.com/ArduPilot/ardupilot/issues/33789) | Copter | normal | ✅ normal | - | - | 54 sn |
| [Strange lost of altitude behavior resulting in crash](https://github.com/ArduPilot/ardupilot/issues/4344) | Copter | normal | ✅ normal | - | - | 100 sn |
| [ PixHawk crashed while ground testing ](https://github.com/ArduPilot/ardupilot/issues/4888) | Copter | normal | ✅ normal | - | - | 155 sn |
| [Issue in horizon level, control surface correction, in tailssiter](https://discuss.ardupilot.org/t/issue-in-horizon-level-control-surface-correction-in-tailssiter/108511) | Plane | unknown | ❌ crash | control | - | 95 sn |
