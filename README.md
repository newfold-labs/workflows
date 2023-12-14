# action-module-plugin-test
Reusable workflows for the newfold organization. These are used for things like testing module changes in a plugin from a module PR.


# Workflows
This repository hosts called workflows. They must be referred to from a "caller" workflow in the repository and have some required inputs. Learn more about workflows and reusable workflows: https://docs.github.com/en/actions/using-workflows/reusing-workflows

For now we're just using the `@main` ref, but we can tag a `@v1` version of these workflows to be updated across the org if the need arises (or a combination).

The caller workflows note a specific workflow in this repo that it `uses`, and passes any inputs/parameters to it. There may be some setup in order to gather required inputs. For example with the `module-plugin-test` workflow, we need to pass in a few values so the workflow can function. We need to determine the branch name for the module to checkout as well as the module and plugin repo references. Special note to the secrets: inherit line as this allows the secrets available in the caller workflow to be available in the called reusable workflow. 

For a full example see the [Marketplace module workflow](https://github.com/newfold-labs/wp-module-marketplace/blob/main/.github/workflows/brand-plugin-test.yml), but here's a simplified example:

```
...

jobs:
  setup:
    name: Setup
    runs-on: ubuntu-latest
    outputs:
      branch: ${{ steps.extract_branch.outputs.branch }}
    steps:

      - name: Extract branch name
        shell: bash
        run: echo "branch=${GITHUB_HEAD_REF:-${GITHUB_REF#refs/heads/}}" >> $GITHUB_OUTPUT
        id: extract_branch

  bluehost:
    name: Bluehost Build and Test
    needs: setup
    uses: newfold-labs/workflows/.github/workflows/module-plugin-test.yml@main
    with:
      module-repo: ${{ github.repository }}
      module-branch: ${{ needs.setup.outputs.branch }}
      plugin-repo: 'bluehost/bluehost-wordpress-plugin'
    secrets: inherit

...
```
# Flags
There are a few useful optional flags which can be passed to this workflow when called.

## only-module-tests
There is a `only-module-tests` input which if set to `true` (it defaults to `false`) will only perform the cypress tests for the module in question. This can help speed up development and debugging when tests are found to fail. It should always be removed in the PR so that the full plugin can be tested in case the code updates in question affect another part of the plugin. This input is merely to benefit engineers working on updates in a PR to fix a module test that has failed in the full test.

## sync-npm-package
There is also a `sync-npm-package` input. It is meant to assist when the module also creates an npm package which the plugin consumes. When set to `true` (it also defaults to `false`), it will run a step that will rsync the contents of the `build` dir in the module (in vendor dir) to the corresponding node package dir (in the node_modules). If there are file changes required for a complete build outside of the `build` dir, this step may need updating.

# Todos:
- Demo recording.

## Ideas for Improvement:
- Add other workflows for reusable use in plugins/modules to manage them in one central location.
- Add a flag to signify the tests should be run in cypress cloud for easier debugging (devise a way to pass the plugin level key).
- Add a flag to run for full matrix of WP versions.
- Add a flag to run for full matrix of PHP versions.
- Add a step that makes a comment on the PR with links to all the plugin zip files.
- Update the plugin versions with a beta tag or pass a new version number.
