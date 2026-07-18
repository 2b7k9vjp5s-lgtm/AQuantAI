"""Typed errors for the Industry Alpha ledger boundary."""


class EvidenceLedgerError(ValueError):
    """Base error for a rejected ledger operation."""


class EvidenceLedgerValidationError(EvidenceLedgerError):
    """A command violates an evidence or lifecycle rule."""


class EvidenceLedgerConflictError(EvidenceLedgerError):
    """A stable identity or revision conflicts with accepted history."""


class EvidenceLedgerImmutableError(EvidenceLedgerError):
    """Accepted ledger history was targeted for mutation."""


class EvidenceLedgerNotFound(EvidenceLedgerError):
    """A requested ledger identity does not exist."""


class EvidenceLedgerNotVisible(EvidenceLedgerError):
    """A case exists but has no revision visible at the requested cutoff."""
