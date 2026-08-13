# run state machine (MASTER_SPEC section 5) - pure unit tests, no DB/Docker
# needed. Covers the exact bug found live in Phase 13: REASONING must be able
# to go straight to COMPLETING when no review is required, not just to
# REVIEW_REQUIRED.
import pytest

from backend.app.services.state_machine import InvalidTransitionError, assert_valid_transition


def test_linear_happy_path_is_valid():
    path = [
        "CREATED", "VALIDATING", "PLANNING", "PLAN_READY", "QUEUED",
        "BROWSER_STARTING", "BROWSING", "EXTRACTION", "VALIDATING_DATA",
        "SNAPSHOTTING", "COMPARING", "REASONING", "COMPLETING", "COMPLETED",
    ]
    for prev, nxt in zip(path, path[1:]):
        assert_valid_transition(prev, nxt)


def test_reasoning_can_go_directly_to_completing_when_no_review_needed():
    # regression test for the bug found live in Phase 13: every early test
    # happened to trigger REVIEW_REQUIRED, so this path went unexercised
    # until a workflow completed without needing review.
    assert_valid_transition("REASONING", "COMPLETING")


def test_reasoning_can_still_go_to_review_required():
    assert_valid_transition("REASONING", "REVIEW_REQUIRED")


def test_review_required_can_only_reach_completing():
    assert_valid_transition("REVIEW_REQUIRED", "COMPLETING")


def test_branch_states_reachable_from_any_active_state():
    for state in ("BROWSING", "EXTRACTION", "COMPARING", "REASONING"):
        assert_valid_transition(state, "FAILED")
        assert_valid_transition(state, "CANCELLED")


def test_illegal_skip_ahead_is_rejected():
    with pytest.raises(InvalidTransitionError):
        assert_valid_transition("CREATED", "COMPLETED")


def test_illegal_backward_transition_is_rejected():
    with pytest.raises(InvalidTransitionError):
        assert_valid_transition("COMPLETED", "PLANNING")


def test_unknown_state_is_rejected():
    with pytest.raises(InvalidTransitionError):
        assert_valid_transition("CREATED", "NOT_A_REAL_STATE")


def test_completed_is_terminal():
    with pytest.raises(InvalidTransitionError):
        assert_valid_transition("COMPLETED", "REASONING")


def test_recovery_can_return_to_queued_or_fail():
    assert_valid_transition("RECOVERY", "QUEUED")
    assert_valid_transition("RECOVERY", "FAILED")


def test_plan_ready_can_skip_approval_when_not_required():
    assert_valid_transition("PLAN_READY", "QUEUED")


def test_plan_ready_can_await_approval_when_required():
    assert_valid_transition("PLAN_READY", "AWAITING_APPROVAL")
