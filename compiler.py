VERSION = '0.2.8-reconstructed'

# Explicit optional REA entrypoint: NOT connected to an ExecutionSpec producer.
# Until reconstructed compiler runtime exists, this does not imply auto-distribution.
def run_optional_rea_release(conn, payload, evidence, authorization, *,
                             issuer, issuer_key, destination_id, observer_id,
                             observer_key, dispatch, observe, enable_dispatch=False,
                             trusted_destination_resolver=None):
    """Manually invoke the governed REA pipeline; no publishing by default."""
    from contracts.rea_pipeline import run_governed_pipeline
    return run_governed_pipeline(
        conn, payload, evidence, authorization,
        issuer=issuer, issuer_key=issuer_key,
        destination_id=destination_id, observer_id=observer_id,
        observer_key=observer_key, dispatch=dispatch, observe=observe,
        enable_dispatch=enable_dispatch,
        trusted_destination_resolver=trusted_destination_resolver,
    )
