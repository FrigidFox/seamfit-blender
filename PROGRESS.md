# Development record

## November 21, 2026 — Blender 5.1 baseline

The workspace began without a Git repository or project documentation. The existing implementation is under /workspace/work/seamfit. Git is initialized in /workspace/work because /workspace/.git is a read-only mount. No existing tracked history was present. Build products remain in the adjacent output directory.

Verified with the official Blender 5.1.2 Linux release, build ec6e62d40fa9, and the upstream libigl26 ZIP from RWT release v1.1.9. The included upstream add-on identifies itself internally as 1.1.8. Test dependencies were libigl 2.6.1, robust-laplacian 1.1.0 and SciPy 1.16.3. All were isolated in work/rwt-deps.

- The 1,008-vertex gaiter started with 489 vertices behind the local body surface and the preview reported zero. The real RWT operator finished. The resulting scene contained one mesh and one rig.
- Verified per-vertex weights summed to one within 0.00001 with at most four influences. Bending Hock.L deformed the mesh. FBX reimport retained four named bones, the mesh binding, one UV set and three material slots. Source vertex coordinates stayed unchanged.
- Blender's extension builder and validator accepted seamfit-0.1.0.zip. Installed the ZIP with the 5.1 CLI in a clean profile, launched Blender again and confirmed the registered extension, scene settings and sidebar class.
- The initial end-to-end trial preceded the latest guide-overlay and small-accessory changes. Re-run it against the packaged build. Missing-dependency detection was separately verified with the upstream dependency operator registered.

### Resume here

Exercise the packaged build on the example, including transfer rollback and retry, multiple garments, landmark alignment and viewport layout. Update this record after those checks. Rebuild and hand off the installer, example and Git bundle.

From /workspace/work, run the following for the baseline in this environment.

    OPENBLAS_NUM_THREADS=1 ./blender-5.1.2-linux-x64/blender -b --factory-startup --python-exit-code 1 --python trial.py
    ./blender-5.1.2-linux-x64/blender --command extension build --source-dir seamfit --output-dir ../output
    ./blender-5.1.2-linux-x64/blender --command extension validate ../output/seamfit-0.1.0.zip

The test fixture is original generated geometry. Named avatar testing, Unity/VRChat import, other operating systems, large-outfit timings and human usability testing remain open.

## November 21, 2026 — Installed-build recovery checks

Repeated the one-garment pose and FBX round trip from the installed ZIP in the clean 5.1.2 profile. Added tests/runtime.py to resolve the installed extension and real upstream solver, with a source-checkout fallback. The fixture script now resolves its own directory. Added tests/recovery.py and ran it with SEAMFIT_REQUIRE_INSTALLED=1.

Invalid region and posed-rig inputs produced actionable errors. Two selected pieces were fitted with a guide pair. Moving the second piece two Blender units away made the real upstream solver fail after transferring the first piece. Object, mesh, armature and scene counts returned to their pre-attempt values. Both preview pieces still had their original empty weight sets. Moving the piece back and retrying produced the two garments and rig with normalized weights. Return to source succeeded.

Native UI automation reached all three panel stages. The first framebuffer captures were black, so visual layout verification is still pending. Continue by inspecting the alternate X11 captures, correcting any evidenced layout issue, and refreshing the package and handoff.

## November 21, 2026 — Native UI and transformed-avatar verification

Inspected actual X11 captures of Setup, Review and Export. Stacked the two object-picker labels to avoid truncation at the default sidebar width. Preview and output meshes now have distinct names, and transfer errors identify the affected garment with a retry action. Added checks for a changed review rig and for hidden or unselectable outfit objects at export.

The rebuilt ZIP installed in the isolated Blender 5.1.2 profile. The example and two-piece rollback tests passed again. tests/transforms.py verified evaluated body shape-key mix on a translated, rotated and nonuniformly scaled rig, matching world-space output in bind pose and refusal to write an incomplete FBX with a hidden garment. tests/guides_ui.py drove two native viewport mouse clicks on the example and verified creation, redraw and removal of their guide pair. The first guide-test assertion incorrectly subtracted Blender property arrays; converting those arrays to vectors corrected the test and the rerun passed.

Added installation, example, fitting and recovery instructions in README.md. The next step is to verify the distribution and portable Git checkpoint, then continue with representative avatar asset testing when licensed inputs are available.

## November 21, 2026 — Distribution checkpoint

The release installer was rebuilt from the current extension sources, validated, installed into the isolated profile and exercised by the fixture, recovery, transformed-avatar and native-guide checks. The distributed Hock-gaiter.blend reopened in Blender 5.1.2 with Digitigrade leg and Trail gaiter preselected in Setup. Packaging is local. There is no configured Git remote.

Release fingerprints:

    ad963bcb1b65408b13c13221b99e6ecaa0e639b6d5058a10c47fe33f975a65bf  seamfit-0.1.0.zip
    f56878c517606b05fbf696210d08acb6caffe589ddcec9c660b242c6caf7834c  Hock-gaiter.blend

### Reproduce the installed-build checks

From the repository root, set BLENDER to the official 5.1 executable. The following commands use the existing managed-workspace profile. On a fresh machine, enable RWT and its dependencies in that profile, or put the extracted robust-weight-transfer-libigl26 folder inside the directory named by SEAMFIT_RWT_PARENT and point SEAMFIT_RWT_DEPS to its Blender-compatible Python libraries. The defaults are ./upstream and ./rwt-deps. The original sources are the Blender release archive and the RWT v1.1.9 GitHub release named in README.md.

    BLENDER=./blender-5.1.2-linux-x64/blender
    export BLENDER_USER_RESOURCES="$PWD/clean-profile"
    export SEAMFIT_REQUIRE_INSTALLED=1 OPENBLAS_NUM_THREADS=1
    "$BLENDER" --command extension build --source-dir seamfit --output-dir ../output
    "$BLENDER" --command extension validate ../output/seamfit-0.1.0.zip
    "$BLENDER" --command extension install-file --repo user_default --enable ../output/seamfit-0.1.0.zip
    "$BLENDER" -b --python-exit-code 1 --python trial.py
    "$BLENDER" -b --python-exit-code 1 --python tests/recovery.py
    "$BLENDER" -b --python-exit-code 1 --python tests/transforms.py
    "$BLENDER" --enable-event-simulate Hock-gaiter.blend --python tests/guides_ui.py

Each test prints PASS on completion. The graphical test requires a display. The recovery test deliberately emits upstream errors for the induced failed transfer before its successful retry. The output ZIP is an installer. The development archive contains the tracked source tree and a full Git bundle. Extract it and use the clone command in README.md to restore history.

### Handoff

Start with AGENTS.md, git status and git log. The next product milestone is validation against representative licensed avatar/garment pairs and Unity import, as specified in PLAN.md. Report any regression on the original example separately from asset-specific fit tuning. Named avatars, other platforms and broad user testing remain unverified. The managed workspace exposes the delivered files in /workspace/output.

## November 21, 2026 — Illustrated workflow guide

Added review and pose-test instructions to README.md. Delivered Seamfit-Workflow.pdf in the output directory with three illustrated pages covering Setup, Review and Export. Checked control names against the panel, used the existing Blender 5.1.2 screenshots and verified the PDF has three pages with extractable text through the final scope note. The extension code and installer were unchanged. The next product milestone remains representative avatar and Unity validation.
