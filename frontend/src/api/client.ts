const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

export interface CheckOptions {
  threshold?: number;
  max_queries?: number;
  exclude_quotes?: boolean;
}

export interface MatchResult {
  text: string;
  start: number;
  end: number;
  similarity: number;
  source_url: string;
  is_legal_citation: boolean;
}

export interface CheckResponse {
  total_score: number;
  status: "ok" | "warning" | "danger" | "critical";
  matches: MatchResult[];
  processing_time: number;
  per_source_scores: Record<string, number>;
}

export async function checkText(
  text: string,
  options?: CheckOptions
): Promise<CheckResponse> {
  const response = await fetch(`${API_BASE_URL}/check`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, options: options ?? {} }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP error ${response.status}`);
  }

  return response.json();
}
