# Changelog

All notable curriculum-documentation changes in this repo should be recorded here.

## Unreleased

## [0.0.6] - Organizing Team update 

### Changed

- Updated the onboarding site registration CTAs to reflect that registration is closed, including the navbar button and hero button, plus a disabled/closed visual treatment in [docs/index.html](docs/index.html) and [docs/assets/site.css](docs/assets/site.css).
- Aligned the team section in [docs/index.html](docs/index.html) added Myk Ogbinar (Founder, DEP), Simonee Ezequiel (Communications), and Bea Lambitco (Content Curator). Renamed groups to Content Curators, Squad Team, and Mentors Team. Corrected role titles across Ops, Communications, Squad, and Mentors. Rebuilt the Admissions panel to match the documented crossover (Katherine Bulac, James David Bradly Carballo, Anam Iqbal). Removed Vanie Bermudez and Renan Matthew Fajardo.
- Further team adjustments: added Jomai Hizon and Kim Audrey Magan to Ops; removed Yui Otsuka and Renzi Vidal from Mentors Team; swapped Zierd Ethan for Vanie Bermudez in Squad Team; renamed Community to Moderators and added Renan Matthew Fajardo.
- Added Zierd Ethan and Andrei Marcus to Curriculum; removed Simonee Ezequiel from Communications.

## [0.0.5] - Site General Improvements

### Changed

- Refreshed the GitHub Pages onboarding site styling in [docs/](docs/): stronger editorial hierarchy, subtler canvas texture, layered card shadows, branded hero panel treatment, and DEP logo usage in the header.
- Expanded the visual language further with a dark hero, gold/navy accents, animated glow layers, and scroll-reveal cards across the onboarding page.
- Replaced the redundant hero fact panel with cohort-focused notes, improved output-card contrast, and widened the FAQ so questions no longer feel clipped.

## [0.0.4] - Submission System Design & Curriculum Restructure

### Added

- Added [CONTEXT.md](CONTEXT.md) defining domain terms and the full participant submission flow: Starter Kit, Milestone Submission (GitHub Issue), Auto-Check (GitHub Action), Milestone Reviewer verdict (`passed` / `needs-improvement`), and Resubmission model.

### Changed

- Restructured phase layout: Phase 2 trimmed to weeks 5–6; Phase 3 expanded to weeks 7–12 (SQL and data modeling moved from Phase 2).
- Moved `week-07` and `week-08` from `02-data-collection/` into `03-data-processing/`.
- Populated all 24 week READMEs with topics, primary and optional resources, build tasks, and deliverables.
- Rewrote Phase 5 as a conditional dual-path: Path A (predictive/ML) and Path B (advanced EDA and stakeholder track).
- Updated all phase READMEs with revised milestone timing, pass criteria, and gate enforcement.
- Updated `docs/MILESTONE_CHECKLIST.md` with hard gate notes on M0 and M1, revised milestone timing, and separate Path A / Path B criteria for M5.
- Updated tech stack diagram (SVG) with corrected week ranges, SQL added to Phase 3, scikit-learn added to Phase 5.
- Updated [README.md](README.md) to reflect Program Overview: added Program Design section (duration, weekly rule, design principles, resource rule, tool stack), split Phase 5 into separate Path A and Path B rows in the curriculum table, added analysis notebook to primary outputs, and fixed Starter Kit link to point to [cohorts/starter-kit/](cohorts/starter-kit/).
- Fixed [06-deployment/week-23/README.md](06-deployment/week-23/README.md) milestone label from `Milestone 5 / 6` to `Milestone 5` — week 24 is the sole M6 deliverable.

## [0.0.3] - Static Site Preliminary

### Added

- Added a dependency-free GitHub Pages onboarding site under [docs/index.html](docs/index.html), with static CSS and JavaScript assets in [docs/assets/](docs/assets/).
- Added cohort-facing sections for registration, program positioning, selection and onboarding flow, expected outputs, responsible AI use, organizing team, and FAQs.

## [0.0.2] - Leveraging AI Guide

### Added

- Added [docs/AI_GUIDE.md](docs/AI_GUIDE.md) as a cohort-facing reference for responsible AI use, example prompts, and assessment support.

### Changed

- Added AI support notes to [01-foundations/README.md](01-foundations/README.md) and [docs/FAQ.md](docs/FAQ.md).
- Added week-specific sample AI prompts to [01-foundations/week-01/README.md](01-foundations/week-01/README.md) through [01-foundations/week-04/README.md](01-foundations/week-04/README.md).

## [0.0.1] - Learner Support / Reference templates

### Added

- Added learner-facing guidance blocks to all weekly curriculum files from Week 1 through Week 24.
- Added a consistent `Learner Support` section structure to each weekly README:
  - `Starter Script / Template`
  - `How To Adapt This To Your Project`
  - `Definition of Done`
  - `Common Mistakes`
  - `If You're Stuck After 2 Hours`

### Changed

- Expanded [01-foundations/week-01/README.md](01-foundations/week-01/README.md) and [01-foundations/week-02/README.md](01-foundations/week-02/README.md) with problem-framing and data-source documentation templates.
- Expanded [01-foundations/week-03/README.md](01-foundations/week-03/README.md) with repo setup, folder structure, and first-commit guidance.
- Expanded [01-foundations/week-04/README.md](01-foundations/week-04/README.md), [02-data-collection/week-05/README.md](02-data-collection/week-05/README.md), and [02-data-collection/week-06/README.md](02-data-collection/week-06/README.md) with ingestion scaffolds for API, scraping, and manual-download paths.
- Expanded [03-data-processing/week-07/README.md](03-data-processing/week-07/README.md) through [03-data-processing/week-12/README.md](03-data-processing/week-12/README.md) with schema, SQL, transform, validation, and pipeline-run-order guidance.
- Expanded [04-analysis-and-insights/week-13/README.md](04-analysis-and-insights/week-13/README.md) through [04-analysis-and-insights/week-16/README.md](04-analysis-and-insights/week-16/README.md) with notebook outlines for summary statistics, charting, inference, and insight writing.
- Expanded [05-project-packaging/week-17/README.md](05-project-packaging/week-17/README.md) through [05-project-packaging/week-20/README.md](05-project-packaging/week-20/README.md) with learner scaffolds for both Path A (predictive) and Path B (non-predictive).
- Expanded [06-deployment/week-21/README.md](06-deployment/week-21/README.md) through [06-deployment/week-24/README.md](06-deployment/week-24/README.md) with dashboard planning, deployment, documentation-polish, QA, and demo-script support.

### Notes

- The added examples are scaffold-level only and use placeholders such as `<your_source_url>` and `<your_kpi_name>` so learners are guided without being handed finished project answers.
