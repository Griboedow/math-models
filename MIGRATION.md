# Repository migration

The `Griboedow/yarn-stand-simulator` repository was renamed to
`Griboedow/math-models` and organized into independent calculators on 2026-10-26.
The existing Git history was retained; this is the same repository.

| Previous location | Current location |
|---|---|
| Yarn calculator at the repository root | `yarn/stand-simulator/` |
| `3d-Models/vehicles/toy-physics/` | `vehicles/toy-physics/` in this repository |

The yarn move starts from commit
[`4915604`](https://github.com/Griboedow/math-models/commit/4915604a89a7d87a11100e28af8b31149ec13502),
including its toolpath mass/inertia reader. Its existing `yarnstand` module,
CLI and package name remain unchanged. Equations and saved numerical evidence
were not rewritten for the move.

Toy physics was imported from
[`3d-Models` commit `f72d8ed`](https://github.com/Griboedow/3d-Models/tree/f72d8ed3d98e1a19b67d4969089e6a80244e4c6c/vehicles/toy-physics).
All 33 tracked files were copied and compared byte for byte before updating
repository navigation and reproduction instructions. The source history remains
at that link. PLA/PETG profiles, equations, tests, inputs and saved numerical
results retain their values. The old folder contains a navigation README after
the migration, avoiding two independently edited calculators.

## Existing clones and branches

Update an existing clone's remote:

```sh
git remote set-url origin https://github.com/Griboedow/math-models.git
git fetch origin
```

Preserve any local work before integrating the new layout. Run yarn commands
inside `yarn/stand-simulator`; install that subdirectory if using the optional
package (`python -m pip install ./yarn/stand-simulator`). Root CI now runs each
calculator in its own working directory. Older branches and historical commits
still use their original layout until they incorporate the migration.

External CAD scripts that accept a simulator path should now receive the path
to `math-models/yarn/stand-simulator`. Legacy CAD scripts with a hard-coded
`yarn-stand-simulator` directory can use a local checkout at their pinned
historical commit, as described by their original reproduction instructions.
