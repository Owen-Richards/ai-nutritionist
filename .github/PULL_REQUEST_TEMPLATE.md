# Pull Request

## 📋 Description

Brief description of the changes and the problem they solve.

Fixes #(issue)

## 🔄 Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 Documentation update
- [ ] 🧹 Code cleanup/refactoring
- [ ] ⚡ Performance improvement
- [ ] 🔒 Security improvement

## 🧪 Testing

- [ ] Unit tests pass
- [ ] Integration tests pass (mock AWS via moto where applicable)
- [ ] Manual testing completed (include steps or evidence)
- [ ] Performance impact assessed (note any hotspots)

**Test Coverage:**
- [ ] New tests added for new functionality
- [ ] Regression tests added for any bug fixes
- [ ] Coverage unchanged or improved; above project threshold (≥ 80%)

## 📸 Screenshots (if applicable)

Add screenshots or GIFs demonstrating the changes.

## 🔍 Code Review Checklist

### AI/Architecture Guardrails
- [ ] No public API changes in `src/core/*` without deprecation path
- [ ] Service boundaries respected (`src/services/*/`), no cross‑service coupling
- [ ] Dependency Injection used; wired via `packages/core/src/container/*`
- [ ] Repository pattern used for persistence; no direct SDK calls in services
- [ ] Pydantic models and type hints added/updated; async I/O for AWS calls
- [ ] Adapters used for AWS integrations; events bus used where appropriate

### Security
- [ ] No hardcoded secrets or credentials
- [ ] Input validation implemented
- [ ] Error handling doesn't expose sensitive information
- [ ] Dependencies are up to date

### Performance
- [ ] No unnecessary database calls
- [ ] Efficient algorithms used
- [ ] Memory usage considered
- [ ] Lambda cold start impact minimized

### Code Quality
- [ ] Code follows project style guidelines
- [ ] Functions are well-documented
- [ ] Complex logic is commented
- [ ] No dead code or TODO comments

### Contracts and APIs (if applicable)
- [ ] Contract tests updated (`tests/contracts/*`) for schema/API changes
- [ ] OpenAPI/AsyncAPI specs updated in `docs/api-reference/*`
- [ ] Backward compatibility maintained; versioning/deprecation noted

## 🚀 Deployment

- [ ] Infrastructure changes documented
- [ ] Migration scripts provided (if needed)
- [ ] Rollback plan considered
- [ ] Environment variables updated

### Infrastructure (Terraform)
- [ ] `terraform fmt -check` passes for modified files
- [ ] `terraform validate` passes in `infrastructure/terraform`
- [ ] No unintended changes to prod settings; env separation preserved

## 📚 Documentation

- [ ] README updated (if applicable)
- [ ] API documentation updated
- [ ] Changelog updated
- [ ] Comments added to complex code

### Observability & Safety
- [ ] Structured logging added where new flows were introduced
- [ ] Rate limiting/feature flags considered where appropriate
- [ ] Privacy/compliance implications assessed; audit logging intact

## ✅ Final Checklist

- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published

## 🔗 Related Issues

Link any related issues or pull requests:

- Related to #
- Depends on #
- Blocks #

---

## 🧰 Validation Commands (paste outputs if relevant)

```bash
# Lint + tests
make ci

# Coverage
make test-cov

# Terraform validation (if TF changed)
cd infrastructure/terraform && terraform fmt -check && terraform validate
```
