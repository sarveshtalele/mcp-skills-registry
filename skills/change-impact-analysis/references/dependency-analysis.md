# Dependency Analysis Reference

## What is a Dependency Graph?

A dependency graph is a **directed acyclic graph (DAG)** where:

- **Nodes** represent source files / modules in the repository.
- **Edges** represent an `import` relationship: an edge from A → B means
  "module A imports module B", i.e. A depends on B.

```
users_controller.py  ──imports──▶  user_service.py
                                       │
                              ──imports──▶  user_repository.py
                                               │
                                      ──imports──▶  db_connection.py
```

## Reverse Graph (Impact Direction)

To answer "what is affected when file X changes?" we traverse the **reverse**
graph, following edges backwards:

```
db_connection.py  ◀── user_repository.py  ◀── user_service.py  ◀── users_controller.py
```

If `db_connection.py` changes, everything above it in the chain is potentially
affected — `user_repository.py`, `user_service.py`, and `users_controller.py`.

## Supported Languages

| Language   | Import syntax parsed |
|------------|----------------------|
| Python     | `import X`, `from X import Y` (AST-based, regex fallback) |
| JavaScript | `import ... from './path'`, `require('./path')` |
| TypeScript | Same as JavaScript + `.tsx` |
| Java       | `import com.example.SomeClass;` |
| C#         | `using MyApp.Services;` |
| Go         | `import "mymodule/package"` |

## Ignored Directories

The following directories are excluded from graph construction to prevent
noise from vendored code and build artifacts:

```
node_modules  .git  __pycache__  dist  build  bin  obj  vendor
.venv  venv  .tox  coverage  .pytest_cache  .mypy_cache  migrations
```

## Graph Traversal Algorithm

The `DependencyGraph.get_reverse_deps()` method implements iterative BFS
on the reverse-edge adjacency list:

```python
def get_reverse_deps(node, transitive=True):
    visited = set()
    queue = list(reverse_edges.get(node, []))
    while queue:
        current = queue.pop()
        if current not in visited:
            visited.add(current)
            if transitive:
                queue.extend(reverse_edges.get(current, []))
    return visited
```

**Complexity:** O(V + E) where V = nodes and E = edges in the subgraph
reachable from the changed file.

## Why Graph-Driven Analysis Is Powerful

| Property | Benefit |
|----------|---------|
| **Deterministic** | Same input → same output, every time |
| **Explainable** | Every impacted file has a traceable path back to the changed file |
| **Transitive** | Catches indirect dependencies that code review misses |
| **Language-agnostic** | Works across polyglot repositories |
| **Fast** | BFS on an in-memory adjacency list is sub-second even at 100k files |

## Limitations

- **Dynamic imports** (`importlib.import_module`, `require(variable)`) are not
  statically resolvable and will not appear as edges.
- **Circular dependencies** are handled safely (visited set prevents infinite loops).
- **Monorepos with build systems** (Bazel, Pants) may use a build-level dep graph
  that is more precise than import-level analysis — consider integrating the build
  graph for higher accuracy.
- **Cross-repository dependencies** (npm packages, Python packages) appear as
  external nodes only when they resolve to local files.
