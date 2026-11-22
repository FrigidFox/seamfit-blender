# Seamfit roadmap

Deliver a guided Blender 5.1 extension for fitting VRChat clothing to an avatar in bind pose, including non-human limb proportions. Deliver a usable first release and distinguish fixture results from named-avatar compatibility.

## Existing design

1. Setup selects one weighted body and one main garment, with optional extra selected clothing meshes. The user roughly aligns the garment and can pick paired surface landmarks directly in the viewport. An optional body vertex group restricts fit queries.
2. Preview creates evaluated mesh copies in an isolated scene. Landmark interpolation changes proportions. A world-space nearest-surface solve applies a clearance target, a bounded correction and optional inward pull. It smooths displacement over mesh edges. Users can inspect, edit, check and relieve the garment before weight transfer.
3. Finish stages disposable copies, calls SentFromSpaceVR's object.skin_weight_transfer, normalizes and limits deform weights to four, and binds each garment to an independent copy of the target bone hierarchy. A failed transfer returns to the fitting scene. A successful export scene contains only generated clothing and the armature.
4. FBX export uses the outfit and skeleton with animation baking and added leaf bones disabled. The original scene remains available.

## Decisions and limits

- The 5.1 test target is official Blender 5.1.2 on Linux. RWT is a separate installation. The upstream v1.1.9 release designates robust-weight-transfer-libigl26.zip for 5.1.
- Inputs are evaluated at their current shape-key mix and visible modifier state. Garment shape keys and modifier stacks are baked on output. UVs and material data travel with the evaluated mesh.
- The armature copy retains rest bones and hierarchy. The source rig's object animation, pose constraints and external controls are outside the export workflow.
- Face-normal vertex checks are local estimates. They can miss triangle crossings, open-surface ambiguities, layer collisions and clipping under animation. Visual and pose review remain part of the workflow.
- Region selection limits the geometric fit. RWT samples the full reference body.
- No Mayu, Novabeast or Nardoragon assets have been provided. Treat each as an open compatibility target.

## Milestones

| Milestone | Acceptance evidence | State |
| --- | --- | --- |
| Native workflow | Installable 5.1 extension, staged sidebar, adjustable fit, actual RWT invocation | Implemented |
| Export verification | Digitigrade fixture goes through weight transfer, deforms when posed, reimports from FBX with materials, UVs and bone hierarchy | Verified on generated fixture |
| Reliability and interface | Exercise failure recovery, retry, multi-piece input and sidebar stages on the packaged build | In progress |
| Distribution | Rebuild from verified source, provide starter scene and portable continuity checkpoint | In progress |
| Named avatars | Fit representative licensed garments to each named base, record settings, review rest and posed results | Requires assets and fit review |
