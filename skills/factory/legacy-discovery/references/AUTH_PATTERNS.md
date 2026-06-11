# Authentication & Access Control Pattern Reference

Copilot uses this reference when explaining the auth model detected in a codebase.

---

## The Three Models

### RBAC — Role-Based Access Control
> "What role do you have?" → determines what you can do.

Every user is assigned one or more **roles**. Access decisions check if the user's role
is in the allowed set. Roles are static labels defined at the application level.

**When to recognize it:**
- You see named roles like `"Admin"`, `"Manager"`, `"Editor"` in code
- Authorization checks are `isInRole()`, `hasRole()`, `Roles="…"`
- A role table or enum defines all possible roles

**Common patterns by framework:**

```csharp
// ASP.NET Core
[Authorize(Roles = "Admin,Manager")]
public IActionResult ManageOrders() { }

if (User.IsInRole("Admin")) { /* elevated action */ }
```

```java
// Spring Security
@PreAuthorize("hasRole('ADMIN')")
public void deleteUser(Long id) { }

@Secured({"ROLE_ADMIN", "ROLE_MANAGER"})
public void updateSettings() { }
```

```python
# Flask-Principal / Flask-Login
@login_required
@roles_required("admin")
def admin_dashboard():
    pass

# Django
@permission_required("myapp.can_publish")
def publish_article(request):
    pass
```

```typescript
// Node / Express / NestJS
@UseGuards(RolesGuard)
@Roles("admin", "manager")
async updateProduct() { }
```

---

### ABAC — Attribute/Policy-Based Access Control
> "What attributes do you (and the resource) have?" → determines access.

Access decisions evaluate **attributes** — user attributes (department, clearance),
resource attributes (owner, classification), and environmental attributes (time, IP).
Policies combine these attributes with boolean logic.

**When to recognize it:**
- Named policies like `"CanEditOrder"`, `"SameRegion"`, `"PublishedOnly"`
- Claims inspection: `ClaimTypes.Department`, `user.claims`
- Authorization requirements: `IAuthorizationRequirement`, `AuthorizationPolicy`

**Common patterns by framework:**

```csharp
// ASP.NET Core policy-based
[Authorize(Policy = "CanEditOrder")]
public IActionResult EditOrder(int id) { }

// Policy registration (usually in Startup.cs / Program.cs)
services.AddAuthorization(options =>
{
    options.AddPolicy("CanEditOrder", policy =>
        policy.RequireClaim("Department", "Sales", "Operations"));
    options.AddPolicy("SeniorOnly", policy =>
        policy.RequireAssertion(ctx =>
            int.Parse(ctx.User.FindFirstValue("YearsOfService") ?? "0") >= 5));
});
```

```java
// Spring @PreAuthorize with SpEL expression
@PreAuthorize("hasPermission(#orderId, 'Order', 'EDIT')")
public void updateOrder(Long orderId) { }

@PostAuthorize("returnObject.owner == authentication.name")
public Order getOrder(Long id) { }
```

```python
# Django object permissions
class OrderPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.department == request.user.department
```

---

### ReBAC — Relationship-Based Access Control
> "What is your relationship to this resource?" → determines access.

Access depends on whether the user has a specific **relationship** to the resource being
accessed — e.g. owner, collaborator, team member, parent object accessor.

**When to recognize it:**
- Ownership checks: `order.UserId == currentUser.Id`, `IsOwner(resource, user)`
- Relationship lookups: `HasPermissionOnResource(user, resource)`
- Google Zanzibar style: tuples `(user, relation, object)` stored in DB

**Common patterns:**

```csharp
// ASP.NET Core ownership check
public async Task<IActionResult> Edit(int id)
{
    var order = await _orderRepo.GetAsync(id);
    if (order.UserId != User.GetUserId())
        return Forbid();
    // ...
}

// Resource-based authorization handler
public class OrderAuthHandler : AuthorizationHandler<EditRequirement, Order>
{
    protected override Task HandleRequirementAsync(
        AuthorizationHandlerContext ctx,
        EditRequirement req,
        Order resource)
    {
        if (resource.OwnerId == ctx.User.GetUserId())
            ctx.Succeed(req);
        return Task.CompletedTask;
    }
}
```

```java
// Spring + custom permission evaluator
@PreAuthorize("hasPermission(#order, 'EDIT')")
public void updateOrder(Order order) { }

// Inside PermissionEvaluator:
public boolean hasPermission(Authentication auth, Object target, Object permission) {
    if (target instanceof Order) {
        return ((Order) target).getOwnerId().equals(auth.getName());
    }
    return false;
}
```

```python
# Django guardian (per-object permissions)
@permission_required_or_403("orders.change_order", (Order, "pk", "pk"))
def edit_order(request, pk):
    pass
```

---

## Hybrid Models

Real projects often combine models:

| Combination | Description | Example |
|-------------|-------------|---------|
| RBAC + ABAC | Role gates coarse access; policy fine-tunes it | `[Authorize(Roles="Employee", Policy="SameRegion")]` |
| RBAC + ReBAC | Role gates entry; ownership check gates edit | Admin can view all; regular user only views their own |
| All three | Enterprise pattern | Admin (RBAC) → Policy check (ABAC) → Ownership (ReBAC) |

---

## Security Observations to Report

When analysing auth, always look for:

1. **Inconsistent enforcement** — some controllers have `[Authorize]`, others don't
2. **Sensitive routes without guards** — `/admin/*`, `/api/users`, `/payments/*` without auth
3. **Over-permissive roles** — single `Admin` role with no granularity
4. **Missing ABAC** — business rules enforced ad-hoc in code instead of via policies
5. **No ReBAC** — users can potentially access other users' resources if IDs are guessable
6. **Hard-coded roles** — roles defined as string literals scattered in code vs. centralized enum
