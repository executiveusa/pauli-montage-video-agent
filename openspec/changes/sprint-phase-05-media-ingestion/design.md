# Design

The existing reservation/transfer/completion protocol remains authoritative. A reservation creates no canonical asset. The API streams an exact `Content-Length` to a temporary file, checks the reservation boundary, and passes the file to the selected object-storage adapter. Completion rechecks stored byte and checksum evidence before appending Asset v1 state. Matching active checksums reuse the existing asset and remove the redundant just-uploaded object.

The Next transfer proxy forwards the authenticated HTTP-only session and request stream without decoding media. Browser `XMLHttpRequest` supplies progress, cancellation, and full-file retry. Signed download requests produce short-lived same-origin preview paths. Archive is the only user-facing removal operation in this phase.

`asset.timeline.add` appends a media item to an appropriate canonical track only when that asset is not already present. Phase 7 owns the richer trim/split/move/reorder interaction.
