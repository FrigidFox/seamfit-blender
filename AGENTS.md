# Working on Seamfit

Start in the directory containing this file and the seamfit package. In the managed workspace this is /workspace/work. Read PLAN.md and PROGRESS.md, then run git status --short --branch, git log -5 --oneline and inspect the files relevant to the next open item. Reconcile the worktree with the log before changing anything. If work was interrupted between a change and a test, preserve it and test it. The checked-out code, recorded evidence and Git history govern the handoff.

## Working agreements

- Continue the existing roadmap. Keep changes small and explain a significant architectural change to the user before implementing it.
- Protect source assets. Fit evaluated copies, run the actual third-party weight-transfer operator on disposable targets, and verify bindings before presenting an export.
- Target Blender 5.1. The managed system blender is 4.3.2. Use the explicit 5.1 binary for verification. Keep scientific dependencies inside the test environment or the upstream add-on installation.
- After a meaningful milestone, update PROGRESS.md with the test conditions, outcome, failures, and next action. Stage only relevant source, test and documentation paths. Review git diff --cached --stat and commit verified work incrementally.
- Before ending a session, inspect git status, run the relevant tests, record remaining gaps and check that the distribution matches the tested tree. If interrupted mid-fix, leave the change in place and identify it as unverified. Preserve others' edits, including untracked files. Avoid destructive resets, cleaning commands and history rewrites.
- Keep installer ZIPs, test outputs, third-party code, dependencies and local Blender installations out of source commits. A Git bundle is the portable handoff for an environment without a remote.

## Code map

- seamfit/__init__.py contains the sidebar, guide picking, operator entry points and FBX export.
- seamfit/fit.py implements world-space landmark displacements, surface fitting, displacement smoothing and vertex checks.
- seamfit/session.py owns evaluated mesh snapshots, scene transitions, rollback, RWT integration and skin binding.
- seamfit/guides.py draws picked guide pairs in the viewport.
- seamfit/blender_manifest.toml declares the Blender extension and its minimum version.
- trial.py generates the original digitigrade example, then exercises fitting through FBX reimport. See PROGRESS.md for the last successful run.

- tests/recovery.py and tests/transforms.py open the generated example in a separate process and verify rollback, retry, binding and visibility.
- tests/guides_ui.py requires a graphical Blender process with --enable-event-simulate. Verify its PASS line in the log.
- README.md contains the user installation and fitting guide. Package only the seamfit directory as a Blender extension. Keep the project handoff separate from the installer.
