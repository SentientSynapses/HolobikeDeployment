# AthleteIdentity Repository Integration

## Source

- Repository: `id_kit/AthleteIdentity`
- Integration domain: `id`
- Source identity: an exact Git commit selected by a revision manifest under `Revisions/`

This directory owns AthleteIdentity's declarative deployment contract, not
adapter implementation, identity source, credentials, or athlete data.

## Deployables

`IdentityClient` reaches the device; `IdentityServer` reaches the estate. Both
halves of one contract, which is why the leaf names both — a composition that
pins one end of a wire and not the other cannot say what it deployed.

### `IdentityServer` builds a base image, and a base image does not deploy

The declared build is the one AthleteIdentity's own deployment README
documents, producing `athleteidentity-server:base`, saved to a tar so the
bundle carries bytes and `admit` has something to hash.

**That image is deliberately not runnable in production.** The repository says
so plainly: it "intentionally contains no device authenticator", and its
Terraform module will not create Cloud Run until `container_image` names a
derived image that has one. AthleteIdentity lists seven further items as
*project-owned* rather than its own — among them the derived image itself, a
reviewed device credential format with its manufacturing enrolment and
rotation procedure, provisioned registry entries, the athlete-facing pairing
approval experience, and operator procedures for revocation and key rotation.
None of them exists.

So what this repository can honestly do with `IdentityServer` today is build
its base image and record its digest. It cannot deploy it, and `provision
server` says so rather than attempting an apply against an image that does not
exist. Deriving the production image is not AthleteIdentity's to do and is not
packaging this repository may invent on its behalf; it is a decision the
project owes, and the release record will keep saying the estate half is
unbuilt until it is made.

## Assembly Contract

The leaf invokes AthleteIdentity's repository-owned IdentityClient build and
stages the service and CLI artifacts. Its serve/probe pair runs the staged
service from disposable profile state and proves health through the service's
wire protocol. Provider selection is non-secret configuration; provider
credentials are never declared data.

## Validation

The current host topology uses the filesystem key provider only beneath its
disposable emulation state and makes no production-provider claim. Production
acceptance requires the declared provider and transport, compatibility with the
HolobikeRider identity bridge, and proof that no credentials, refresh tokens,
private keys, or athlete records entered artifacts or reports.
