# Related tools — what CVAssure is not

**Owner:** Person 1. **All facts below were re-opened on 30 September 2026.** A claim without a
URL, or a URL that did not load, is labelled `UNVERIFIED` and must not go on a slide.

The comparison column set is fixed by the plan §13.1: offline/CPU, data + model + records
together, cross-asset link, signed tamper-evident audit, generated coverage of unsupported
attacks, unified finding schema, drift vs manipulation. Every cell is `yes` / `partial` / `no`
with a source.

---

## 1. The comparison table

| Tool | offline / CPU | data + model + records | cross-asset link | signed tamper-evident audit | generated coverage of what it cannot detect | unified finding schema | drift vs manipulation |
|---|---|---|---|---|---|---|---|
| **CVAssure** (this repo) | yes | yes | yes | partial *(hash chain now, Ed25519 when P4 lands)* | yes | yes | yes *(fixture-level today, P5's detectors pending)* |
| IBM Adversarial Robustness Toolbox | yes | no *(library, not a pipeline)* | no | no | no | no | no |
| Cleanlab | yes | no *(data only)* | no | no | no | no | no |
| NIST / IARPA TrojAI | partial *(submissions run in a container on NIST's server)* | no *(model only)* | no | no | no | partial *(one probability per model file)* | no |
| BackdoorBench | partial *(needs GPUs to be useful at benchmark scale)* | no *(experiments, not assurance)* | no | no | no | no | no |
| Microsoft Counterfit | yes | no *(model only)* | no | no | no | no | no |
| Deepchecks | partial *(a hosted product exists)* | partial *(data and model, not inference provenance)* | no | no | no | partial | partial *(data drift checks)* |
| Protect AI ModelScan | yes | no *(model file only)* | no | no | no | no | no |
| OpenSSF Model Signing (OMS) | yes | no *(model artefact only)* | no | yes *(specification)* | no | no | no |
| sigstore model-transparency | yes | no *(model artefact only)* | no | yes | no | no | no |
| in-toto | yes | no *(build steps)* | no | yes | no | no | no |
| SLSA | yes | no *(build systems)* | no | yes *(levels, not a tool)* | no | no | no |
| C2PA | yes | no *(media files, not models)* | no | yes | no | no | no |
| CycloneDX AI/ML-BOM | yes | partial *(documents inventory, not integrity)* | no | no *(references signatures, does not verify)* | no | no | no |

**Sources for every row.** Accessed 30 September 2026.

| Tool | Source URL |
|---|---|
| IBM ART | <https://adversarial-robustness-toolbox.readthedocs.io/en/latest/modules/defences/detector_poisoning.html> · <https://github.com/Trusted-AI/adversarial-robustness-toolbox> |
| Cleanlab | <https://github.com/cleanlab/cleanlab> |
| NIST / IARPA TrojAI | <https://pages.nist.gov/trojai/docs/about.html> · <https://pages.nist.gov/trojai/docs/submission.html> |
| BackdoorBench | <https://github.com/SCLBD/BackdoorBench> · <https://backdoorbench.github.io/> · licence: <https://raw.githubusercontent.com/SCLBD/BackdoorBench/main/LICENSE> |
| Microsoft Counterfit | <https://github.com/azure/counterfit> |
| Deepchecks | <https://docs.deepchecks.com/> |
| Protect AI ModelScan | <https://github.com/protectai/modelscan> |
| OpenSSF Model Signing (OMS) | <https://github.com/ossf/model-signing-spec> · <https://openssf.org/projects/model-signing/> |
| sigstore model-transparency | <https://github.com/sigstore/model-transparency> |
| in-toto | <https://in-toto.io/> |
| SLSA | <https://slsa.dev/> |
| C2PA | <https://c2pa.org/> |
| CycloneDX AI/ML-BOM | <https://cyclonedx.org/capabilities/mlbom/> |

Two corrections worth recording, because both appeared in the hand-off research and both are
wrong:

- `https://github.com/ossf/model-signing` **does not exist** (GitHub 404 on 30 Sep 2026). The
  real artefacts are the specification repo `ossf/model-signing-spec` and the project page
  `openssf.org/projects/model-signing/`.
- `https://github.com/sigstore/model-signing` **does not exist** either. The code lives in
  `sigstore/model-transparency`.

---

## 2. Short notes, one paragraph each

**IBM Adversarial Robustness Toolbox (ART).** A Python library of attacks and defences whose
poisoning-detector module implements activation clustering (Chen et al. 2018), spectral
signatures, provenance defence and RONI. It is a library of methods, not a product: it does not
assemble a multi-contributor assurance report, link a model trigger to a contributing source, or
produce a signed inference chain. MIT licensed ("MIT License, Copyright (C) The Adversarial
Robustness Toolbox (ART) Authors 2018", read from the repo's `LICENSE`). **CVAssure does not
import it.** Person 2 may take the *idea* of spectral signatures and reimplement the few lines
of linear algebra it needs, which keeps the core dependency-free and offline.
Source: <https://adversarial-robustness-toolbox.readthedocs.io/en/latest/modules/defences/detector_poisoning.html>

**Cleanlab.** Confident learning for label issues, outliers and duplicate detection; the README
describes it as the "standard data-centric AI package for data quality and machine learning with
messy, real-world data and labels". Apache-2.0 (read from the repo's `LICENSE`). It is a data
quality library: it does not reconstruct a backdoor, verify inference records, or link a model
behaviour to a contributor. Person 2 may copy the idea; **CVAssure adds no dependency on it**.
Source: <https://github.com/cleanlab/cleanlab>

**NIST / IARPA TrojAI.** A benchmark and evaluation programme for detectors that score whether an
already-trained model contains a hidden trigger. The submission documentation shows the whole
evaluation runs as a Singularity container on NIST's test and evaluation server, and a submission
produces a probability per model file. That makes it a *model-only, network-homed benchmark*, not
an air-gapped governance report over data, model and records. It is named in the problem statement
(§7.1, under Assumption A1) as a reference resource. **CVAssure does not download the TrojAI
corpus and does not vendor it.** It appears in the coverage statement as a named reference for the
attack family, and in the limitations text where a model-only benchmark is the relevant
comparison.
Sources: <https://pages.nist.gov/trojai/docs/about.html> · <https://pages.nist.gov/trojai/docs/submission.html>

**BackdoorBench.** A public benchmark of backdoor attacks and defences (NeurIPS 2022
datasets-and-benchmarks track) with a companion site. Two things matter for us. First, its licence
is **CC BY-NC 4.0 — non-commercial**; the `LICENSE` file reads "Creative Commons
Attribution-NonCommercial 4.0 International" and "Copyright (c) 2022". That is why CVAssure treats
it as a *definition* reference for attack families and never as a dependency or a data source in a
submitted artefact. Second, it is a benchmark, not an assurance product: it does not produce a
report, a finding schema, a signed audit trail, or a coverage statement. Person 5 may copy the
*definitions* of BadNets-style patch and blend attacks; **no BackdoorBench weights or code enter
this repo**, and nothing from it is downloaded.
Sources: <https://github.com/SCLBD/BackdoorBench> · <https://backdoorbench.github.io/> · <https://raw.githubusercontent.com/SCLBD/BackdoorBench/main/LICENSE>

**Microsoft Counterfit.** A CLI that the project describes as "a generic automation layer for
assessing the security of ML models" — it orchestrates attacks against a model through a
framework-agnostic interface. Model-focused, attack-focused, no data or records assessment, no
tamper-evident trail. Adjacent as a *tool design* reference (a CLI wrapping pluggable methods),
not as a competitor to an assurance layer.
Source: <https://github.com/azure/counterfit>

**Deepchecks.** Documents itself across LLM evaluation, testing and monitoring with a hosted
product. It covers data and model validation and drift, which overlaps our §§2.2.1 and 2.2.4
partly, but it does not bind inference records cryptographically and it does not emit one
assurance Finding over three assets. It is the closest *product* comparator on the drift side.
Source: <https://docs.deepchecks.com/>

**Protect AI ModelScan.** "Protection against Model Serialization Attacks" — it scans a model file
for unsafe serialisation. That is a real and adjacent control, and it is explicitly **not** what
CVAssure does: our model stage is about behaviour and provenance (substitution, triggers,
weight digest), not about whether a pickle would execute. Worth naming because a judge may ask
"doesn't something already check model files?" — the answer is yes, and it checks a different
thing.
Source: <https://github.com/protectai/modelscan>

**OpenSSF Model Signing (OMS).** A specification for signing ML model artefacts, with a project
page under the OpenSSF. It is the standards-side answer to "is this the model I think it is", and
it is where Person 4's Ed25519 record format should look for terminology. CVAssure's audit log is
a hash chain today and gains signatures when Person 4 lands; when it does, OMS is the naming
reference to check against.
Sources: <https://github.com/ossf/model-signing-spec> · <https://openssf.org/projects/model-signing/>

**sigstore model-transparency.** The implementation side of model signing, described as
"supply chain security for ML". It signs and verifies model artefacts against sigstore identity.
Person 4's design touches this space, but CVAssure's records chain binds *inference records* to
inputs, model digest and config, which is a longer chain than artefact signing.
Source: <https://github.com/sigstore/model-transparency>

**in-toto.** "A framework to secure the integrity of software supply chains", designed to make
transparent what steps produced an artefact and who performed them. The shape — an ordered,
attestable sequence of steps with a final layout — is close to our audit log's ordered events.
CVAssure's log is per-run and offline, not a supply-chain layout, but the *ordered-events-with-
hashes* idea is the same.
Source: <https://in-toto.io/>

**SLSA.** "Supply-chain Levels for Software Artifacts" — a framework and checklist of standards
and controls "to prevent tampering, improve integrity". It is a maturity specification for build
supply chains, not a tool, and it says nothing about data integrity or model behaviour. Included
because the audit-log requirement invites the comparison.
Source: <https://slsa.dev/>

**C2PA.** The Coalition for Content Provenance and Authenticity "provides an open technical
standard for publishers, creators and consumers to establish the origin and edits of digital
content". It is the closest analogue to what we do for *media files*, and its vocabulary
(provenance, assertions, edits) is worth borrowing in the report. It does not cover model
weights or contributor-level data poisoning.
Source: <https://c2pa.org/>

**CycloneDX AI/ML-BOM.** "CycloneDX facilitates transparency in AI and machine learning systems by
representing critical information about models, datasets, and their dependencies", including
dataset provenance and training methodology. It is an *inventory and documentation* format: it
records what a system claims about itself. CVAssure produces measured findings plus a covered /
unsupported statement, which is a different artefact. The two compose: an ML-BOM could carry our
coverage JSON.
Source: <https://cyclonedx.org/capabilities/mlbom/>

---

## 3. Papers that belong in limitations text

Named in `limitations` strings where a method was *not* implemented, with year and source. Verified
titles, accessed 30 September 2026. **None of these are implemented in CVAssure.**

| Method | Paper | Source |
|---|---|---|
| BadNets (patch attack; the family our patch trigger belongs to) | Gu et al., 2017 — *BadNets: Identifying Vulnerabilities in the Machine Learning Model Supply Chain* | <https://arxiv.org/abs/1708.06733> |
| Spectral Signatures | Tran, Li, Madry, 2018 — *Spectral Signatures in Backdoor Attacks* | <https://arxiv.org/abs/1811.00636> |
| Activation Clustering | Chen et al., 2018 — *Detecting Backdoor Attacks on Deep Neural Networks by Activation Clustering* | <https://arxiv.org/abs/1811.03728> |
| Neural Cleanse (the method our model stub names as a limitation) | Wang et al., 2019 — *Neural Cleanse: Identifying and Mitigating Backdoor Attacks in Neural Networks*, IEEE S&P 2019 | <https://people.cs.uchicago.edu/~ravenben/publications/abstracts/backdoor-sp19.html> |
| Fine-Pruning | Liu, Dolan-Gavitt, Garg, 2018 — *Fine-Pruning: Defending Against Backdooring Attacks on Deep Neural Networks* | <https://arxiv.org/abs/1805.12185> |
| Confident Learning | Northcutt, Jiang, Chuang, 2021 — *Confident Learning: Estimating Uncertainty in Dataset Labels*, JAIR | <https://arxiv.org/abs/1911.00068> |

The Neural Cleanse paper is not on arXiv; the author-hosted abstract page above is the source
that loaded. IEEE S&P 2019 is the venue, as recorded on that page.

---

## 4. The slide line

After the table, two sentences maximum, for the PPT owner:

> CVAssure is the offline command that turns training data, a model and inference records into one
> Finding object, links a model trigger to the contributor whose samples carry it, keeps a
> tamper-evident audit trail, and states plainly which attack classes it does not detect. The
> tools above each cover one part of that lifecycle; none of them produce the joined report.

Do not claim CVAssure beats any of them at their own job. It is a different artefact: an
assurance layer over three assets, not a detector library, a benchmark, or a signing standard.

---

## 5. What this changes in this repo

- No new dependency. Every tool above is a *comparison*, not an import. `import cvassure.core`
  still pulls only pydantic, PyYAML, jsonschema, typer, rich and numpy.
- Assumption A1 gets the citation list: TrojAI and BackdoorBench are references for attack
  families, and neither is installed or vendored.
- BackdoorBench's **non-commercial** licence is the concrete reason for that rule, and it is
  recorded in `configs/coverage_rules.yaml` as an assumption.
- The two dead URLs are removed, so no slide can cite a 404.