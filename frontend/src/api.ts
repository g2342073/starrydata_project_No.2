import {
  AxisOption,
  SearchResponse,
  FilterRequestBody,
  FilterResponse,
  Paper
} from "./types";

const API_BASE = "https://starrydata-project-no-2-backend.onrender.com";

export type SearchMode = "all_terms" | "exact";

export type SearchPayload = {
  components?: string[];
  query?: string;
  mode?: SearchMode;
};

export async function searchAxis(arg: string[] | SearchPayload): Promise<SearchResponse> {  // �݊��F����܂Œʂ�z��ŌĂ΂ꂽ�ꍇ
  const payload: SearchPayload = Array.isArray(arg)
    ? { components: arg, mode: "all_terms" }
    : { ...arg };

  // �����w�肪�Ȃ���Ώ]���ǂ���
  if (!payload.mode) payload.mode = "all_terms";
  if (!payload.components) payload.components = [];

  const res = await fetch(`${API_BASE}/api/search`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(`Search failed: ${res.statusText}`);
  }
  const data = (await res.json()) as SearchResponse;
  return data;
}


export async function filterPoints(body: FilterRequestBody): Promise<FilterResponse> {
  const res = await fetch(`${API_BASE}/api/filter`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(body)
  });
  if (!res.ok) {
    throw new Error(`Filter failed: ${res.statusText}`);
  }
  return (await res.json()) as FilterResponse;
}

export async function fetchPaper(sid: string): Promise<Paper> {
  const res = await fetch(`${API_BASE}/api/paper/${encodeURIComponent(sid)}`);
  if (!res.ok) {
    throw new Error(`Paper not found: ${sid}`);
  }
  return (await res.json()) as Paper;
}
