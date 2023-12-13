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


# Todos:
- Readme updates
- Demo recording
- Add other workflows for reusable use in plugins/modules so they are managed in one central location. 
- Add optional step for when a js build is required (like in the ecommerce module).

## Potential Todos/Ideas:
- Flag to run for full matrix of WP versions.
- Flag to run for full matrix of PHP versions.
- Flag to only run this module's test vs all the plugin tests.
- Add a comment to the PR with links to the plugin zip files.
- Update the plugin versions with a beta tag or pass a new version number.