# Acceptance

- An authenticated owner streams supported media into tenant-owned storage and receives a canonical Asset v1 record only after verification.
- A second workspace cannot use the signed transfer or preview.
- An incomplete, oversized, mismatched-MIME, or invalid transfer fails before project mutation.
- The asset list and timeline reference survive runtime reconstruction.
- The browser exposes upload progress, cancellation, full-file retry, thumbnail/preview, timeline use, and safe archive.
- Duplicate active content reuses one verified asset record.
- Archive hides the library item without deleting original bytes or breaking canonical references.
- Studio typecheck/build, active OpenSpecs, Studio tests, and full repository regression pass before and after merge.
