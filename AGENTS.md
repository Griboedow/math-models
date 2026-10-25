# Repository conventions

Use English for repository documentation, code comments, generated labels and
GitHub content. Use the user's preferred language in conversation.

This repository is the canonical home for mathematical models and simulators.
Keep each calculator under its subject area, with a README in its own folder.
The root README is a short statement of purpose and a catalog, not a duplicate
of every calculator's manual. Update the catalog when adding or moving a model.

A calculator README must explain its purpose, scope, inputs and units, how to
run it, examples, tests and limits. Preserve the distinction between assumed,
supplier-derived and measured inputs, and between numerical checks and physical
validation. Do not alter historical numerical results merely to reorganize files.

Keep CAD and print kits in https://github.com/Griboedow/3d-Models. Link to their
exact revisions when needed. Do not vendor virtual environments, build outputs,
raw toolpaths, large meshes or duplicate simulator snapshots here.

Run each model's checks from its own folder. Keep root CI paths synchronized
with the directory structure. Preserve existing package and CLI names unless
the user asks to change them; a repository rename alone does not require that.
