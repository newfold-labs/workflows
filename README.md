# Workflows
This repository houses reusable workflows tailored for the Newfold organization, specifically designed for tasks such as testing module changes within a plugin from a module pull request (PR). These workflows that must be referenced from a "caller" workflow within the repository, and they come with required inputs. For more details on workflows and reusable workflows, refer to [GitHub Actions documentation](https://docs.github.com/en/actions/using-workflows/reusing-workflows).

Currently, we are utilizing the `@main` ref, but the option to tag a `@v1` version exists for these workflows, allowing updates across the organization if the need arises.

## module-plugin-test

Caller workflows specify a particular workflow from this repository using the `uses` keyword and pass necessary inputs/parameters to it. There may be setup involved to gather required inputs. For example, with the `module-plugin-test` workflow, values like the branch name for the module to checkout and module and plugin repo references need to be passed in. Special attention to the `secrets: inherit` line is essential, as it allows the secrets available in the caller workflow to be accessible in the called reusable workflow.

For a comprehensive example, refer to the `brand-plugin-test.yml` file in most modules. Notably, the [Marketplace module workflow](https://github.com/newfold-labs/wp-module-marketplace/blob/main/.github/workflows/brand-plugin-test.yml) is fully set up. Here's a simplified example:

```yaml
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

  brand:
    name: Plugin Build and Test
    needs: setup
    uses: newfold-labs/workflows/.github/workflows/module-plugin-test.yml@main
    with:
      module-repo: ${{ github.repository }}
      module-branch: ${{ needs.setup.outputs.branch }}
      plugin-repo: 'org/wp-plugin-brand'
    secrets: inherit

...
```
### Options

#### module-repo
The `module-repo` input specifies the module to be considered in the tests and is a required input. Sending the `github.repository` value to the callable workflow suffices:
```
with:
      module-repo: ${{ github.repository }}
```

#### module-branch
The `module-branch` input indicates the branch in the module repo to be considered in the tests and is also required. An example step, set as a prerequisite with the `needs` property on subsequent tests, is shown below:
```
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
      module-branch: ${{ needs.setup.outputs.branch }}

```

#### plugin-repo
The `plugin-repo` input, also required, indicates the repository for the plugin. Each plugin for running tests needs its own step indicating the callable workflow in `uses` and the reference to the plugin repo. These plugin tests run in parallel once the setup step is complete:
```
  bluehost:
    name: Bluehost Build and Test
    needs: setup
    uses: newfold-labs/workflows/.github/workflows/module-plugin-test.yml@main
    with:
      plugin-repo: 'bluehost/bluehost-wordpress-plugin'
```

#### plugin-branch
The `plugin-branch`  input is optional and defaults to `main`. If needed to run tests on a different branch, this input can be added. For example, if module updates integrate with code in the plugin or another module that has already been merged, the `develop` or any `update/feature-name` branch can be targeted:
```
    plugin-branch: 'develop'
```
#### php-version
The optional input `php-version` input updates the version of PHP loaded for the workflow, currently set to a default of `8.1`. 

#### node-version
The optional input `node-version` input updates the version of Node loaded for the workflow, currently set to a default of `16.x`.

#### secrets
Ensure to include `secrets: inherit` to indicate that any secrets should be sent to the callable workflow.

### Flags
Several useful optional flags can be passed to this workflow when called.

#### only-module-tests
The `only-module-tests` input, defaulting to `false`, if set to `true` will only perform the cypress tests for specified module. This can help speed up development and debugging when tests are found to fail. It should always be removed in the PR so that the full plugin can be tested in case the code updates in question affect another part of the plugin. This input is merely to benefit engineers working on updates in a PR to fix a module test that has failed in the full test.

#### sync-npm-package
The `sync-npm-package` input, defaulting to `false`, is useful when the module also creates an npm package required by the plugin. When set to `true`, it runs a step to rsync the contents of the `build` directory in the module (in the vendor files) to the corresponding node package directory (in the node_modules files). Adjustments may be needed if there are file changes required for a complete build outside of the `build` directory. 

Refer to the [ecommerce module workflow PR](https://github.com/newfold-labs/wp-module-ecommerce/pull/192) for an example including this flag, as the module is also an installed npm package.


### Ideas for Improvement:
- Add a flag to signify tests should run in Cypress cloud for easier debugging (devise a way to pass the plugin level key).
- Add a flag to run for the full matrix of WP versions.
- Add a flag to run for the full matrix of PHP versions.
- Add a step that comments on the PR with links to all the plugin zip files.
- Update plugin versions with a beta tag or pass a new version number.
- Update with wp-cli command(s) to update site state before running tests. Useful for running tests in another language or region, such as a hostgator-latam environment.

## Other Workflows
While this repository is still relatively new, we plan to add additional reusable workflows for managing plugins/modules in one central location.