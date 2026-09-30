# page 1

SIH 2026 \| CVAssure \| Team work plan with mock-ups (5 members) Page 1
CVAssure: Team Work Plan with Mock-ups Trustworthy Computer Vision
Integrity Assurance \| SIH 2026 \| 5 members. Each person owns one area,
builds their part of the MVP, and delivers one real picture for the PPT.
Mock-ups in this document show exactly what each picture and screen
should look like. A separate PPT owner, outside these 5, collects the
images and builds the PPT. Overview \# Role Owns Image delivered for PPT
1 Lead / integration Finding schema, CLI, plugin loader, YAML policy,
audit log, coverage statement, cross-asset linking Architecture diagram
(+ real CLI run screenshot) 2 Training-data integrity Label flips,
near-duplicates, OOD, spectral signatures, contributor risk, COCO / YOLO
adapters Risk heatmap + duplicate cluster 3 Model integrity Fingerprint,
weight digest, trigger sweep, trigger reconstruction, access tiers
Reconstructed trigger heatmap + access-tier matrix 4 Provenance, crypto
and dashboard Signed records, hash chain, Merkle, replay / tamper tests,
offline HTML report, QR hash, demo video Chain diagram with rejected
tamper, dashboard screenshot, 3-frame storyboard 5 Shift and attack
testbed Seeded attacks, drift vs manipulation, precision / recall /
AUROC / runtime Fog = drift vs patch = manipulation + metrics chart
Order of work • Step 1: Person 1 freezes the Finding schema (day 1) and
builds the repo skeleton with stub detectors, so the CLI and report run
end to end from day 2. • Step 2: Persons 2-5 replace their stub with a
real detector and produce their image from real output, not mock-ups.
Person 5 pushes seeded attacks out by day 2 because everyone measures
against them. • Step 3: Person 4 finishes the crypto core first, then
builds the dashboard and demo video (on dummy Finding JSON first, then
real output). • Step 4: Persons 1-5 send finished images with captions
to the PPT owner, who collects them, unifies the style, builds the deck,
exports the PDF and prepares the pitch.

------------------------------------------------------------------------

# page 2

SIH 2026 \| CVAssure \| Team work plan with mock-ups (5 members) Page 2
The MVP and how five people stay in sync MVP definition: one command,
offline on CPU, runs the whole C-07 story and produces the HTML report:
cvassure audit --data ... --model ... --records .... Data is checked and
C-07 is ranked high risk, the model is scanned and its trigger is
matched to C-07's patched samples, live records are signed and a
tampered and a replayed record are rejected, and a fog batch is labelled
drift while a patched batch is labelled manipulation. The HTML report is
the user interface. Anything beyond this list is a stretch goal. Perso n
MVP must-have (build these first) Stretch (only after MVP works) 1
Frozen Finding schema, CLI with plugin loader running on stubs by day 2,
YAML policy with 2-3 rules, audit log, coverage statement from P5's
table, cross-asset link (trigger vs patch) Red-team mode, signed dataset
/ model cards 2 Frozen embeddings, label-flip, near-duplicate and OOD
detectors on CIFAR-10, source risk with C-07 ranked first Spectral
signatures, COCO / YOLO adapters, hnswlib 3 Model wrapper with access
tiers, behavioural fingerprint, weight digest, patch-library sweep on
one backdoored and one swapped model Neural-Cleanse reconstruction,
fine-pruning curves, calibration 4 Signed hash-chained records with
tamper / replay rejection, offline HTML report with QR hash, 2-minute
demo video Merkle batches, key rotation file, hardware-token signing 5
build_demo_scenario (seeded), MMD + KS + PSI with calibration, four-axis
verdict for fog vs patch, results table for 5 attacks with a clean
control Domain classifier, GTSRB / EuroSAT, more attack variants, WaNet
Rules that keep separate work from colliding • Five contracts frozen on
day 1: Finding schema and Detector interface (P1), ground-truth manifest
(P5), record format (P4), embedding file format (P2: NumPy array plus
sample IDs), model wrapper interface (P3). Changing one means telling
everyone. • Stubs first: every detector starts as a stub that returns a
fake Finding, so the full pipeline runs immediately and each person
swaps in the real thing without waiting for others. • One repo, one
folder per person. Nobody edits another person's folder. Work goes on
branches; P1 merges small pull requests daily and breaks ties. • Shared
data by seed, not by file. Everyone regenerates the demo scenario from
P5's build_demo_scenario(seed=42). • Daily 15-minute call: done
yesterday, doing today, blocked by. A shared task board (GitHub Projects
or Trello). Anyone blocked for more than a few hours says so the same
day. • Checkpoints: day 2 stub pipeline runs, day 4 first real detectors
plugged in, day 6 full end-to-end run on the demo scenario, day 8
feature freeze, days 9-10 bug fixes and rehearsal only. How to use the
mock-ups • A mock-up is a design target so everyone builds the same
picture in the same style. It is not a result. • All numbers in mock-ups
(0.xx, xx%, N) are placeholders. Never put a mock-up on a slide.
Regenerate the picture from real output, keep the layout, and use only
measured numbers. • Every final image: PNG at least 1600 px wide,
palette blue 0070C0 and navy 1F3864, red only for danger, green only for
safe, plus a one-line caption saying what the judge should notice.

------------------------------------------------------------------------

# page 3

SIH 2026 \| CVAssure \| Team work plan with mock-ups (5 members) Page
3 1. Lead / integration MVP must-have Frozen Finding schema and JSON
Schema file; skeleton CLI running end to end on stubs by day 2; 2-3
policy rules; audit log; coverage statement generated from P5's results;
the C-07 trigger-vs-patch link. Build • Define the Finding JSON schema
(asset, reason, evidence, severity, confidence, access level,
limitations, disposition) and publish the JSON Schema file • Build the
cvassure audit CLI, plugin loader and YAML policy engine • Audit log
(reuse the hash chain from Person 4) and auto-generated coverage
statement • Cross-asset linking: match the model trigger to patches in a
contributor's samples • Run the daily sync, merge pull requests, keep
the nightly demo run green Research • Existing tools: IBM ART, Cleanlab,
NIST TrojAI; how they differ from CVAssure • SIH judging criteria and
past winning ideas PPT image Architecture diagram (data, model, records,
findings, audit) for slide 3, plus a real screenshot of the CLI run.
Sent to the PPT owner. Done when One command runs the full demo offline
and produces the report. Mock-up 1A: architecture diagram (slide 3)
MOCK-UP: design target only, illustrative values, NOT real results
INPUTS ADAPTERS DETECTOR PLUGINS FINDINGS Dataset COCO JSON / YOLO txt
Model ONNX / PyTorch Inference records JSON + Ed25519 signatures Format
adapters normalise to one internal schema model wrapper: predict /
features / gradients (declares access tier) Data integrity (P2)
embeddings, flips, dupes Model integrity (P3) fingerprint, trigger sweep
Provenance (P4) signed chain, replay / tamper Shift and drift (P5)
MMD/KS/PSI, drift vs manip. Finding objects asset, reason, evidence,
severity, confidence, access, limitations, disposition Cross-asset
linking (P1) trigger = patch in C-07? YAML policy (P1) accept / review /
quarantine Signed audit log (P1, P4) seeds, config + policy hashes
Offline HTML report (P4) heatmap, gallery, QR hash Coverage statement
(P1) generated from P5 results What the judge should notice: Three
assets in, one uniform Finding object out, and the cross-asset link
joining the data and model stories. • Must show: Inputs, adapters, four
detector plugins with owners, Finding schema box, cross-asset link,
policy, audit log, report, coverage statement. • Make the real one with:
diagrams.net (draw.io) or Mermaid / Graphviz, exported as PNG at 2x;
keep the boxes and colours of the mock-up. • File name:
p1_architecture.png

------------------------------------------------------------------------

# page 4

SIH 2026 \| CVAssure \| Team work plan with mock-ups (5 members) Page 4
Mock-up 1B: the one-command run (MVP proof, slide 4) MOCK-UP: design
target only, illustrative values, NOT real results \$ cvassure audit
--data ./demo/data --model ./demo/model.onnx --records ./demo/records
\[1/5\] Load data (COCO JSON, offline) ......... ok N images, 3
contributors \[2/5\] Data integrity ......................... 3 findings
top source: C-07 (risk 0.xx) \[3/5\] Model integrity (white-box)
............ 1 finding class 0: anomalously small trigger \[4/5\]
Inference records ...................... N records 2 REJECTED (1 edited,
1 replayed) \[5/5\] Shift assessment ....................... batch B5 =
probable drift \| batch B8 = manipulation LINK model trigger matches the
patch seen in samples from C-07 -\> severity escalated DISPOSITION data
C-07: QUARANTINE \| model: REVIEW \| records: 2 REJECTED Report:
out/report.html (sha256 9f2c...) Audit log: out/audit.log (chain
verified) Time: mm:ss What the judge should notice: One offline command
finishes all five checks, links the model trigger to C-07 and prints its
own verified report hash. • Must show: The exact command, five stages,
the LINK line, the DISPOSITION line, report path with hash and total
runtime (measured). • Make the real one with: A real terminal screenshot
of the finished tool; increase font size so it stays readable on a
slide. • File name: p1_cli_run.png Mock-up 1C: one Finding (illustrative
values) { "id": "F-019", "asset": "model", "reason": "Reconstructed
trigger for class 0 is anomalously small (MAD score 3.4)", "evidence":
\["out/evidence/F-019_mask.png", "out/evidence/F-019_scores.json"\],
"severity": 0.88, "confidence": 0.79, "access_level": "white-box",
"limitations": "Neural-Cleanse style; unreliable for blended or
input-aware triggers", "disposition": "review", "linked_findings":
\["F-012"\] } Mock-up 1D: generated coverage statement (fill from P5's
results table) Attack class Status Measured detection Main limitation
Patch / blend trigger in data Supported xx% Random-position and
clean-label triggers are weaker Label flipping Supported xx% Needs
embeddings that separate the classes Near-duplicate flooding Supported
xx% Heavy edits rely on the embedding stage OOD insertion Supported xx%
Hard OOD (similar classes) is lower than easy OOD Model substitution
Supported xx% Needs the onboarding fingerprint Backdoored model Partial
xx% Black-box: sweep only; reconstruction needs white-box Record
tampering / replay Supported xx% A compromised signing key defeats the
scheme Adaptive attackers Unsupported - Attacker knows the detectors
Imperceptible clean-label perturbations Unsupported - Not detected by
current methods Hardware / compiler backdoors Unsupported - Out of scope

------------------------------------------------------------------------

# page 5

SIH 2026 \| CVAssure \| Team work plan with mock-ups (5 members) Page 5
2. Training-data integrity MVP must-have Frozen embeddings shared by day
3; label-flip, near-duplicate and OOD detectors on CIFAR-10;
source-level risk with C-07 ranked first and C-01 / C-04 not flagged.
Build • Frozen offline embeddings (ResNet / DINO / CLIP style) shared
with the team • Label-flip detector (linear probe + cross-validation),
pHash + FAISS duplicates, Mahalanobis OOD, spectral-signature triggers •
Source-level risk score (Beta posterior) per contributor and batch •
COCO JSON and YOLO txt adapters Research • Confident learning (Northcutt
2021), Spectral Signatures (Tran 2018), Activation Clustering (Chen
2018) • FAISS / hnswlib offline usage PPT image Contributor risk heatmap
with C-07 highlighted, plus a side-by-side duplicate cluster (slides 2
and 3). Done when Detectors reach measured precision / recall on Person
5's seeded attacks. Watch out Share embeddings early; P4 and P5 depend
on them. If P5 falls behind by day 4, take over the MMD / KS / PSI
tests. Mock-up 2: risk heatmap + duplicate cluster (slides 2 and 3)
MOCK-UP: design target only, illustrative values, NOT real results
Contributor risk heatmap (source risk per batch) B1 B2 B3 B4 B5 B6 C-01
C-02 C-03 C-05 C-07 C-07: HIGH RISK 0 (normal) 1 (high risk) Ranked list
on the right of the report: C-07 first. Rows = contributors, columns =
batches over time. Near-duplicate cluster #1 (size N, source C-07) seed
image mirror shift 2px bright +10% crop + resize JPEG q40 class
distribution of cluster class 5: 92% pHash catches tier 1-2, embeddings
catch tier 3 What the judge should notice: One contributor row glows red
as batches arrive, and the duplicate flood is visible as a tight family
of edited copies from one seed image. • Must show: Contributors as rows,
batches as columns, colour scale legend, C-07 outlined and labelled; a
seed image with 5 to 8 real edited copies, cluster size, source and
class distribution. • Make the real one with: matplotlib / seaborn
heatmap from the source-risk table; PIL montage of the FAISS nearest
neighbours for the cluster; combine into one 1600 px wide PNG. • File
name: p2_risk_and_duplicates.png

------------------------------------------------------------------------

# page 6

SIH 2026 \| CVAssure \| Team work plan with mock-ups (5 members) Page 6
3. Model integrity MVP must-have Model wrapper with access tiers;
behavioural fingerprint + weight digest; patch-library trigger sweep.
Backdoored demo model flagged, swapped model changes the fingerprint.
Build • Model wrapper for ONNX and PyTorch declaring white / gray /
black-box access • Behavioural fingerprint on a fixed reference battery;
weight-digest check • Patch-library trigger sweep (black-box) and
Neural-Cleanse style reconstruction (white-box, if time) • Train small
clean and backdoored CNNs for calibration and demo Research • Neural
Cleanse (Wang 2019), Fine-Pruning (Liu 2018), BadNets (Gu 2017) • How to
calibrate confidence with known-clean vs backdoored models PPT image
Reconstructed trigger mask / heatmap and the access-tier capability
matrix (slide 3). Done when Backdoored demo model is flagged; swapped
model changes the fingerprint. Watch out Train the demo backdoored model
in week one; P1 needs it for the cross-asset link and P5 for the
metrics. Mock-up 3A: reconstructed trigger heatmap (slide 3) MOCK-UP:
design target only, illustrative values, NOT real results Input image
Reconstructed trigger mask Overlay: where the trigger sits clean sample
target class 0, mask L1 = small mask on top of the image Reconstructed
mask size per target class 0 1 2 3 4 5 6 7 8 9 median - 2 x MAD
threshold Class 0 is flagged: its reconstructed trigger is far smaller
than every other class, the Neural-Cleanse style outlier test. If only
labels are available (black-box) this panel is replaced by the
patch-sweep attack-success-rate plot. What the judge should notice: The
mask lights up exactly where the poisoned patch sits, and only one class
has a suspiciously small trigger. • Must show: Clean input,
reconstructed mask as a heat image, overlay showing the location,
per-class bar chart with the median minus 2 MAD line and the flagged
class in red. • Make the real one with: matplotlib imshow of the
optimised mask and mask-times-image overlay; bar chart of per-class mask
L1 norms. Use the sweep's attack-success-rate plot if only black-box
access exists. • File name: p3_trigger.png

------------------------------------------------------------------------

# page 7

SIH 2026 \| CVAssure \| Team work plan with mock-ups (5 members) Page 7
Mock-up 3B: access-tier capability matrix (slide 3) Method White-box
(weights + grads) Gray-box (logits / activations) Black-box (labels
only) Weight digest vs signed reference Available Unavailable
Unavailable Parameter / activation statistics Available Partial
(activations) Unavailable Trigger reconstruction (Neural Cleanse style)
Available Approximate Unavailable Behavioural fingerprint on reference
battery Available Available Available (labels only) Query-based trigger
sweep (patch library) Available Available Available Generate this matrix
automatically from the wrapper's declared capabilities so it is always
true for the model in front of you. A tool that shows "Unavailable:
black-box only" honestly is a selling point. Export as
p3_access_tiers.png. 4. Provenance, crypto and dashboard MVP must-have
Signed hash-chained inference records; edit and replay both rejected
live; offline HTML report with heatmap, gallery, timeline, quarantine
export and QR hash; 2-minute demo video. Build • Days 1-4, crypto core:
canonical JSON record (RFC 8785 style) with input hash, model digest,
config hash, output, nonce, sequence number, timestamp, previous hash •
Ed25519 signing (PyNaCl), hash chain, Merkle batch root; replay,
alteration and substitution tests; key rotation file; optional
deterministic re-execution check • Hand the hash-chain code to Person 1
early for the audit log • From day 5, dashboard: single self-contained
HTML report (no CDN): risk heatmap, evidence gallery, shift timeline,
quarantine export, report hash and QR code • Record a 2-minute demo
video following the C-07 story Research • Ed25519 (RFC 8032), JSON
canonicalisation (RFC 8785), Merkle trees (RFC 6962) • What a
compromised key means; state it in the coverage statement • Design
references for security dashboards; offline charting with inline SVG /
JS PPT image Chain diagram with red REJECTED records (slide 3) plus a
10-second screen recording; dashboard screenshot (slide 2); 3-frame
storyboard. Done when Live demo: edit one output, replay one record,
both rejected instantly. Report opens offline on any laptop; demo video
under 2 minutes. Watch out Start the dashboard on dummy Finding JSON as
soon as the schema is frozen, then swap in real output, so nothing waits
on other people.

------------------------------------------------------------------------

# page 8

SIH 2026 \| CVAssure \| Team work plan with mock-ups (5 members) Page 8
Mock-up 4A: hash chain with rejected tamper (slide 3) MOCK-UP: design
target only, illustrative values, NOT real results Merkle root (signed,
periodic) covers records #1 - #5 #1 seq 1 prev: 0000.. sig: OK #2 seq 2
prev: a1f3.. sig: OK #3 (edited) seq 3 prev: 7be0.. sig: FAIL #4 seq 4
prev: c92d.. sig: OK #5 seq 5 prev: 41aa.. sig: OK #2 replayed seq 2
(again) nonce: reused sig: OK REJECTED hash + signature do not verify
REJECTED replayed record: nonce reused Blue arrow = prev_hash link.
Every record signs its own content plus the previous record's hash, so
edits, deletions and reordering break verification. What the judge
should notice: Two red records: an edited output and a replayed old
record, both refused while every untouched record stays green. • Must
show: Six records with sequence, previous-hash and signature status, the
signed Merkle root, arrows for the chain, red callouts stating the
reason for rejection. • Make the real one with: Generate from the real
verifier output with Graphviz or matplotlib so the hashes shown are
real; also record a 10-second screen capture of the live edit and
replay. • File name: p4_chain_tamper.png

------------------------------------------------------------------------

# page 9

SIH 2026 \| CVAssure \| Team work plan with mock-ups (5 members) Page 9
Mock-up 4B: offline dashboard (slide 2) MOCK-UP: design target only,
illustrative values, NOT real results CVAssure \| Assurance Report run:
yyyy-mm-dd tool v0.x policy hash: b71c... report sha256: 7a3f9c... C-07:
HIGH RISK \| model trigger matches patch in C-07 samples \| recommended
action: QUARANTINE Contributor risk B1 B2 B3 B4 B5 B6 C-01 C-02 C-03
C-05 C-07 low high click a row: batch timeline for that source Evidence
gallery (flagged images) sev 0.9x patch sev 0.9x patch sev 0.7x dup sev
0.9x patch sev 0.7x dup sev 0.7x dup click image: full crop with trigger
overlay + evidence Shift timeline batch B1 ... B8 shift risk blue: fog =
gradual = drift red: patch = step = manipulation Findings and actions
Export quarantine list Audit: verified ID Asset Reason Severity
Disposition F-012 data patch-trigger cluster in class 0, source C-07
0.93 quarantine F-019 model anomalously small trigger, class 0 (matches
F-012) 0.88 review (escalated) F-027 records edited output + replayed
record rejected 1.00 rejected What the judge should notice: The report
already tells the story: one contributor is high risk, evidence images
show the trigger, fog and patch behave differently on the timeline, and
the report can be verified. • Must show: Verdict banner, contributor
heatmap, evidence gallery with severity chips, shift timeline, findings
table with dispositions, Export quarantine list button, audit-verified
chip, report hash and QR code. Works with no internet. • Make the real
one with: Your real report.html opened in Chrome at 1600 px width;
capture with the browser screenshot tool or Playwright. Every asset
(fonts, charts, images) is inline, no CDN. • File name: p4_dashboard.png

------------------------------------------------------------------------

# page 10

SIH 2026 \| CVAssure \| Team work plan with mock-ups (5 members) Page 10
Mock-up 4C: 3-frame demo storyboard (slide 2 or video cover) MOCK-UP:
design target only, illustrative values, NOT real results 1. Poison
found C-07 ranked high risk, with evidence 2. Trigger matched model
trigger = patch in C-07 samples 3. Tamper rejected edited and replayed
records fail verification B1 B2 B3 B4 C-02 C-03 C-05 C-07 C-07
highlighted mask = C-07 sample MATCH: severity escalated #3 edited
output REJECTED #2 replayed REJECTED rejected instantly What the judge
should notice: Poison found, trigger matched, tamper rejected: the whole
C-07 story in three frames. • Must show: Three equally sized frames with
numbered captions and arrows between them; each frame is a real cropped
screen from the demo video. • Make the real one with: Cut three frames
from the demo video (or the report) and assemble them with PIL or
PowerPoint; keep captions large. • File name: p4_storyboard.png 5. Shift
and attack testbed MVP must-have Seeded build_demo_scenario with
manifest; MMD + KS + PSI with calibration; four-axis verdict for fog vs
patch; results table for 5 attacks with a clean control. Build • Seeded
attack generators: patch / blend trigger, label flips 1-20%, duplicate
flooding, OOD insertion, model swap, record tampering, natural shift •
Reference profile plus MMD, KS and PSI tests fused with conformal
calibration • Drift-vs-manipulation scoring on four axes; "undetermined,
review" when unsure • Run all detectors and report precision, recall,
AUROC and runtime per attack (see your detailed guide PDF) Research •
ImageNet-C corruptions, MMD, conformal prediction • Datasets: CIFAR-10,
GTSRB, EuroSAT, DOTA, COCO subset PPT image Fog batch labelled
operational drift vs patched batch labelled manipulation, plus one
metrics bar chart (slides 2 and 5). Done when One results table the team
can quote: detection rate per attack, with a clean control. Watch out
Heaviest dependency in the team. Push the attack generators out by day
2, then do the shift scoring.

------------------------------------------------------------------------

# page 11

SIH 2026 \| CVAssure \| Team work plan with mock-ups (5 members) Page 11
Mock-up 5A: fog = drift, patch = manipulation (slides 2 and 5) MOCK-UP:
design target only, illustrative values, NOT real results FOG BATCH
(severity ramps 0 to 3, all sources) sample images from the batch (haze
grows) mean difference vs reference locality abruptness source class
four axes (0 = drift-like, 1 = manipulation-like) shift tag: haze /
illumination (tag accuracy xx%) PROBABLE OPERATIONAL DRIFT manipulation
score 0.xx PATCHED BATCH (C-07, from batch 5) sample images from the
batch (patch circled) mean difference vs reference locality abruptness
source class four axes (0 = drift-like, 1 = manipulation-like) shift
tag: none fits (change is localised) SUSPECTED MANIPULATION manipulation
score 0.xx Same statistical alarm (MMD, KS, PSI fire on both batches),
opposite explanation. When the axes disagree the verdict is
UNDETERMINED, REVIEW instead of a forced answer. What the judge should
notice: The same alarm fires on both batches but the explanation is
opposite: haze is global, gradual and shared; the patch is local, abrupt
and tied to one source. • Must show: Sample images from each batch,
mean-difference map (spread vs corner spot), four axis bars, shift tag,
verdict badge with score. • Make the real one with: PIL / matplotlib
panel built from real batches and real axis values; do not hand-draw the
bars. • File name: p5_fog_vs_patch.png

------------------------------------------------------------------------

# page 12

SIH 2026 \| CVAssure \| Team work plan with mock-ups (5 members) Page 12
Mock-up 5B: detection rate per attack (slide 5) MOCK-UP: design target
only, illustrative values, NOT real results Detection rate per attack
(CIFAR-10, 3 seeds, CPU only) - PLACEHOLDER 0% 50% 100% xx% Patch
trigger xx% Blend trigger xx% Label flips 5% xx% Near- duplicates xx%
OOD (SVHN) xx% Model swap xx% Record tamper xx% Fog = drift clean
control: false-alarm rate Error bars = spread over seeds. Attacks that
slip through are shown, not hidden; they feed the coverage statement.
What the judge should notice: Numbers are measured, with error bars and
a clean-control false-alarm line; weak spots are visible rather than
hidden. • Must show: One bar per attack, mean over 3+ seeds with spread,
clean-control line, title naming dataset, seeds and CPU-only. • Make the
real one with: matplotlib bar chart with figsize (10, 5.5) at dpi 200,
colours 0070C0 and 1F3864, from out/results_table.csv. • File name:
p5_metrics.png

------------------------------------------------------------------------

# page 13

SIH 2026 \| CVAssure \| Team work plan with mock-ups (5 members) Page 13
How this makes our PPT stronger The template allows only 6 slides, so
every slide must carry one strong visual and one number. Images come
from real project output. The PPT owner (outside the 5) builds the deck;
the From column shows who supplies each image. Slide Add From (mock-up)
2 Idea Dashboard screenshot + contributor heatmap + fog-vs-patch next to
the three cards P4 (4B), P2 (2), P5 (5A) 3 Technical approach
Architecture diagram, trigger heatmap, access-tier matrix, chain-tamper
picture P1 (1A), P3 (3A, 3B), P4 (4A) 4 Feasibility One line of proof:
demo runs offline on CPU in X minutes (measured), plus the CLI run P1
(1B), P5 5 Impact Results chart: detection rate per attack, drift vs
manipulation example P5 (5B, 5A) 6 References GitHub link, demo video
link (storyboard as cover), comparison row vs existing tools, coverage
statement P1 (1D), P4 (4C) Extra ideas that win points • Measured
results: even one small table beats a claim. • Comparison row: CVAssure
vs existing tools (offline, cross-asset linking, signed evidence, honest
limits). • Honest limits: show the coverage statement; "never claims
more than it can prove" is our differentiator. • Roadmap: red-team mode
and signed dataset / model cards; mention them on slide 4. • Demo story:
C-07 poisons data, model trigger matches, tamper rejected, fog labelled
as drift. Rules for everyone • One palette (blue 0070C0, navy 1F3864),
PNG images at least 1600 px wide, file names as listed in each mock-up.
• Every image needs a one-line caption saying what the judge should
notice. • Do not claim results you have not measured. Put unsupported
attacks in the coverage statement. • Send your own images straight to
the PPT owner by day 8. Submit the PPT as PDF only; keep text short and
fonts large. • Every detector outputs the frozen Finding schema. Do not
change it after day 1 without telling Person 1. Suggested timeline Days
Who What 1-2 All Contracts frozen (P1 schema, P5 manifest, P4 record
format, P2 embedding format, P3 wrapper). P1 stub pipeline runs end to
end. P5 seeded scenario pushed. 3-4 P2, P3, P5 / P4 Real detectors
replace stubs; P4 finishes crypto core and hands the hash chain to P1.
Checkpoint: first real detectors plugged in. 5-6 P2, P3, P5 / P4 First
real images exported; P4 builds the dashboard on real Finding output.
Checkpoint: full end-to-end run on the demo scenario. 7-8 P4, P5, P1
Dashboard, demo video, results table, coverage statement. Feature freeze
on day 8; all 5 send final images to the PPT owner. 9 PPT owner Final
PPT with images and rehearsal. Persons 1-5 on call for quick fixes to
their own images. 10 All Buffer and PDF upload.
