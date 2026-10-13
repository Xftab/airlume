"""Natural-language layer: question -> typed ViewIntent -> validated query.

The language model only ever fills the `ViewIntent` form (schema.py).
It never writes SQL or code. Dates are resolved by `resolve.py` in code.
"""
