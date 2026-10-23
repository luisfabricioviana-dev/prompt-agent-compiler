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


def run_optional_rea_github_release(conn, payload, evidence, authorization, *,
                                    issuer, issuer_key, destination_id, github_token,
                                    observer_id, observer_key, dispatch, observe,
                                    enable_dispatch=False, github_opener=None,
                                    expected_repository_id=None):
    """Resolve GitHub identity when dispatch is explicitly enabled.

    This is a manual integration entrypoint: caller-provisioned token and
    callback are required. No ExecutionSpec or automatic deployment is implied.
    """
    from contracts.rea_github_destination import resolve_github_destination
    resolver = None
    if enable_dispatch is True:
        if type(expected_repository_id) is not int or expected_repository_id <= 0:
            from contracts.rea_pipeline import PipelineResult
            return PipelineResult("BLOCKED", "trusted_repository_id_required", "")
        resolver = lambda: resolve_github_destination(
            destination_id, token=github_token, opener=github_opener,
            expected_repository_id=expected_repository_id)
    return run_optional_rea_release(
        conn, payload, evidence, authorization, issuer=issuer, issuer_key=issuer_key,
        destination_id=destination_id, observer_id=observer_id,
        observer_key=observer_key, dispatch=dispatch, observe=observe,
        enable_dispatch=enable_dispatch, trusted_destination_resolver=resolver)
