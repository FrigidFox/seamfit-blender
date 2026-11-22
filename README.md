# Seamfit for Blender 5.1

Fit clothing to a rigged VRChat avatar, transfer skin weights with SentFromSpaceVR’s Robust Weight Transfer, and export a clothing-only FBX with the target skeleton.

**[Download the Blender installer](https://raw.githubusercontent.com/FrigidFox/seamfit-blender/downloads/seamfit-0.2.0.zip)** · [Illustrated workflow guide](https://github.com/FrigidFox/seamfit-blender/blob/downloads/Seamfit-Workflow-0.2.0.pdf) · [Example Blender scene](https://raw.githubusercontent.com/FrigidFox/seamfit-blender/downloads/Hock-gaiter.blend)

## Fitting shorts

Choose **Avatar body** and **Clothing**, roughly position the waistband and leg openings, and click **Fit clothing**. The default keeps loose fabric in place while pushing out clipping. In Review, use **Fix clipping** if the check finds intersections. Click **Recheck fit** after manual edits. When the waistband, crotch and hems look right, choose **Bind clothing to rig**, then **Export clothing FBX**.

The fitted copy keeps the source garment’s indexed vertices, edges and face loops. Subdivision Surface is skipped when obtaining the garment’s original cage. Other modifiers that change connectivity trigger a message before the fit proceeds. The body reference still uses its visible surface. The current garment shape-key mix is baked. A new fit from the source is required for the topology checks when updating an older review scene.

## First fitting

1. In Blender 5.1, open Edit → Preferences → Get Extensions. In the top-right menu, choose **Install from Disk** and select seamfit-0.2.0.zip.
2. Install the author's **robust-weight-transfer-libigl26.zip** for Blender 5.1. Follow the dependency installation prompt in its **SENT** sidebar and restart Blender if prompted. [Upstream download](https://github.com/sentfromspacevr/robust-weight-transfer/releases/tag/v1.1.9) · [Author's tutorial](https://jinxxy.com/SentFromSpaceVR/robust-weight-transfer)
3. Open Hock-gaiter.blend to try the included digitigrade example, or open your avatar in its bind pose. In the 3D Viewport press **N**, then open **Seamfit**. The example already has its body and clothing assigned.
4. On your own avatar, choose the target body mesh and garment. The body needs one enabled Armature modifier with deform weights. Place the clothing roughly around the corresponding body part. For a multi-piece outfit, open **More fit options**, enable **Include other selected meshes** and check the displayed list.
5. Click **Fit clothing**. Orbit the model and inspect the silhouette, cuffs and seams. Use **Recheck fit** to flag vertices inside the body and corners of clothing faces that cross it. Enter Edit Mode to see or adjust flagged vertices. Return to Object Mode and check again.
6. Click **Bind clothing to rig**. Seamfit runs RWT and checks each vertex for normalized deform weights with up to four influences. In the export scene, pose-test the clothing, return the armature to its rest pose and choose **Export clothing FBX**. **Return to source** takes you back to the original file's working scene.

## Reviewing and pose-testing the result

In Review, a local poke-through can often be corrected with **Body clearance** and **Fix clipping**. Check intersections again after each adjustment. If an entire sleeve or pant leg follows the wrong body part, use **Return to source**, adjust its placement or add guides, and generate a new preview. The new preview starts from the source garment, so finish broad alignment before editing individual vertices in Review.

In the export scene, select the armature and enter Pose Mode. Rotate a joint under the garment, such as the hock in the example. Watch for fabric stretching toward a neighboring limb. Undo the test rotation and return to Object Mode. Keep the outfit visible and selectable when you click **Export clothing FBX**.

## Fitting a different silhouette

For a digitigrade leg, place guide pairs near the knee, hock and cuff. Open **More fit options → Alignment guides**, click **Pick guide pair**, click the location on the garment, then click its intended location on the body. Orbit between clicks when needed. Each click raycasts the requested mesh, so overlapping objects can be picked. The overlay labels paired points A and B. Add a pair on the other side of a limb when the fit needs to change its width.

Use **More fit options** to adjust clearance, pull loose fabric closer or limit how far a correction can travel. Reduce inward pull for skirts, flares and baggy sleeves. If a tail or neighboring limb attracts the fit, choose a body vertex group under **Fit region**. It needs enough contiguous faces for their vertices to have group weights of at least 0.25. For large pose or proportion differences, align the garment first and preview again.

The source scene keeps its assets. The fitted garment takes the current shape mix, UVs and materials from the verified garment cage. Garment morphs are baked at their current mix. Make mesh edits in Review before transfer. The check uses the full reference body. Inspect near contacts, self-intersections and layers visually. Inspect the fit from multiple angles and in a representative pose. Materials referencing external images still need those textures when moving the FBX to another project.

## If transfer stops

The review scene keeps your fitted meshes after a failed transfer. Check the named garment for loose pieces far from the body. Adjust alignment or open **Adjust fit or transfer** and change **Match distance**, then retry. If the SENT tab requests dependencies, complete that installation first. A rig currently in a pose must be set to **Rest Position** in Armature Data Properties before previewing.

## Continuing development

Start with AGENTS.md, PLAN.md and PROGRESS.md. If you have the portable Git bundle, run the following in the folder where you saved it.

    git clone seamfit-history.bundle seamfit-development
    cd seamfit-development
    git status --short --branch
    git log -5 --oneline

The Blender extension builder packages the seamfit directory. The example and test outputs are regenerated by trial.py. See PROGRESS.md for commands and verified scope.
