# Phase 08 Design

`StudioProject.assets` remains canonical. Binary objects live in a replaceable `ObjectStorage` adapter. Upload is a reservation/transfer/completion protocol: reserve an asset ID and signed transfer, write and verify bytes, then atomically add a validated Asset v1 record. Local storage is owner-safe; S3-compatible storage is optional and server-configured.
