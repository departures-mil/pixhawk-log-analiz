# Gerçek kırım logları ile teşhis doğruluğu

Kaynak: discuss.ardupilot.org kamuya açık konular · Tarih: 2026-11-24 09:29 · Log sayısı: 117 (+3 okunamayan)

Etiket kaynağı: **uzman etiketleri** — her konudaki deneyimli/ekip üyelerinin yanıtları elle okunarak kırım/normal ve kök neden belirlendi (tools_data/crashbench/labels.json). Kök neden puanı yalnız uzmanların bir nedende birleştiği kırımlar üzerinden hesaplanır.

| Ölçüt | Değer |
|---|---|
| Genel doğruluk (kırım/olay ↔ normal) | %86 |
| Kırımı yakalama oranı (duyarlılık) | %92 (78/85) |
| Normal uçuşu doğru tanıma (özgüllük) | %72 (23/32) |
| Kesin 'kırım' kararı verilen kırım logları | 45/85 |
| Normal logda yanlış 'kırım' kararı | 0 |
| Kök neden uyumu (ana neden) | %59 (42/71) |
| Kök neden uyumu (ana veya ikincil nedenlerde) | %76 (54/71) |

## Sürüm geçmişi

| Tarih | Sürüm / etiket | Log | Doğruluk | Duyarlılık | Özgüllük | Kök neden |
|---|---|---|---|---|---|---|
| 2026-11-23 17:08 | v1.0.4 · forum başlığı | 65 | %77 | %85 | %56 | %21 |
| 2026-11-24 04:55 | v1.0.5 · uzman | 114 | %79 | %87 | %59 | %35 |
| 2026-11-24 05:03 | v1.0.6 · uzman | 117 | %80 | %87 | %59 | %51 |
| 2026-11-24 09:17 | dev | 117 | %84 | %93 | %59 | %52 |
| 2026-11-24 09:18 | dev | 117 | %84 | %93 | %59 | %54 |
| 2026-11-24 09:19 | dev | 114 | %86 | %93 | %66 | %58 |
| 2026-11-24 09:19 | dev | 117 | %84 | %93 | %59 | %58 |
| 2026-11-24 09:20 | dev | 117 | %86 | %89 | %78 | %56 |
| 2026-11-24 09:20 | dev | 117 | %86 | %92 | %72 | %58 |
| 2026-11-24 09:29 | dev | 117 | %86 | %92 | %72 | %59 |

## Log listesi

| Konu | Araç | Etiket | Program | Kök neden (program) | Kök neden (uzman) | Süre |
|---|---|---|---|---|---|---|
| [Crash on first flight after mayor crash](https://discuss.ardupilot.org/t/crash-on-first-flight-after-mayor-crash/10063) | Copter | crash | ✅ crash | control | compass | 89 sn |
| [*SOLVED* Agricultural Quad Crash Analysis](https://discuss.ardupilot.org/t/solved-agricultural-quad-crash-analysis/101517) | Copter | crash | ✅ crash | motor | motor | 417 sn |
| [Arducopter initial tuning and setup - Oscillation issue](https://discuss.ardupilot.org/t/arducopter-initial-tuning-and-setup-oscillation-issue/103213) | Copter | crash | ✅ crash | unknown | control | 332 sn |
| [Coptor automatically begins hovering in a roughly elliptical orbit aro](https://discuss.ardupilot.org/t/coptor-automatically-begins-hovering-in-a-roughly-elliptical-orbit-around-the-takeoff-location-in-loiter-mode/107868) | Copter | crash | ✅ crash | motor | compass | 36 sn |
| [Desired Pitch ignored - crashing at launch](https://discuss.ardupilot.org/t/desired-pitch-ignored-crashing-at-launch/117787) | Plane | crash | ✅ crash | control | control | 13 sn |
| [First crash with ardupilot, please help to find reason](https://discuss.ardupilot.org/t/first-crash-with-ardupilot-please-help-to-find-reason/118894) | Copter | crash | ✅ crash | gps | motor | 524 sn |
| [Hexacopter Crash Log Analysis Request](https://discuss.ardupilot.org/t/hexacopter-crash-log-analysis-request/121620) | Copter | crash | ✅ crash | motor | motor | 1658 sn |
| [Drone logs from our third crash](https://discuss.ardupilot.org/t/drone-logs-from-our-third-crash/125310) | Copter | crash | ✅ crash | motor | compass | 1708 sn |
| [Help me analyze the logs of the Crash](https://discuss.ardupilot.org/t/help-me-analyze-the-logs-of-the-crash/132485) | Copter | crash | ✅ crash | control | control | 82 sn |
| [Correct tuning response to manual tuning charts](https://discuss.ardupilot.org/t/correct-tuning-response-to-manual-tuning-charts/133895) | Copter | crash | ✅ crash | control | - | 151 sn |
| [Crash Analysis Help - EKF Failures, Compass Inconsistent, GPS Dropouts](https://discuss.ardupilot.org/t/crash-analysis-help-ekf-failures-compass-inconsistent-gps-dropouts-arducopter-4-5-7/135472) | Copter | crash | ✅ crash | motor | motor | 180 sn |
| [Crash analysis of hexacopter](https://discuss.ardupilot.org/t/crash-analysis-of-hexacopter/137474) | Copter | crash | ✅ crash | control | motor | 1164 sn |
| [Crashed because of Compass?](https://discuss.ardupilot.org/t/crashed-because-of-compass/137647) | Copter | crash | ✅ crash | motor | control | 414 sn |
| [Crashed – It yawed badly and crashed due to compass anomalies in ArduC](https://discuss.ardupilot.org/t/crashed-it-yawed-badly-and-crashed-due-to-compass-anomalies-in-arducopter-4-6-0-with-micoair-nxt-px4-v2/138968) | Copter | crash | ✅ crash | motor | motor | 899 sn |
| [Tandem Wing Tilt-Hexaplane Crashed during Auto Transition (Rolled Righ](https://discuss.ardupilot.org/t/tandem-wing-tilt-hexaplane-crashed-during-auto-transition-rolled-right-log-attached/140136) | Plane | crash | ✅ crash | compass | - | 53 sn |
| [Crash Analysis - Uncommanded dip in throttle](https://discuss.ardupilot.org/t/crash-analysis-uncommanded-dip-in-throttle/141437) | Copter | crash | ✅ crash | control | radio | 694 sn |
| [Review CubeOrange 21'' crash log](https://discuss.ardupilot.org/t/review-cubeorange-21-crash-log/142574) | Copter | crash | ✅ crash | control | control | 536 sn |
| [Drone has crashed, log file attached](https://discuss.ardupilot.org/t/drone-has-crashed-log-file-attached/143330) | Copter | crash | ✅ crash | control | control | 235 sn |
| [Cube 2.1,3.4.6,(I think), MP 1.3.48, New to Pixhawk2, Crash, Logs](https://discuss.ardupilot.org/t/cube-2-1-3-4-6-i-think-mp-1-3-48-new-to-pixhawk2-crash-logs/17161) | Copter | crash | ✅ crash | control | - | 314 sn |
| [Crash multiple times](https://discuss.ardupilot.org/t/crash-multiple-times/25966) | Copter | crash | ✅ crash | vibration | vibration | 29 sn |
| [Help with log analysis after maiden crash in Autotune](https://discuss.ardupilot.org/t/help-with-log-analysis-after-maiden-crash-in-autotune/34453) | Plane | crash | ✅ crash | control | control | 17 sn |
| [Crash - ALT_HOLD - Drone climbs, no throttle control](https://discuss.ardupilot.org/t/crash-alt-hold-drone-climbs-no-throttle-control/39705) | Copter | crash | ✅ crash | motor | ekf | 15 sn |
| [[solved] Strange Crash and Prearm IOMCU error on cube?](https://discuss.ardupilot.org/t/solved-strange-crash-and-prearm-iomcu-error-on-cube/41509) | Copter | crash | ✅ crash | control | - | 667 sn |
| [Crash on a X8 after starting AutoTune](https://discuss.ardupilot.org/t/crash-on-a-x8-after-starting-autotune/42085) | Copter | crash | ✅ crash | motor | motor | 642 sn |
| [Crashed in Autotune in Copter 3.6 seems like ESC problem?](https://discuss.ardupilot.org/t/crashed-in-autotune-in-copter-3-6-seems-like-esc-problem/42115) | Copter | crash | ✅ crash | motor | control | 836 sn |
| [Kakute F7 6 inch - Flip & Crash - Need help with logs](https://discuss.ardupilot.org/t/kakute-f7-6-inch-flip-crash-need-help-with-logs/42527) | Copter | crash | ✅ crash | motor | motor | 80 sn |
| [Crashed Log Analysis](https://discuss.ardupilot.org/t/crashed-log-analysis/44903) | Copter | crash | ✅ crash | motor | motor | 369 sn |
| [Copter crashed! Could you please help me?](https://discuss.ardupilot.org/t/copter-crashed-could-you-please-help-me/46644) | Copter | crash | ✅ crash | control | motor | 40 sn |
| [Crashed! Crashed into a tower while do the mission! Deviate from sched](https://discuss.ardupilot.org/t/crashed-crashed-into-a-tower-while-do-the-mission-deviate-from-scheduled-course/48069) | Copter | crash | ✅ crash | motor | control | 735 sn |
| [Copter crashed after successful autotune](https://discuss.ardupilot.org/t/copter-crashed-after-successful-autotune/54470) | Copter | crash | ✅ crash | control | control | 1304 sn |
| [Crash Analysis - QuadCopter](https://discuss.ardupilot.org/t/crash-analysis-quadcopter/55749) | Copter | crash | ✅ crash | motor | motor | 251 sn |
| [Review my crash analysis](https://discuss.ardupilot.org/t/review-my-crash-analysis/56960) | Copter | crash | ✅ crash | motor | motor | 1857 sn |
| [Help in analysis of logs after crashing(autotuning)](https://discuss.ardupilot.org/t/help-in-analysis-of-logs-after-crashing-autotuning/66230) | Copter | crash | ✅ crash | motor | motor | 801 sn |
| [Need help with crash analysis](https://discuss.ardupilot.org/t/need-help-with-crash-analysis/68371) | Copter | crash | ✅ crash | compass | vibration | 811 sn |
| [Crash ArduCopter 4.0.7 (log attached)](https://discuss.ardupilot.org/t/crash-arducopter-4-0-7-log-attached/69409) | Copter | crash | ✅ crash | motor | radio | 33 sn |
| [Need help to analyze log - sudden crash](https://discuss.ardupilot.org/t/need-help-to-analyze-log-sudden-crash/74509) | Copter | crash | ✅ crash | motor | motor | 98 sn |
| [Help needed in determining cause of crash](https://discuss.ardupilot.org/t/help-needed-in-determining-cause-of-crash/75345) | Copter | crash | ✅ crash | motor | motor | 320 sn |
| [Octocopter multiple crash](https://discuss.ardupilot.org/t/octocopter-multiple-crash/76588) | Copter | crash | ✅ crash | motor | motor | 398 sn |
| [Single copter crash log. Could someone analyze it for me?](https://discuss.ardupilot.org/t/single-copter-crash-log-could-someone-analyze-it-for-me/81825) | Copter | crash | ✅ crash | control | control | 34 sn |
| [[CRASH] Hexacopter suddenly crashed while auto](https://discuss.ardupilot.org/t/crash-hexacopter-suddenly-crashed-while-auto/83521) | Copter | crash | ✅ crash | motor | motor | 339 sn |
| [Help needed to understand crash log please](https://discuss.ardupilot.org/t/help-needed-to-understand-crash-log-please/90207) | Copter | crash | ✅ crash | vibration | vibration | 138 sn |
| [In-Flight Crash Investigation](https://discuss.ardupilot.org/t/in-flight-crash-investigation/94084) | Plane | crash | ✅ crash | control | control | 72 sn |
| [Crash Log File Assistance](https://discuss.ardupilot.org/t/crash-log-file-assistance/96429) | Copter | crash | ✅ crash | motor | motor | 117 sn |
| [Vicious Crash Log 12S X Class](https://discuss.ardupilot.org/t/vicious-crash-log-12s-x-class/98768) | Copter | crash | ✅ crash | motor | motor | 70 sn |
| [Quadcopter Crash Log Analysis Request](https://discuss.ardupilot.org/t/quadcopter-crash-log-analysis-request/99897) | Copter | crash | ✅ crash | motor | motor | 20 sn |
| [Log Analysis of Crash(Almost)](https://discuss.ardupilot.org/t/log-analysis-of-crash-almost/101181) | Copter | crash | ✅ incident | gps | vibration | 2681 sn |
| [MFE Fighter VTOL crash - suspected IO MCU failure](https://discuss.ardupilot.org/t/mfe-fighter-vtol-crash-suspected-io-mcu-failure/102276) | Plane | crash | ✅ incident | control | - | 460 sn |
| [Ardupilot Quad-plane unexpected crash](https://discuss.ardupilot.org/t/ardupilot-quad-plane-unexpected-crash/102402) | Plane | crash | ✅ incident | control | control | 23 sn |
| [V-Tail Fixed Wing Crash](https://discuss.ardupilot.org/t/v-tail-fixed-wing-crash/121201) | Plane | crash | ✅ incident | control | control | 11817726897044 sn |
| [Please help analyse a crash log](https://discuss.ardupilot.org/t/please-help-analyse-a-crash-log/121455) | Plane | crash | ✅ incident | power | control | 694 sn |
| [AUTOTUNE crash and strange logs](https://discuss.ardupilot.org/t/autotune-crash-and-strange-logs/12677) | Plane | crash | ✅ incident | stall | - | 261 sn |
| [Diagnose Pixhawk crash log](https://discuss.ardupilot.org/t/diagnose-pixhawk-crash-log/12788) | Copter | crash | ✅ incident | power | - | 87 sn |
| [Help on log analisys, Helicopter crashed](https://discuss.ardupilot.org/t/help-on-log-analisys-helicopter-crashed/133637) | Copter | crash | ✅ incident | compass | control | 27 sn |
| [Copter 4.6.1 Custom Build - Crash Dump](https://discuss.ardupilot.org/t/copter-4-6-1-custom-build-crash-dump/135782) | Copter | crash | ✅ incident | control | motor | 66 sn |
| [Newbie trying Crash Analysis on Vtol Project](https://discuss.ardupilot.org/t/newbie-trying-crash-analysis-on-vtol-project/137901) | Plane | crash | ✅ incident | control | compass | 258 sn |
| [4+1 VTOL Crash analysis in Q mode (VTOL motors quit)](https://discuss.ardupilot.org/t/4-1-vtol-crash-analysis-in-q-mode-vtol-motors-quit/142142) | Plane | crash | ✅ incident | unknown | motor | 17798507202233 sn |
| [Crash Log Analysis - Shutdown during hover](https://discuss.ardupilot.org/t/crash-log-analysis-shutdown-during-hover/142695) | Copter | crash | ✅ incident | control | - | 998 sn |
| [Log analysis Crashed!](https://discuss.ardupilot.org/t/log-analysis-crashed/142836) | Copter | crash | ✅ incident | power | power | 1618 sn |
| [Crash Analysis Request: Hexa-X / Cube Orange+ / 28" Props / ArduCopter](https://discuss.ardupilot.org/t/crash-analysis-request-hexa-x-cube-orange-28-props-arducopter-4-6-2/143577) | Copter | crash | ✅ incident | motor | motor | 830 sn |
| [Watchdog after a flight with temporary loss of control. No crash, soft](https://discuss.ardupilot.org/t/watchdog-after-a-flight-with-temporary-loss-of-control-no-crash-soft-landing/145555) | Copter | crash | ✅ incident | control | - | 216 sn |
| [Crash logs, RTL spiral into ground](https://discuss.ardupilot.org/t/crash-logs-rtl-spiral-into-ground/15863) | Plane | crash | ✅ incident | power | - | 489 sn |
| [Testing RF Immunity - Crash Log - What fails?](https://discuss.ardupilot.org/t/testing-rf-immunity-crash-log-what-fails/18540) | Copter | crash | ✅ incident | power | motor | 273810 sn |
| [Crash after Autotune, Pixhawk](https://discuss.ardupilot.org/t/crash-after-autotune-pixhawk/21863) | Copter | crash | ✅ incident | power | vibration | 654 sn |
| [CRASH: Log Review Request](https://discuss.ardupilot.org/t/crash-log-review-request/23148) | Copter | crash | ✅ incident | power | power | 2023 sn |
| [Hexacopter drifting away = crash (log + video)](https://discuss.ardupilot.org/t/hexacopter-drifting-away-crash-log-video/26675) | Copter | crash | ✅ incident | motor | compass | 139 sn |
| [Log Crash Analysis Help](https://discuss.ardupilot.org/t/log-crash-analysis-help/37003) | Copter | crash | ✅ incident | power | motor | 424325 sn |
| [AC-copter 3.7-dev fell from the sky crash log](https://discuss.ardupilot.org/t/ac-copter-3-7-dev-fell-from-the-sky-crash-log/37800) | Copter | crash | ✅ incident | gps | power | 175 sn |
| [Advice on log with crash on takeoff](https://discuss.ardupilot.org/t/advice-on-log-with-crash-on-takeoff/42843) | Plane | crash | ✅ incident | power | control | 1146 sn |
| [Helicopter lost control in stabilize mode and crashed.Log attached](https://discuss.ardupilot.org/t/helicopter-lost-control-in-stabilize-mode-and-crashed-log-attached/54194) | Copter | crash | ✅ incident | power | ekf | 690 sn |
| [Crash Log analysis and problem diagnosis (potential bug?)](https://discuss.ardupilot.org/t/crash-log-analysis-and-problem-diagnosis-potential-bug/5457) | Copter | crash | ✅ incident | power | - | 301851 sn |
| [Sudden Fall Down and Crash (Attaching LOGS)](https://discuss.ardupilot.org/t/sudden-fall-down-and-crash-attaching-logs/57400) | Copter | crash | ✅ incident | power | power | 111 sn |
| [VTOL crash analysis!](https://discuss.ardupilot.org/t/vtol-crash-analysis/69983) | Plane | crash | ✅ incident | battery | control | 147 sn |
| [Drone crashed - sudden rise in YAW during flying and crash landed](https://discuss.ardupilot.org/t/drone-crashed-sudden-rise-in-yaw-during-flying-and-crash-landed/76391) | Copter | crash | ✅ incident | motor | motor | 657 sn |
| [X Quad 3.2.1 mid flight crash](https://discuss.ardupilot.org/t/x-quad-3-2-1-mid-flight-crash/8079) | Copter | crash | ✅ incident | power | power | 230928 sn |
| [Crash with 4.2.0-beta and 4.3.0-daily (bdshot)](https://discuss.ardupilot.org/t/crash-with-4-2-0-beta-and-4-3-0-daily-bdshot/83297) | Copter | crash | ✅ incident | power | power | 124 sn |
| [New Pilot: Can someone please help me understand my crash?](https://discuss.ardupilot.org/t/new-pilot-can-someone-please-help-me-understand-my-crash/85880) | Plane | crash | ✅ incident | power | ekf | 104 sn |
| [Need help looking over a log, had an unexpected crash?](https://discuss.ardupilot.org/t/need-help-looking-over-a-log-had-an-unexpected-crash/87171) | Plane | crash | ✅ incident | control | - | 1041 sn |
| [Copter crashed with, EKF primary changed:0 EKF primary changed:2 - dea](https://discuss.ardupilot.org/t/copter-crashed-with-ekf-primary-changed-0-ekf-primary-changed-2-deadly-crash/92858) | Copter | crash | ✅ incident | power | vibration | 1034 sn |
| [Tailless VTOL crash log](https://discuss.ardupilot.org/t/tailless-vtol-crash-log/99978) | Plane | crash | ✅ incident | stall | control | 17 sn |
| [PixHawk crashed while ground testing](https://discuss.ardupilot.org/t/pixhawk-crashed-while-ground-testing/11638) | Copter | crash | ❌ noflight | - | - | 155 sn |
| [Drone sudden crash log](https://discuss.ardupilot.org/t/drone-sudden-crash-log/133605) | Copter | crash | ❌ noflight | - | motor | 29 sn |
| [Large X8 disarm/power/logging loss in flight causing crash - Onboard l](https://discuss.ardupilot.org/t/large-x8-disarm-power-logging-loss-in-flight-causing-crash-onboard-log/97192) | Copter | crash | ❌ noflight | - | power | 96 sn |
| [Discrepancy in the Matek F765 log file after a crash](https://discuss.ardupilot.org/t/discrepancy-in-the-matek-f765-log-file-after-a-crash/97318) | Plane | crash | ❌ noflight | - | - | 56 sn |
| [Crash analysis, probable power loss](https://discuss.ardupilot.org/t/crash-analysis-probable-power-loss/118356) | Copter | crash | ❌ normal | - | power | 12033899678709 sn |
| [Crash logs analysis](https://discuss.ardupilot.org/t/crash-logs-analysis/12892) | Copter | crash | ❌ normal | - | - | 173 sn |
| [VTOL tiltrotor crash in QLOITER – sudden yaw spin, backward movement, ](https://discuss.ardupilot.org/t/vtol-tiltrotor-crash-in-qloiter-sudden-yaw-spin-backward-movement-and-nose-down-rotation/145787) | Plane | crash | ❌ normal | - | - | 946 sn |
| [Loss of altitude and crash when engaging LOITER](https://discuss.ardupilot.org/t/loss-of-altitude-and-crash-when-engaging-loiter/44042) | Copter | crash | ❌ normal | - | - | 58 sn |
| [VTOL Unstable & crashed in Qstablized mode](https://discuss.ardupilot.org/t/vtol-unstable-crashed-in-qstablized-mode/82934) | Plane | crash | ❌ normal | - | control | 285 sn |
| [RC Input issues, log review, and questions](https://discuss.ardupilot.org/t/rc-input-issues-log-review-and-questions/101553) | Plane | normal | ❌ incident | power | - | 567 sn |
| [Performance review of Quadcopter](https://discuss.ardupilot.org/t/performance-review-of-quadcopter/112001) | Copter | normal | ❌ incident | unknown | - | 575 sn |
| [Review log for Yaw 1Hz oscillation](https://discuss.ardupilot.org/t/review-log-for-yaw-1hz-oscillation/122473) | Plane | normal | ❌ incident | unknown | - | 92 sn |
| [About Pid tuning of 30inch prop quadrotor](https://discuss.ardupilot.org/t/about-pid-tuning-of-30inch-prop-quadrotor/131480) | Copter | normal | ❌ incident | unknown | - | 7133983284583 sn |
| [Autotune doesnt complete, logs cut off](https://discuss.ardupilot.org/t/autotune-doesnt-complete-logs-cut-off/137946) | Copter | normal | ❌ incident | power | - | 170 sn |
| [Hover Learn Results and INS Raw Log Review](https://discuss.ardupilot.org/t/hover-learn-results-and-ins-raw-log-review/141829) | Copter | normal | ❌ incident | unknown | - | 185 sn |
| [Plane enters spiral/toilet-bowl loop during roll in AutoTune (Factory ](https://discuss.ardupilot.org/t/plane-enters-spiral-toilet-bowl-loop-during-roll-in-autotune-factory-pids/144973) | Plane | normal | ❌ incident | control | - | 600 sn |
| [First Flight & some issues with X8. Need help analysing logs!](https://discuss.ardupilot.org/t/first-flight-some-issues-with-x8-need-help-analysing-logs/17024) | Copter | normal | ❌ incident | power | - | 642 sn |
| [AUTOTUNE resulted in twitchy control surfaces](https://discuss.ardupilot.org/t/autotune-resulted-in-twitchy-control-surfaces/73403) | Plane | normal | ❌ incident | stall | - | 1789 sn |
| [Autotune won't engage](https://discuss.ardupilot.org/t/autotune-wont-engage/101722) | Copter | normal | ✅ noflight | - | - | 310 sn |
| [Seeking Feedback on Tuning 7-Inch Copter for Improved Stability](https://discuss.ardupilot.org/t/seeking-feedback-on-tuning-7-inch-copter-for-improved-stability/103076) | Copter | normal | ✅ noflight | - | - | 215 sn |
| [FFT based harmonic notch filter for dynamic tuning](https://discuss.ardupilot.org/t/fft-based-harmonic-notch-filter-for-dynamic-tuning/104391) | Copter | normal | ✅ noflight | - | - | 118 sn |
| [Jitter in auto modes, help with log review](https://discuss.ardupilot.org/t/jitter-in-auto-modes-help-with-log-review/108349) | Copter | normal | ✅ noflight | - | - | 27 sn |
| [Hot motors, even in gentle hover](https://discuss.ardupilot.org/t/hot-motors-even-in-gentle-hover/122147) | Copter | normal | ✅ noflight | - | - | 207 sn |
| [Notch filter review cross check](https://discuss.ardupilot.org/t/notch-filter-review-cross-check/130954) | Copter | normal | ✅ noflight | - | - | 200 sn |
| [My logs (and only my logs) wont open in the PID Review Tool](https://discuss.ardupilot.org/t/my-logs-and-only-my-logs-wont-open-in-the-pid-review-tool/137978) | Copter | normal | ✅ noflight | - | - | 46 sn |
| [Maiden Tarot 650 rolls right (tips over) before take off when I increa](https://discuss.ardupilot.org/t/maiden-tarot-650-rolls-right-tips-over-before-take-off-when-i-increased-throttle-log/64684) | Copter | normal | ✅ noflight | - | - | 47 sn |
| [Log review for big hex](https://discuss.ardupilot.org/t/log-review-for-big-hex/78394) | Copter | normal | ✅ noflight | - | - | 87 sn |
| [Maiden TRex 550 flight, massive side-to-side shaking](https://discuss.ardupilot.org/t/maiden-trex-550-flight-massive-side-to-side-shaking/93323) | Copter | normal | ✅ noflight | - | - | 113 sn |
| [Filtering Vibration to Get a Better Tune](https://discuss.ardupilot.org/t/filtering-vibration-to-get-a-better-tune/98578) | Copter | normal | ✅ noflight | - | - | 266 sn |
| [First Maiden Log File](https://discuss.ardupilot.org/t/first-maiden-log-file/99997) | Copter | normal | ✅ noflight | - | - | 175 sn |
| [Log Review: AUTO mission stopped in flight](https://discuss.ardupilot.org/t/log-review-auto-mission-stopped-in-flight/110997) | Copter | normal | ✅ normal | - | - | 507 sn |
| [Notch filter review+ tune analysis](https://discuss.ardupilot.org/t/notch-filter-review-tune-analysis/115513) | Plane | normal | ✅ normal | - | - | 134 sn |
| [Log review: autotune, cuav yaw with gps and optical flow](https://discuss.ardupilot.org/t/log-review-autotune-cuav-yaw-with-gps-and-optical-flow/115971) | Copter | normal | ✅ normal | - | - | 707 sn |
| [Autotune gives poor tuning values on roll axis and causing vibration o](https://discuss.ardupilot.org/t/autotune-gives-poor-tuning-values-on-roll-axis-and-causing-vibration-on-arms/120018) | Copter | normal | ✅ normal | - | - | 256 sn |
| [Quadcopter aggressive gains after autotune](https://discuss.ardupilot.org/t/quadcopter-aggressive-gains-after-autotune/126920) | Copter | normal | ✅ normal | - | - | 87 sn |
| [Pitch commands cause some yaw.🤔 I did not tune the copter](https://discuss.ardupilot.org/t/pitch-commands-cause-some-yaw-i-did-not-tune-the-copter/66822) | Copter | normal | ✅ normal | - | - | 189 sn |
| [Tuning a fleet of large quadrotors](https://discuss.ardupilot.org/t/tuning-a-fleet-of-large-quadrotors/67153) | Copter | normal | ✅ normal | - | - | 241 sn |
| [F450 log review](https://discuss.ardupilot.org/t/f450-log-review/78506) | Copter | normal | ✅ normal | - | - | 167 sn |
| [What data log params to track for PID tuning](https://discuss.ardupilot.org/t/what-data-log-params-to-track-for-pid-tuning/81170) | Plane | normal | ✅ normal | - | - | 74 sn |
| [Low throttle hover, MAG issues, and DSHOT600](https://discuss.ardupilot.org/t/low-throttle-hover-mag-issues-and-dshot600/89501) | Copter | normal | ✅ normal | - | - | 249 sn |
| [Help tuning 14" quad](https://discuss.ardupilot.org/t/help-tuning-14-quad/90984) | Copter | normal | ✅ normal | - | - | 171 sn |
