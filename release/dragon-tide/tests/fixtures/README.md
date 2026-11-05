# Save compatibility baselines

These are synthetic representative records of the v3.68.0 serialization format, not player data or captured playthroughs. Fixture-only challenge/tree/evolution identifiers intentionally exercise preservation of opaque records.

Keep these baselines when adding new save versions. Add migration cases rather than simply replacing old fixtures to make tests pass. Tests execute the game's actual storage loaders and writers; they do not prove that `resumeRun()` can reconstruct every historical world. In particular, `fallen` is indexed by the generated settlement array, so changes to world generation require a separate compatibility decision even when `RUN_SAVE_VERSION` stays unchanged.
