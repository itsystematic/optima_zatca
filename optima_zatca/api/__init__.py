"""The HTTP surface the onboarding interface talks to.

Split by concern: :mod:`onboarding` holds the whitelisted methods,
:mod:`serialise` turns Optima ZATCA's documents into the wire shapes the client
expects, :mod:`validation` holds the field rules, :mod:`guidance` the explainer
copy, and :mod:`runner` drives the certificate chain in the background.
"""
