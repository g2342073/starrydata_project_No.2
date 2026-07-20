export interface AxisOption {
  prop_x: string;
  prop_y: string;
  unit_x_list: string[];  // この prop_x/prop_y の組で出てくる unit_x のユニーク一覧
  unit_y_list: string[];  // この prop_x/prop_y の組で出てくる unit_y のユニーク一覧
}

export interface SearchResponse {
  axis_options: AxisOption[];
  form_category_options: string[];
}

export type SearchMode = "all_terms" | "exact";

export interface FilterRequestBody {
  // 追加
  query?: string;
  mode?: SearchMode;

  // 既存
  components: string[];
  prop_x: string;
  prop_y: string;
  unit_x?: string;
  unit_y?: string;
  x_min: number | null;
  x_max: number | null;
  y_min: number | null;
  y_max: number | null;
  form_category?: string;
}

export interface Point {
  SID: string;
  x: number;
  y: number;
  form_category?: string;
  form_comment?: string;
  purity_category?: string;
  purity_comment?: string;
}

export interface FilterResponse {
  axis_x: string;
  axis_y: string;
  points: Point[];
}

export interface Paper {
  SID: string;
  DOI?: string | null;
  URL?: string | null;
  issued?: string | null;
  author?: string | null;
  title?: string | null;
  container_title?: string | null;
  container_title_short?: string | null;
  volume?: string | null;
  issue?: string | null;
  page?: string | null;
  ISSN?: string | null;
  publisher?: string | null;
  project_names?: string | null;
  created_at?: string | null;
}
