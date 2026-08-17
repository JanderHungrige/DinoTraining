"""Head types: the registry contract, and (from feature 3) their implementations.

`registry` deliberately imports no torch. The API layer, compatibility checks and the
catalogue importer all need to reason about head types without paying a multi-second
torch import or loading a model.
"""
