# IEEE S&P 2026 Accepted Papers — LLM/Agent/AI-Security Subset

**Status:** Working survey, compiled 2026-09-02. Scope, per explicit user instruction, is
**only** the LLM/agent/AI-security-relevant subset of IEEE S&P 2026 (47th IEEE Symposium
on Security and Privacy) accepted papers — not the full accepted-papers list.

**Discovery method and its limits.** The official accepted-papers pages
(`sp2026.ieee-security.org/accepted-papers.html` and the `www.ieee-security.org/TC/SP2026/`
mirror) could not be fetched directly across repeated attempts in this session — every
attempt failed with a `robots.txt fetch failed: ConnectTimeout` error, which looks like a
transient site-level connectivity issue rather than a real robots.txt block (other pages on
the same domain, e.g. CFP pages, surfaced fine in search snippets). Because of this, the
paper list below was assembled indirectly: targeted web searches for the string "Accepted
to IEEE Symposium on Security and Privacy 2026" (the exact acceptance note several of these
papers carry on arXiv) combined with LLM/agent/security keywords, cross-checked against
individual lab/author publication pages (Purdue PurSec, Duke, CMU CyLab) that independently
list their group's S&P 2026 acceptances. **This is very unlikely to be the complete set** —
it is what surfaced through this indirect discovery path, not an exhaustive crawl of the
program. Treat the list as a partial, evidence-backed sample, not a census.

**Relevance to LLM-DoW-Bench:** none of the papers found below propose a cost/token/dollar
amplification metric, a Denial-of-Wallet framing, or a multi-agent delegation-cost benchmark.
This is consistent with (does not contradict) the project's existing novelty claims in
`CLAUDE.md` §6 / `threat-model.md` §5 — logged here as an additional data point, not proof of
absence (see the discovery-method caveat above).

---

## 1. Investigating the Impact of Dark Patterns on LLM-Based Web Agents

- **arXiv:** [2510.18113](https://arxiv.org/abs/2510.18113)
- **Authors:** Devin Ersoy, Brandon Lee, Ananth Shreekumar, Arjun Arunasalam, Muhammad Ibrahim, Antonio Bianchi, Z. Berkay Celik (Purdue PurSec Lab)
- **Venue confirmation:** arXiv comments field states "Accepted to IEEE Symposium on Security and Privacy 2026"; independently listed on the Purdue PurSec lab publications page.

**Abstract (paraphrased from the paper):** As LLM-based web agents automate online tasks,
they may encounter dark patterns — deceptive UI designs that traditionally manipulate human
users into unintended decisions. The paper asks whether these same patterns work against
autonomous agents. It introduces **LiteAgent**, a framework that captures comprehensive
agent–browser interaction logs, and **TrickyArena**, a controlled testbed embedding 14
documented dark patterns across e-commerce, streaming, and news site clones. Evaluating six
popular agents across three LLM backbones, the study finds agents fall victim to a single
dark pattern roughly 41% of the time, that *higher-performing* agents are, counterintuitively,
more vulnerable, and that combining visual-design tricks with multiple simultaneous patterns
increases susceptibility further.

**Methodology:**
1. *TrickyArena construction* — four React-based websites (one per popular site category),
   each with 14 selectively-togglable dark patterns drawn from a documented taxonomy, so
   individual and combined-pattern conditions can be isolated.
2. *LiteAgent instrumentation* — an agent-agnostic harness that launches the agent under
   test, injects JS listeners to capture clicks/scrolls/keystrokes, and produces both a
   structured action trace and a screen recording.
3. *Agent Action Validator* — automated, logic-based checks against the action database to
   score task completion and dark-pattern susceptibility, cross-checked by manual video
   review for verification.

**Voice/writing profile:** Frames the contribution around a *transferred-risk* narrative
("X is a known human-targeted threat; does it also work on agents?") rather than proposing an
entirely new attack primitive — motivation section leans on prior HCI/dark-pattern literature
before pivoting to agents. Strong empirical framing throughout (headline numbers — "41%",
"six agents", "three LLMs" — appear in the abstract itself, not held for the results section).
Contribution list is explicit and enumerated (framework, testbed, empirical findings,
implications for defenses) — a common S&P house style. Threat model and defenses are treated
lightly; the paper is primarily a measurement study, with "implications for defense" left as
future work rather than a designed-and-evaluated defense.

**Relevance to LLM-DoW-Bench:** Methodologically close in *shape* (agent-agnostic harness +
purpose-built testbed + automated-plus-manual scoring), useful as a structural precedent for
how to justify a testbed-plus-harness contribution to an S&P-adjacent audience. Not
cost/DoW-relevant in content — it measures task-outcome manipulation, not resource
amplification.

---

## 2. When AI Meets the Web: Prompt Injection Risks in Third-Party AI Chatbot Plugins

- **arXiv:** [2511.05797](https://arxiv.org/abs/2511.05797)
- **Authors:** not yet independently verified — the only author attribution found in this
  session traces to a third-party blog summary of the paper, which is not a reliable primary
  source for authorship and is **not** treated as verified here. `\needsdata{}`-equivalent:
  re-verify authors directly from the arXiv abstract page or PDF before citing.
- **Venue confirmation:** arXiv comments field itself states "Accepted to IEEE Symposium on
  Security and Privacy 2026" (seen directly in WebFetch output from the abstract/HTML pages).

**Abstract (paraphrased):** A large-scale empirical study of 17 third-party AI chatbot
plugins deployed across more than 10,000 websites. Two vulnerability classes are documented:
(1) eight plugins (serving roughly 8,000 sites) do not protect conversation-history
integrity, letting an attacker forge conversation histories — including fake system messages
— to amplify prompt-injection attacks by a reported 3–8x; (2) fifteen plugins integrate
context-enrichment tools (e.g., web scraping) without distinguishing trustworthy site content
from untrusted third-party material, creating indirect-injection exposure — roughly 13% of
studied e-commerce sites had already exposed their chatbots to such untrusted third-party
content in the wild.

**Methodology:** Ecosystem-scale empirical audit (17 plugins, 10,000+ site deployments) with
controlled follow-up experiments varying system-prompt architecture and the underlying LLM to
isolate which design choices drive the vulnerability. Findings are organized by severity tier
(low through critical) and by exploitation vector (content injection via descriptions,
review/comment poisoning, navigation-triggered payloads, cross-plugin propagation).

**Voice/writing profile:** Ecosystem-measurement style typical of applied-security S&P
papers — leads with scale ("10,000+ websites") as the headline credibility signal, then
narrows to mechanism. Severity taxonomy and vector taxonomy both explicit and named, which
is a recurring structural pattern across these S&P 2026 papers (compare to TrickyArena's
14-pattern taxonomy above and PromptLocate's attack taxonomy below) — worth noting as a house
convention this project's own paper could mirror when presenting the V1–V6 vector taxonomy.

**Relevance to LLM-DoW-Bench:** Directly adjacent — this is exactly the kind of
"conversation-history/content amplification" mechanism the project's C1 (tool-result content
control) capability formalizes, but applied to plugin ecosystems rather than agent
delegation, and measured as an attack-success/exposure metric rather than a cost-ratio
metric. Worth a `\needsdata{}`-flagged mention in Related Work once authorship is verified.

---

## 3. PromptLocate: Localizing Prompt Injection Attacks

- **arXiv:** [2510.12252](https://arxiv.org/abs/2510.12252)
- **Authors:** Yuqi Jia, Yupei Liu, Zedian Shao, Jinyuan Jia, Neil Zhenqiang Gong
- **Venue confirmation:** arXiv comments field: "To appear in IEEE Symposium on Security and
  Privacy, 2026" (verified directly via WebFetch of the abstract page).

**Abstract (paraphrased):** Prompt injection attacks contaminate an LLM's input data with an
injected prompt (injected instruction + injected data) to hijack the model onto an
attacker-specified task. Localizing *where* the injection lives within contaminated data
matters for forensics and data recovery, but is largely unexplored. The paper proposes
**PromptLocate**, the first dedicated localization method, via a three-step pipeline: (1)
split contaminated data into semantically coherent segments, (2) identify segments
contaminated by injected instructions, (3) pinpoint segments contaminated by injected data.
Evaluated against eight existing and eight adaptive attacks, with accurate localization
reported across both.

**Methodology:** Segmentation-then-classification pipeline; evaluated against a
deliberately broad attack corpus (8 existing + 8 adaptive/adversarial variants) to test
robustness against attackers who know a localizer is present — an adaptive-attacker
evaluation discipline.

**Voice/writing profile:** Narrow, single-mechanism contribution paper (a forensic tool, not
a benchmark or measurement study) — title states the contribution as a gerund noun phrase
("Localizing X"), consistent with a common S&P/CCS naming convention for tool papers. Framing
emphasizes a *gap* claim ("despite its growing importance, ... remains largely unexplored")
before presenting the method — structurally similar to how this project's own gap claims
(CLAUDE.md §6.7) are framed, useful as a stylistic precedent.

**Relevance to LLM-DoW-Bench:** Low direct relevance (forensics/localization, not cost or
availability). Useful primarily as evidence that prompt-injection *mechanism*-level papers
remain an active, well-represented S&P 2026 category — supports the claim that this project's
threat model (built on standard indirect prompt injection, per `threat-model.md` §2.3) rests
on a still-active, not stale, attack primitive.

---

## 4. GraphRAG under Fire

- **arXiv:** [2501.14050](https://arxiv.org/abs/2501.14050)
- **Authors:** Jiacheng Liang, Yuhui Wang, Changjiang Li, Rongyi Zhu, Tanqiu Jiang, Neil
  Gong, Ting Wang
- **Venue confirmation:** listed as an S&P 2026 acceptance on a co-author's (Duke, Z. Gong)
  institutional publications page; not yet independently cross-checked against the arXiv
  comments field itself (a WebFetch pass on the abstract page did not surface a venue note in
  the returned excerpt) — treat venue as **probable, not fully confirmed**, and re-verify
  directly from the PDF before citing in `paper/main.tex`.

**Abstract (paraphrased, low confidence pending full re-verification):** GraphRAG
structures external knowledge as multi-scale knowledge graphs to improve retrieval-augmented
generation. The paper introduces **GragPoison**, a poisoning attack that exploits shared
relations within the knowledge graph, reported to achieve up to 98% attack success while
poisoning less than 68% of the relevant text.

**Methodology (partial, low confidence):** Graph-structure-aware poisoning attack targeting
the relation-sharing property specific to GraphRAG (as opposed to flat-index RAG); evaluated
by attack success rate against poisoning-budget fraction.

**Voice/writing profile:** Title follows an aggressive, informal "X under Fire" naming
convention distinct from the more literal/descriptive titles above — notable stylistic
outlier among this set; worth being aware of as one end of the acceptable-title-tone range at
this venue, though this project's own paper should likely stay closer to the descriptive end
given its measurement/benchmark framing.

**Relevance to LLM-DoW-Bench:** Not directly relevant (retrieval poisoning for output
manipulation, not cost/availability). Flagged mainly because it is the one paper in this set
targeting a specific *architecture* (GraphRAG) rather than agents/plugins in general — a
reminder that this project's own threat model should stay explicit about which agent
architectures (LangGraph tool-use, specifically) it does and doesn't generalize to.

---

## 5. Incalmo: An Autonomous LLM-Assisted System for Red Teaming Multi-Host Networks

- **arXiv:** [2501.16466](https://arxiv.org/abs/2501.16466)
- **Authors:** Brian Singer, Keane Lucas, Lakshmi Adiga, Meghna Jain, Lujo Bauer, Vyas Sekar
  (CMU)
- **Venue confirmation:** listed directly on CMU CyLab's "CyLab researchers to present at
  IEEE S&P 2026" news page, and a CMU-hosted PDF mirror is filed under a `papers/2026/` path
  named `sp2026-incalmo.pdf`.

**Abstract (paraphrased):** Asks whether LLMs can autonomously execute multi-host red-team
exercises against enterprise networks. Finds that existing LLM-based offense systems
(PentestGPT, CyberSecEval3) fail at this task. Introduces **Incalmo**, which has the LLM plan
at the level of high-level declarative tasks, executed by separate domain-specific task
agents (a planner/executor split), with supporting services tracking compromised assets
across the attack chain. Evaluated on **MHBench**, a new benchmark of 40 emulated networks
(22–50 hosts each): Incalmo achieves 37/40 successful critical-asset compromises versus 3/40
for baselines, completing within 12–54 minutes at reportedly minimal cost.

**Methodology:** (1) baseline failure analysis of existing LLM-offense tools on multi-host
scenarios; (2) Incalmo system design — LLM-as-strategic-planner + specialized task agents as
executors, an explicit planner/executor architectural split; (3) **MHBench** benchmark
construction (40 emulated networks at varying scale) as the evaluation vehicle; (4) head-to-
head comparison against baselines on success rate, wall-clock time, and (per the abstract)
cost.

**Voice/writing profile:** Of all six papers found, this is the closest structural sibling to
LLM-DoW-Bench's own contribution shape: (a) identify that existing tools/benchmarks
underserve a specific LLM-agent capability (multi-host planning under Incalmo; multi-agent
delegation-cost amplification under this project), (b) build a named, reusable benchmark
(MHBench / this project's corpus), (c) build a system with an explicit multi-agent
architecture (planner + domain task agents / root + sub-agents), (d) report head-to-head
metrics against baselines including **wall-clock time and cost** — i.e., a peer S&P 2026
paper already treats "cost" as a first-class reported metric for a multi-agent LLM system,
even though it does not treat cost as an *attack objective* the way this project does. Title
follows a "named-system: descriptive-subtitle" convention (like TrickyArena/LiteAgent above).

**Relevance to LLM-DoW-Bench:** High structural relevance, low content overlap. Confirms (i)
S&P reviewers are receptive to "new named benchmark + new named system + baseline comparison"
papers in the LLM-agent space, and (ii) multi-agent planner/executor architectures with
explicit sub-agent delegation are an established, reviewer-legible design pattern at this
venue — directly useful precedent for how `harness.py`'s planned root/sub-agent design
(CLAUDE.md §6.6a's Ling et al. cross-framework-realism note) could be framed for a
submission. Should be added to Related Work as a "benchmark-methodology precedent," distinct
from the existing "Concurrent Work" cost-amplification citations (Zhou et al., SkillBloat,
LeechHijack, CORBA) which are content-adjacent rather than structure-adjacent.

---

## 6. PILOT: Command-line Interface Fuzzing via Path-Guided, Iterative Large Language Model Prompting *(tangential — LLM-as-tool, not LLM-as-target)*

- **Authors:** Momoko Shiraishi, Yinzhi Cao, Takahiro Shinagawa
- **arXiv ID:** not yet located/verified in this session.
- **Venue confirmation:** found via a University of Tokyo lab news page announcing the S&P
  2026 acceptance directly (not yet cross-checked against arXiv).

**Abstract (paraphrased):** Proposes PILOT (Path-guided, Iterative LLM-Orchestrated
Testing), which combines LLMs with program call-path information from static analysis to
generate semantically meaningful CLI options and input files for fuzzing. Found 51 previously
unknown vulnerabilities across 43 real-world CLI programs (33 fixed, 3 assigned CVEs).

**Why flagged tangential rather than excluded:** this paper uses an LLM as an *instrument*
for finding traditional software vulnerabilities — it is not about attacking or securing LLM
agents themselves, so it sits outside this project's actual threat model. Included only
because it technically satisfies "LLM paper accepted at S&P 2026"; **not recommended for
citation** in `paper/main.tex` unless a specific need arises (e.g., illustrating the breadth
of "LLM+security" work at the venue).

---

## Papers found but excluded as not LLM/AI-security-relevant

- **International Students and Scams: At Risk Abroad** (Katherine Zhang, Arjun Arunasalam,
  Pubali Datta, Z. Berkay Celik) — confirmed accepted to S&P 2026 via full-text fetch, but is
  a mixed-methods human-subjects study of scam victimization with no AI/LLM component.
  Excluded per the user's explicit scoping to "just LLM/agent/AI-security papers."

## Candidates seen but not yet resolved

- **Systems Security Foundations for Agentic Computing** (Christodorescu, Fernandes, Hooda,
  Jha, Rehberger, Chaudhuri, Fu, Shams, Amir, Choi, Choudhary, Palumbo, Labunets, Pandya) —
  arXiv:2512.01295. Highly topically relevant (bridges AI-safety and systems-security framing
  for agentic systems, 11 case studies of real attacks) but **venue not confirmed** — the
  fetched arXiv page did not show an S&P 2026 acceptance note, and it may be a position
  paper/preprint rather than an accepted S&P paper. Do not cite as an S&P 2026 paper without
  re-verifying directly.

---

## Cross-paper observations (for this project's own S&P/SaTML framing)

1. **Taxonomy-first structure is a house convention.** Every content-relevant paper above
   (dark patterns, chatbot plugins, PromptLocate) leads with an explicit, named taxonomy
   (14 dark patterns; severity tiers x exploitation vectors; instruction-vs-data
   localization) before presenting results. `threat-model.md`'s V1–V6 / C1–C2 taxonomy
   already follows this pattern — reinforces that the existing structure is venue-appropriate
   and should stay prominent in the paper's own presentation.
2. **Scale and headline numbers go in the abstract, not just results.** All three empirical
   papers put their key quantitative finding (41%, 10,000+ sites/3–8x, 98%/68%) directly in
   the abstract. `paper/main.tex`'s abstract should be checked against this convention once
   real experimental numbers exist (per the `\needsdata{}` discipline already in place —
   no placeholder numbers should appear there regardless).
3. **Cost/wall-clock reporting as a baseline-comparison axis is already normalized** (Incalmo
   reports both), which is independent supporting evidence — beyond the literature already
   logged in `CLAUDE.md` §6 — that a paper centering cost/token/dollar metrics as its primary
   axis (rather than a secondary efficiency footnote) is a legitimate, reviewer-legible move
   at this venue, not a category mismatch.
4. **None of the six confirmed papers propose a cost-ratio or Denial-of-Wallet-style metric.**
   This is a negative result from a necessarily partial search (see the discovery-method
   caveat at the top) and should not be cited in the paper as "no S&P 2026 paper does this" —
   only logged internally as one more data point consistent with the project's existing
   novelty claims.

## Open follow-ups

- Verify author list for paper 2 (chatbot plugins, arXiv:2511.05797) directly from the arXiv
  page/PDF, not the blog secondary source currently cited above.
- Verify venue confirmation for paper 4 (GraphRAG under Fire) directly from the arXiv
  comments field or PDF, not only the Duke publications-page listing.
- Locate the arXiv ID for paper 6 (PILOT) if it is ever needed for citation.
- Resolve venue status for "Systems Security Foundations for Agentic Computing"
  (arXiv:2512.01295) before treating it as an S&P 2026 paper.
- This list should be treated as a lower bound. A more exhaustive pass would require either
  the official accepted-papers page becoming reachable (retry periodically — the failures
  looked transient) or a much larger set of targeted keyword searches (e.g., "watermarking,"
  "membership inference," "model extraction," "tool poisoning," "MCP," "agent hijacking,"
  none of which were tried in this session).
