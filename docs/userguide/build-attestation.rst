Build Attestation
=================

kas supports the generation of SLSA / in-toto build attestation data.
Currently, support for the following attestation formats is implemented:

- `provenance v1 <https://slsa.dev/spec/v1.0/provenance>`_

Provenance
----------

The provenance data provides information about the build. This includes
data about the build environment, as well as all primary (first-level)
dependencies. The attestation will be stored in
``attestation/kas-build.provenance.json``

The following modes are supported: ``mode=min``, ``mode=max``, whereby
the mode controls the amount of information that is included in the
attestation. The CLI options hereby loosely follow the ``docker buildx``
provenance options, which are described in detail in
`Provenance attestations <https://docs.docker.com/build/attestations/slsa-provenance/>`_.
For compatibility with the ``docker buildx`` CLI options, we also support
``--provenance true``, which is equivalent to ``--provenance mode=min``.

In min mode, the provenance attestation will contain information about:

- Build timestamps
- Build materials (project-config files)
- Source repositories and revisions
- Build platform

In max mode, it will also contain the build environment, i.e. all
environment variables of the ``env`` section along with their values.

.. warning::
    In max mode, the provenance attestation captures all environment
    variables specified in the ``env`` section. Make sure to not expose
    any secrets.

For example, to build the configuration described in the file
``kas-project.yml`` and emit provenance attestations, you could run::

    kas build --provenance mode=max kas-project.yml

Working with sigstore cosign
----------------------------

The `cosign tool <https://github.com/sigstore/cosign>`_ from the `sigstore
project <https://www.sigstore.dev/>`_ (`documentation <https://docs.sigstore.dev/>`_)
has native support for in-toto build predicates. However, it currently can only
operate directly on the predicate but not on the enclosing attestation
(cosign 2.2.4). By that, the predicate first needs to be extracted (provenance
in this example)::

    cat build/attestation/kas-build.provenance.json | jq '.predicate' > provenance.json

Attestation Signing
~~~~~~~~~~~~~~~~~~~

.. warning::
    The following command operates on the public append-only transparency
    log. Make sure to understand the implications before executing.

The following example shows how to create a signed build attestation
from a provenance predicate and a local artifact, using the OIDC keyless
signing workflow:

.. code-block:: sh

    cosign attest-blob \
        --type=slsaprovenance1 \
        --predicate=provenance.json \
        --output-signature=kas-build.dsse.json \
        --output-certificate=cert.pem \
        <image>.wic

.. note::
    Currently the attestation can only be created for a single artifact file.

For later verification, both the signed attestation (``kas-build.dsse.json``),
as well as the certificate (``cert.pem``) are needed. Make sure to
ship them along with the artifact.

Attestation Verification
~~~~~~~~~~~~~~~~~~~~~~~~

The previously signed blob can be verified again:

.. code-block:: sh

    cosign verify-blob-attestation \
        --certificate=cert.pem \
        --signature=kas-build.dsse.json \
        --certificate-identity="<redacted>" \
        --certificate-oidc-issuer="<oidc issuer>" \
        --type=slsaprovenance1 \
        <image>.wic

Attestation Restoration
~~~~~~~~~~~~~~~~~~~~~~~

The dsse record (``kas-build.dsse.json``) contains the original
attestation data as base64 encoded string. To restore the attestation,
run::

    cat kas-build.dsse.json | jq -r '.payload' | base64 -d | jq
