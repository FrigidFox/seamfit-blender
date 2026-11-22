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
