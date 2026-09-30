"""Exit codes for the CLI.

A detector failure, a verification failure, and a policy hit use different codes.
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
    """A required component is missing. Exit 2."""

    def __init__(self, who: str, what: str) -> None:
        self.who = who
        super().__init__(what)
