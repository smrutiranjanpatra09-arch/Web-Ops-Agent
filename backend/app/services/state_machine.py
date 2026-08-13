from backend.app.models.run import RUN_STATES

# allowed forward transitions per MASTER_SPEC section 5. Branches (RECOVERY,
# RERUN_REQUESTED, FAILED, CANCELLED) are reachable from most active states.
TERMINAL_STATES = {"COMPLETED", "FAILED", "CANCELLED"}
BRANCH_STATES = {"RECOVERY", "RERUN_REQUESTED", "FAILED", "CANCELLED"}

_LINEAR_ORDER = [
    "CREATED", "VALIDATING", "PLANNING", "PLAN_READY", "AWAITING_APPROVAL", "APPROVED", "QUEUED",
    "BROWSER_STARTING", "BROWSING", "EXTRACTION", "VALIDATING_DATA", "SNAPSHOTTING", "COMPARING",
    "REASONING", "REVIEW_REQUIRED", "COMPLETING", "COMPLETED",
]

_ALLOWED: dict[str, set[str]] = {}
for i, state in enumerate(_LINEAR_ORDER[:-1]):
    _ALLOWED[state] = {_LINEAR_ORDER[i + 1]} | BRANCH_STATES
_ALLOWED["COMPLETED"] = set()
_ALLOWED["PLAN_READY"] = {"AWAITING_APPROVAL", "QUEUED"} | BRANCH_STATES  # skip approval when not required
_ALLOWED["REASONING"] = {"REVIEW_REQUIRED", "COMPLETING"} | BRANCH_STATES  # skip review when not required
_ALLOWED["REVIEW_REQUIRED"] = {"COMPLETING"} | BRANCH_STATES
for b in BRANCH_STATES:
    _ALLOWED[b] = set()
_ALLOWED["RECOVERY"] = {"QUEUED", "BROWSER_STARTING", "FAILED"}
_ALLOWED["RERUN_REQUESTED"] = {"CREATED"}


class InvalidTransitionError(ValueError):
    pass


def assert_valid_transition(current: str, target: str) -> None:
    if current not in RUN_STATES or target not in RUN_STATES:
        raise InvalidTransitionError(f"Unknown state in transition {current} -> {target}")
    if target not in _ALLOWED.get(current, set()):
        raise InvalidTransitionError(f"Illegal transition {current} -> {target}")
