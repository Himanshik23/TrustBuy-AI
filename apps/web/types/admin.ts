// Mirrors admin_routes.py across auth-service, catalog-service, community-service.

export interface VerdictCount {
  verdict: string;
  count: number;
}

export interface MetricsOverview {
  investigations_today: number;
  investigations_total: number;
  average_confidence: number;
  agent_failure_rate: number;
  verdict_distribution: VerdictCount[];
}

export interface FailedInvestigation {
  investigation_id: string;
  source_url: string;
  status: string;
  created_at: string;
}
