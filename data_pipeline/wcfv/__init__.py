"""
wcfv — World Cup Fantasy Value.

A data pipeline + model that estimates the fantasy value of every player at the
2026 FIFA World Cup. The package is organised into four stages that mirror the
flow of data:

    fetch/    – pull raw data from source (squads, FBref stats, groups, odds, prices)
    process/  – clean, consolidate and match that data into one tidy table
    model/    – turn stats + fixtures into expected fantasy points and value
    export.py – emit a single JSON file for the React front-end

Each stage writes its output to disk, so any stage can be re-run on its own
without repeating the (slow, network-bound) stages before it.
"""

__version__ = "1.0.0"
