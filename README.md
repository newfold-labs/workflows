# action-module-plugin-test
Action for testing module changes in a plugin. 

Use by doing something along these lines:

```
- uses: newfold-labs/action-module-plugin-test/.github/workflows/main.yml@main
  with:
    module-repo: 'newfold-labs/wp-module-marketplace'
    module-branch: 'feature/name'
    plugin-repo: 'newfold-labs/wp-plugin-hostgator'
```