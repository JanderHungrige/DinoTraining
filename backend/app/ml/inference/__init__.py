"""Running a frozen backbone plus trained or imported heads over images.

Wave 3's read path. Training lives in :mod:`app.ml.training`; the two share the head
registry, the decoders and the preprocessing plan, and share no code of their own.
"""
