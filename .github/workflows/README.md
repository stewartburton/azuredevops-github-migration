This directory is intentionally kept empty.

The migration tool no longer stores or runs any GitHub Actions workflows inside its own repository.
All converted Azure DevOps pipelines should be committed ONLY to the destination repositories you are migrating to.

If you need an example verification workflow, copy `examples/verify-migration-workflow.yml` into the target repository's `.github/workflows/` directory.
