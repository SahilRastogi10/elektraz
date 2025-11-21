import numpy as np, pandas as pd
import pyomo.environ as pyo

def build_milp(cands: pd.DataFrame,
               demand_nodes: pd.DataFrame,
               dist_km: np.ndarray,
               pred_daily_kwh: np.ndarray,
               equity_score: np.ndarray,
               safety_penalty: np.ndarray,
               grid_penalty: np.ndarray,
               site_capex: np.ndarray,
               pv_capex_per_kw: float,
               storage_capex_per_kwh: float,
               params: dict):
    """
    cands: DataFrame with columns [cand_id, lat, lon, utility, in_afc, ...]
    demand_nodes: DataFrame with columns [node_id, pop_weight] (e.g., ZCTA centroids)
    dist_km: (I x J) distances from candidates to demand nodes
    pred_daily_kwh: length I
    equity_score: length I
    safety_penalty: length I (>=0)
    grid_penalty: length I (>=0)
    site_capex: length I (base site + civil + interconnect)
    """
    I, J = len(cands), len(demand_nodes)
    m = pyo.ConcreteModel("Solar_DCFC_Siting")

    m.I = pyo.RangeSet(0, I-1)
    m.J = pyo.RangeSet(0, J-1)

    # Decision vars
    m.open = pyo.Var(m.I, domain=pyo.Binary)
    # Use 0 as lower bound for ports/pv/storage - constraints enforce minimums only when site is open
    m.ports = pyo.Var(m.I, domain=pyo.Integers, bounds=(0, params["ports_max"]))
    m.pv_kw = pyo.Var(m.I, domain=pyo.NonNegativeReals, bounds=(0, params["pv_kw_max"]))
    m.storage_kwh = pyo.Var(m.I, domain=pyo.NonNegativeReals, bounds=(0, params["storage_kwh_max"]))
    m.assign = pyo.Var(m.I, m.J, domain=pyo.NonNegativeReals, bounds=(0,1))

    # Constants
    port_power_kw = params["port_power_kw"]
    max_sites = params["max_sites"]
    budget = params["budget_usd"]

    # Objective components
    util = sum( m.assign[i,j] * demand_nodes.loc[j,"pop_weight"] for i in m.I for j in m.J )
    # Scale util by predicted kWh to prioritize high-use sites
    util_scaled = sum( m.open[i] * pred_daily_kwh[i] for i in m.I )

    # Equity bonus (e.g., EJSCREEN composite scaled 0..1)
    equity = sum( m.open[i] * equity_score[i] for i in m.I )

    # Penalties
    safety = sum( m.open[i] * safety_penalty[i] for i in m.I )
    grid = sum( m.open[i] * grid_penalty[i] for i in m.I )

    # Cost (NPC proxy): site capex + PV + storage + charger ports (simple per-port capex)
    per_port_capex = 65000.0  # adjust with real source
    cost = sum( m.open[i]*site_capex[i] + m.pv_kw[i]*pv_capex_per_kw + m.storage_kwh[i]*storage_capex_per_kwh + m.ports[i]*per_port_capex for i in m.I )

    w = params["weights"]
    m.OBJ = pyo.Objective(expr= w["util"]*util_scaled + w["equity"]*equity - w["safety_penalty"]*safety - w["grid_penalty"]*grid - w["npc_cost"]*(cost/1e6), sense=pyo.maximize)

    # Constraints

    # Coverage: each demand node assigned to exactly 1 open site (within feasible detour)
    max_detour_km = params["max_detour_m"]/1000.0
    def assign_feasible(m, i, j):
        return m.assign[i,j] <= m.open[i] * (1.0 if dist_km[i,j] <= max_detour_km else 0.0)
    m.AssignFeasible = pyo.Constraint(m.I, m.J, rule=assign_feasible)

    def assign_sum(m, j):
        # Use <= 1 instead of == 1 to allow demand nodes without nearby sites
        # to remain unassigned (prevents infeasibility when no site is within max_detour)
        return sum(m.assign[i,j] for i in m.I) <= 1.0
    m.AssignSum = pyo.Constraint(m.J, rule=assign_sum)

    # Linking constraints: ensure closed sites have 0 for ports/pv/storage (no cost)
    # and open sites meet minimum requirements

    # Ports: min when open, 0 when closed
    def min_ports_when_open(m, i):
        return m.ports[i] >= params["ports_min"] * m.open[i]
    m.MinPorts = pyo.Constraint(m.I, rule=min_ports_when_open)

    def max_ports_when_closed(m, i):
        return m.ports[i] <= params["ports_max"] * m.open[i]
    m.MaxPorts = pyo.Constraint(m.I, rule=max_ports_when_closed)

    # PV: min when open, 0 when closed
    def min_pv_when_open(m, i):
        return m.pv_kw[i] >= params["pv_kw_min"] * m.open[i]
    m.MinPV = pyo.Constraint(m.I, rule=min_pv_when_open)

    def max_pv_when_closed(m, i):
        return m.pv_kw[i] <= params["pv_kw_max"] * m.open[i]
    m.MaxPV = pyo.Constraint(m.I, rule=max_pv_when_closed)

    # Storage: 0 when closed (min is already 0)
    def max_storage_when_closed(m, i):
        return m.storage_kwh[i] <= params["storage_kwh_max"] * m.open[i]
    m.MaxStorage = pyo.Constraint(m.I, rule=max_storage_when_closed)

    # Spacing constraint (optional simple heuristic): do not open two sites closer than min_spacing_km
    min_spacing_km = params["min_spacing_km"]
    close_pairs = [(i,k) for i in range(I) for k in range(i+1, I)
                   if np.hypot(cands.loc[i,"x"]-cands.loc[k,"x"], cands.loc[i,"y"]-cands.loc[k,"y"]) < (min_spacing_km*1000)]
    m.ClosePairs = pyo.ConstraintList()
    for (i,k) in close_pairs:
        m.ClosePairs.add(expr= m.open[i] + m.open[k] <= 1)

    # NEVI corridor logic: encourage within 1 mile buffers via implicit scoring (already in equity/util); you can also force quotas if needed.

    # Budget
    m.Budget = pyo.Constraint(expr= cost <= budget)

    # Site count
    m.SiteCount = pyo.Constraint(expr= sum(m.open[i] for i in m.I) <= max_sites)

    return m

def solve_milp(model: pyo.ConcreteModel, solver_name="highs", time_limit_s=600, mip_gap=0.01):
    if solver_name.lower()=="highs":
        solver = pyo.SolverFactory("highs")
        solver.options["time_limit"] = time_limit_s
        solver.options["mip_rel_gap"] = mip_gap
    else:
        solver = pyo.SolverFactory("cbc")
        solver.options["seconds"] = time_limit_s
        solver.options["ratioGap"] = mip_gap

    # Solve with load_solutions=False to handle infeasibility gracefully
    result = solver.solve(model, tee=False, load_solutions=False)

    # Check termination condition and handle infeasibility
    from pyomo.opt import TerminationCondition, SolutionStatus

    if result.solver.termination_condition == TerminationCondition.infeasible:
        raise ValueError(
            "MILP model is infeasible. This typically occurs when:\n"
            "  - min_spacing_km is too large relative to candidate site density\n"
            "  - max_detour_m is too small (no sites within reach of some demand nodes)\n"
            "  - budget_usd is too low to open any valid configuration\n"
            "Consider adjusting these parameters in your config file."
        )
    elif result.solver.termination_condition == TerminationCondition.unbounded:
        raise ValueError("MILP model is unbounded. Check objective function weights.")
    elif len(result.solution) > 0 and result.solution(0).status == SolutionStatus.optimal:
        # Load the solution into the model
        model.solutions.load_from(result)
    elif len(result.solution) > 0:
        # Load feasible (possibly suboptimal) solution
        model.solutions.load_from(result)
    else:
        raise ValueError(
            f"Solver failed with termination condition: {result.solver.termination_condition}. "
            "No solution found."
        )

    return result
