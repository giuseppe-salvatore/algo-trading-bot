# Commit Message Conventions

This repository follows conventional commit message standards with specific length requirements.

## Title (Subject Line)

- **Length**: 50-72 characters (aim for ~50, hard limit 72)
- **Format**: `<type>[optional scope]: <description>`
- **Style**: 
  - Use imperative mood ("fix bug" not "fixed bug" or "fixes bug")
  - Capitalize first letter
  - No period at end

**Examples:**
- ✅ `fix(ci): match justfile install pattern for workspace deps`
- ✅ `feat(auth): add OAuth2 support`
- ✅ `docs: update installation guide`
- ❌ `fix(ci): match justfile install pattern to ensure workspace dependencies are installed` (too long)

## Body

- **Length**: Wrap lines at 72 characters
- **Separator**: Blank line between title and body
- **Style**:
  - Use imperative mood
  - Explain what and why, not how (code shows how)
  - Use bullet points for multiple changes
  - Wrap text at 72 characters per line

**Example:**

```
fix(ci): match justfile install pattern for workspace deps

Use pdm install followed by explicit workspace package installations
to ensure all workspace dependencies are properly installed.

- Install dependencies for each workspace package
- Fixes ModuleNotFoundError for 'requests' module
- Ensures transitive dependencies are resolved
```

## Commit Types

- `fix`: Bug fix
- `feat`: New feature
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semicolons, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `ci`: CI/CD changes
- `build`: Build system changes

## Scope (Optional)

Use scope to indicate which part of the codebase is affected:
- `(ci)`: CI/CD workflows
- `(auth)`: Authentication
- `(api)`: API changes
- `(ui)`: User interface
- Package or module names

## Configuration

This repository uses a Git commit template (`.gitmessage`) to help maintain these conventions.

To use the template automatically, run:
```bash
git config commit.template .gitmessage
```
