# action-module-plugin-test
Action for testing module changes in a plugin. 

Use by doing something along these lines:

```
- uses: newfold-labs/workflows/.github/workflows/module-plugin-test.yml@main
  with:
    module-repo: 'newfold-labs/wp-module-marketplace'
    module-branch: 'feature/name'
    plugin-repo: 'newfold-labs/wp-plugin-hostgator'
```