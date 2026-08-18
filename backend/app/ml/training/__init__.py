"""Training: config, sample derivation, losses, metrics and the job runner.

Losses and metrics are registries keyed by head-type id, exactly like the head
builders. The loop never branches on task.
"""
