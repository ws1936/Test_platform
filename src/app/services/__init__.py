"""Application-level utility services.

Modules in this package provide stateless helpers that are *not*
domain-specific. ``variable_substitutor`` lives here because variable
substitution is used by the API test engine (F008) but is also a
generic string utility that does not depend on the database, HTTP
layer, or any single domain entity.
"""