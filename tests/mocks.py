"""Type aliases for mocked Discord objects.

These are MagicMocks to the type checker, so tests can set attributes freely, but they
name what the mock stands in for."""

from unittest.mock import MagicMock

type MockGuild = MagicMock
type MockMember = MagicMock
