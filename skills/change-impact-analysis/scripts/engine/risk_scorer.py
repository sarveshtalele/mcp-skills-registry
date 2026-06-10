"""
Risk Scorer
Produces a deterministic 0-100 deployment risk score by weighing six independent
factors.  Each factor has a fixed maximum contribution so the total caps at 100.

Factor weights
--------------
1. Change volume      — up to 20 pts  (number of directly changed files)
2. Transitive spread  — up to 20 pts  (how many modules are impacted)
3. API contract       — up to 25 pts  (breaking contract violations)
4. Module type risk   — up to 20 pts  (DB/API/config changes)
5. Sensitivity        — up to 10 pts  (security / financial code touched)
6. Consumer breadth   — up to  5 pts  (number of downstream apps)
"""
from typing import Any, Dict, List


RISK_ACTIONS: Dict[str, str] = {
    "LOW":      "Safe to deploy. Standard release pipeline applies.",
    "MEDIUM":   "Deploy with monitoring. Notify on-call team before release.",
    "HIGH":     "Requires senior engineer review + documented rollback plan.",
    "CRITICAL": "Block deployment. Escalate to tech lead. Full regression suite required.",
}


class RiskScorer:
    def score(
        self,
        impact: Dict[str, Any],
        contract_violations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        factors: List[Dict[str, Any]] = []
        total = 0

        # 1. Change volume (max 20)
        file_count = len(impact.get("changed_files", []))
        if file_count == 0:
            pts = 0
        elif file_count <= 5:
            pts = 4
        elif file_count <= 10:
            pts = 8
        elif file_count <= 20:
            pts = 14
        else:
            pts = 20
        total += pts
        factors.append({"factor": "change_volume", "points": pts, "detail": f"{file_count} files changed"})

        # 2. Transitive spread (max 20)
        transitive = impact.get("transitive_impact_count", 0)
        pts = 20 if transitive > 50 else (14 if transitive > 20 else (8 if transitive > 10 else min(transitive // 2, 6)))
        total += pts
        factors.append({"factor": "transitive_spread", "points": pts, "detail": f"{transitive} modules transitively affected"})

        # 3. API contract violations (max 25)
        breaking = [v for v in contract_violations if v.get("severity") == "breaking"]
        pts = min(25, len(breaking) * 10)
        if pts:
            total += pts
            factors.append({"factor": "breaking_api_changes", "points": pts, "detail": f"{len(breaking)} breaking contract change(s)"})

        # 4. Module type risk (max 20)
        modules = impact.get("impacted_modules", [])
        module_types = {m["module_type"] for m in modules}
        type_pts = 0
        if "database" in module_types:
            type_pts += 10
            factors.append({"factor": "database_schema_change", "points": 10, "detail": "Database / migration files affected"})
        if "api_endpoint" in module_types:
            type_pts += 6
            factors.append({"factor": "api_surface_change", "points": 6, "detail": "API endpoint files affected"})
        if "config" in module_types:
            type_pts += 4
            factors.append({"factor": "configuration_change", "points": 4, "detail": "Config / infrastructure files affected"})
        total += min(20, type_pts)

        # 5. Sensitivity (max 10)
        all_risk_factors = [rf for m in modules for rf in m.get("risk_factors", [])]
        if "security_sensitive" in all_risk_factors:
            total += 5
            factors.append({"factor": "security_sensitive", "points": 5, "detail": "Auth / security code in blast radius"})
        if "financial_critical" in all_risk_factors:
            total += 5
            factors.append({"factor": "financial_critical", "points": 5, "detail": "Payment / billing code in blast radius"})

        # 6. Consumer breadth (max 5)
        consumers = len(impact.get("consumer_apps", []))
        pts = min(5, consumers)
        total += pts
        factors.append({"factor": "consumer_breadth", "points": pts, "detail": f"{consumers} consumer application(s) affected"})

        score = min(100, total)
        level = self._level(score)

        return {
            "score": score,
            "level": level,
            "action": RISK_ACTIONS[level],
            "factors": factors,
        }

    @staticmethod
    def _level(score: int) -> str:
        if score <= 30:
            return "LOW"
        if score <= 60:
            return "MEDIUM"
        if score <= 80:
            return "HIGH"
        return "CRITICAL"
