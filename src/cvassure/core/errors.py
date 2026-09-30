"""Typed exits. The CLI returns one of these and nothing else.

Every number here is in the plan's §7.4 table. A stage or detector failure must
be distinguishable from a policy failure, because "it did not work" and "it said
no" are different answers to a judge.
"""

from __future__ import annotations


class ExitCode:
    OK = 0
    USAGE = 2  # usage or config error
    DETECTOR = 3  # a detector or schema check failed
    VERIFY = 4  # audit log or report verification failed
    STUB = 5  # --strict and a stub ran
    FAIL_ON = 10  # --fail-on disposition was present


class CvassureError(Exception):
    """Base. Carries the exit code so the CLI never guesses."""

    exit_code = ExitCode.USAGE


class ConfigError(CvassureError):
    exit_code = ExitCode.USAGE


class DetectorsError(CvassureError):
    exit_code = ExitCode.DETECTOR


class VerificationError(CvassureError):
    exit_code = ExitCode.VERIFY


class StubRanError(CvassureError):
    exit_code = ExitCode.STUB


class FailOnTripped(CvassureError):
    exit_code = ExitCode.FAIL_ON


class BlockedOn(CvassureError):
    """A teammate artefact is missing. Printed as BLOCKED-ON: P<n>, exit 2."""

    def __init__(self, who: str, what: str) -> None:
        self.who = who
        super().__init__(f"BLOCKED-ON: {who} - {what}")
