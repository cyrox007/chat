"""Operational worker entrypoints for PubChat.

Workers are invoked by an external scheduler/process. They are intentionally not
started from the FastAPI lifespan so multiple web workers do not each create
independent background schedulers.
"""
