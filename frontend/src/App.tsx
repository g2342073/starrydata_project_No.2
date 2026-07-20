import React, { useState } from "react";
import Plot from "react-plotly.js";
import { searchAxis, filterPoints, fetchPaper } from "./api";
import { AxisOption, Point, Paper } from "./types";
import PaperModal from "./PaperModal";

const App: React.FC = () => {
  // components テキストボックス
  const [componentsText, setComponentsText] = useState("");
  const [searchMode, setSearchMode] = useState<"all_terms" | "exact">("all_terms");
  // dataset A から得られる value の候補
  const [valueOptions, setValueOptions] = useState<string[]>([]);
  // value プルダウンの value
  const [selectedValue, setSelectedValue] = useState<string>("");
  // dataset A から得られる axis の候補
  const [axisOptions, setAxisOptions] = useState<AxisOption[]>([]);
  // axis プルダウンの value（"prop_x|prop_y" 形式）
  const [selectedAxis, setSelectedAxis] = useState<string>("");
  // 単位プルダウン用
  const [xUnitOptions, setXUnitOptions] = useState<string[]>([]);
  const [yUnitOptions, setYUnitOptions] = useState<string[]>([]);
  const [selectedXUnit, setSelectedXUnit] = useState<string>("");
  const [selectedYUnit, setSelectedYUnit] = useState<string>("");
  // x_min, x_max, y_min, y_max
  const [xMin, setXMin] = useState<string>("");
  const [xMax, setXMax] = useState<string>("");
  const [yMin, setYMin] = useState<string>("");
  const [yMax, setYMax] = useState<string>("");
  // Form Category
  const [formCategoryOptions, setFormCategoryOptions] = useState<string[]>([]);
  const [selectedFormCategory, setSelectedFormCategory] = useState<string>("");
  // dataset B
  const [points, setPoints] = useState<Point[]>([]);
  const [axisXLabel, setAxisXLabel] = useState<string>("");
  const [axisYLabel, setAxisYLabel] = useState<string>("");
  const [isSwapped, setIsSwapped] = useState(false);

  // 論文情報表示用
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null);
  const [paperError, setPaperError] = useState<string | null>(null);

  const [loadingSearch, setLoadingSearch] = useState(false);
  const [loadingDisplay, setLoadingDisplay] = useState(false);

  // components テキストから配列を作る
  const parseComponents = (): string[] => {
    return componentsText
      .trim()
      .split(/\s+/)
      .filter((w) => w.length > 0);
  };

  // Reset ボタン
  const handleReset = () => {
    setComponentsText("");
    setAxisOptions([]);
    setSelectedAxis("");
    setValueOptions([]);
    setSelectedValue("");
    setXMin("");
    setXMax("");
    setYMin("");
    setYMax("");
    setPoints([]);
    setAxisXLabel("");
    setAxisYLabel("");
    setSelectedPaper(null);
    setPaperError(null);
    setXUnitOptions([]);
    setYUnitOptions([]);
    setSelectedXUnit("");
    setSelectedYUnit("");
    setSearchMode("all_terms");
    setFormCategoryOptions([]);
    setSelectedFormCategory("");
  };

  // Search ボタン
  const handleSearch = async () => {
    const query = componentsText.trim();
    const comps = parseComponents();

    if (searchMode === "all_terms") {
      if (comps.length === 0) {
        alert("Please enter at least one component.");
        return;
      }
    } else {
      if (!query) {
        alert("Please enter text for exact match.");
        return;
      }
    }

    setLoadingSearch(true);
    setSelectedAxis("");
    setAxisOptions([]);
    setPoints([]);
    setSelectedPaper(null);
    setPaperError(null);

    setSelectedValue("");
    setValueOptions([]);
    setXUnitOptions([]);
    setYUnitOptions([]);
    setSelectedXUnit("");
    setSelectedYUnit("");

    try {
      const payload =
        searchMode === "exact"
          ? { query, mode: "exact" as const, components: [] }
          : { query, mode: "all_terms" as const, components: comps };

      const data = await searchAxis(payload);
      const options = data.axis_options;

      setAxisOptions(options);
      setFormCategoryOptions(data.form_category_options ?? []);
      setSelectedFormCategory("");

      const vals = new Set<string>();
      options.forEach((opt) => {
        vals.add(opt.prop_x);
        vals.add(opt.prop_y);
      });
      setValueOptions(Array.from(vals));

      if (options.length === 0) {
        alert("No data matching the conditions was found.");
      }
    } catch (err: any) {
      console.error(err);
      alert("An error occurred during Search:" + err.message);
    } finally {
      setLoadingSearch(false);
    }
  };

  // value プルダウンリスト
  const filteredAxisOptions = selectedValue
    ? axisOptions.filter(
        (opt) => opt.prop_x === selectedValue || opt.prop_y === selectedValue
      )
    : axisOptions;

  // axis プルダウンリスト
  const handleAxisChange = (value: string) => {
    setSelectedAxis(value);
    // 単位の選択をリセット
    setSelectedXUnit("");
    setSelectedYUnit("");
    setXUnitOptions([]);
    setYUnitOptions([]);

    if (!value) {
      return;
    }

    const [prop_x, prop_y] = value.split("|");
    const opt = axisOptions.find(
      (o) => o.prop_x === prop_x && o.prop_y === prop_y
    );

    if (opt) {
      const xUnits = opt.unit_x_list ?? [];
      const yUnits = opt.unit_y_list ?? [];
      setXUnitOptions(xUnits);
      setYUnitOptions(yUnits);

      // 候補が 1 個しかないときは自動選択
      if (xUnits.length === 1) {
        setSelectedXUnit(xUnits[0]);
      }
      if (yUnits.length === 1) {
        setSelectedYUnit(yUnits[0]);
      }
    }
  };

  // Display ボタン
  const handleDisplay = async () => {
    setIsSwapped(false);

    if (!selectedAxis) {
      alert("Select axis.");
      return;
    }

    const query = componentsText.trim();
    const comps = parseComponents();

    if (searchMode === "all_terms") {
      if (comps.length === 0) {
        alert("Enter components, then press Display.");
        return;
      }
    } else {
      if (!query) {
        alert("Enter text for exact match, then press Display.");
        return;
      }
    }

    const [prop_x, prop_y] = selectedAxis.split("|");

    const parseOrNull = (s: string): number | null => {
      if (!s.trim()) return null;
      const v = Number(s);
      if (Number.isNaN(v)) {
        return null;
      }
      return v;
    };

    const x_min = parseOrNull(xMin);
    const x_max = parseOrNull(xMax);
    const y_min = parseOrNull(yMin);
    const y_max = parseOrNull(yMax);

    setLoadingDisplay(true);
    setSelectedPaper(null);
    setPaperError(null);

    try {
      const query = componentsText.trim();

      const res = await filterPoints({
        // 追加（重要）
        query,
        mode: searchMode,

        // 既存互換：all_terms の場合は components も渡す．exact の場合は空配列でOK
        components: searchMode === "all_terms" ? comps : [],

        prop_x,
        prop_y,
        unit_x: selectedXUnit,
        unit_y: selectedYUnit,
        form_category: selectedFormCategory,
        x_min,
        x_max,
        y_min,
        y_max
      });

      setAxisXLabel(res.axis_x);
      setAxisYLabel(res.axis_y);
      setPoints(res.points);
    } catch (err: any) {
      console.error(err);
      alert("An error occurred during Display:" + err.message);
    } finally {
      setLoadingDisplay(false);
    }
  };

  // points をグループ化する関数
  const groupPoints = (pts: Point[]) => {
    const groups: Record<string, Point[]> = {};

    pts.forEach((p) => {
      const formCategory =
        p.form_category && p.form_category.trim() !== ""
          ? ` | ${p.form_category}`
          : "";

      const key = `${p.SID} | ${p.composition}${formCategory}`;
      if (!groups[key]) groups[key] = [];
      groups[key].push(p);
    });

    return groups;
  };

  // Download ボタン（フロント側で CSV を生成してダウンロード）
  const handleDownload = () => {
    if (points.length === 0) {
      alert("No data to download.");
      return;
    }
    const header = ["SID", "composition", "x", "y"];
    const lines = [header.join(",")];
    for (const p of points) {
      lines.push([p.SID, p.composition, p.x.toString(), p.y.toString()].join(","));
    }
    const csv = lines.join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "datasetB.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  // table の SID クリック
  const handleSidClick = async (sid: string) => {
    setSelectedPaper(null);
    setPaperError(null);
    try {
      const paper = await fetchPaper(sid);
      setSelectedPaper(paper);
    } catch (err: any) {
      console.error(err);
      setPaperError(err.message);
    }
  };

  // axis プルダウン option の表示文字列
  const axisOptionLabel = (opt: AxisOption) => {
    return `${opt.prop_x} vs ${opt.prop_y}`;
  };

  return (
    <div style={{ padding: "1rem", fontFamily: "sans-serif" }}>
      <h1>Starrydata Viewer</h1>

      {/* 検索パネル */}
      <section
        style={{
          border: "1px solid #ccc",
          borderRadius: "8px",
          padding: "1rem",
          marginBottom: "1rem"
        }}
      >
        <h2>Search Conditions</h2>

        {/* テキストボックス components */}
        <div style={{ marginBottom: "0.5rem" }}>
          <label>
            Components:
            <input
              type="text"
              value={componentsText}
              onChange={(e) => setComponentsText(e.target.value)}
              style={{ width: "400px", marginLeft: "0.5rem" }}
              placeholder="Example: Ni Co"
            />
          </label>
        </div>
        <div style={{ marginBottom: "0.5rem" }}>
          <label>
            Search mode:
            <select
              value={searchMode}
              onChange={(e) => setSearchMode(e.target.value as any)}
              style={{ marginLeft: "0.5rem" }}
            >
              <option value="all_terms">All terms（space-separated AND）</option>
              <option value="exact">Exact match</option>
            </select>
          </label>
        </div>

        {/* ボタン Search / Reset */}
        <div style={{ marginBottom: "0.5rem" }}>
          <button onClick={handleSearch} disabled={loadingSearch}>
            {loadingSearch ? "Searching..." : "Search"}
          </button>
          <button onClick={handleReset} style={{ marginLeft: "0.5rem" }}>
            Reset
          </button>
        </div>
      </section>

      {/* 散布図 scatter */}
      <section
        style={{
          border: "1px solid #ccc",
          borderRadius: "8px",
          padding: "1rem",
          marginBottom: "1rem"
        }}
      >
        <h2>Scatter Plot</h2>

        {/* プルダウン value */}
        <div style={{ marginBottom: "0.5rem" }}>
          <label>
            Value:
            <select
              value={selectedValue}
              onChange={(e) => {
                setSelectedValue(e.target.value);
                setSelectedAxis(""); // axis をリセット
              }}
              style={{ marginLeft: "0.5rem", minWidth: "250px" }}
            >
              <option value="">--- Select value ---</option>
              {valueOptions.map((v, idx) => (
                <option key={idx} value={v}>
                  {v}
                </option>
              ))}
            </select>
          </label>
        </div>

        {/* プルダウン axis */}
        <div style={{ marginBottom: "0.5rem" }}>
          <label>
            X-axis vs Y-axis: 
            <select
              value={selectedAxis}
              onChange={(e) => handleAxisChange(e.target.value)}
              style={{ marginLeft: "0.5rem", minWidth: "250px" }}
            >
              <option value="">--- Select axis ---</option>
              {filteredAxisOptions.map((opt, idx) => (
                <option
                  key={`${opt.prop_x}|${opt.prop_y}|${idx}`}
                  value={`${opt.prop_x}|${opt.prop_y}`}
                >
                  {axisOptionLabel(opt)}
                </option>
              ))}
            </select>
          </label>
        </div>

        {/* X-unit / Y-unit プルダウン（横並び） */}
        <div style={{ display: "flex", gap: "1rem", marginBottom: "0.5rem", flexWrap: "wrap" }}>
          <div>
            <label>
              X-unit:
              <select
                value={selectedXUnit}
                onChange={(e) => setSelectedXUnit(e.target.value)}
                style={{ marginLeft: "0.5rem", minWidth: "150px" }}
              >
                <option value="">--- Select X-unit ---</option>
                {xUnitOptions.map((u) => (
                  <option key={u} value={u}>
                    {u}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div>
            <label>
              Y-unit:
              <select
                value={selectedYUnit}
                onChange={(e) => setSelectedYUnit(e.target.value)}
                style={{ marginLeft: "0.5rem", minWidth: "150px" }}
              >
                <option value="">--- Select Y-unit ---</option>
                {yUnitOptions.map((u) => (
                  <option key={u} value={u}>
                    {u}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>

        {/* x_min, x_max, y_min, y_max */}
        <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
          <div>
            <label>
              Lower limit of x: 
              <input
                type="text"
                value={xMin}
                onChange={(e) => setXMin(e.target.value)}
                style={{ width: "100px", marginLeft: "0.5rem" }}
              />
            </label>
          </div>
          <div>
            <label>
              Upper limit of x: 
              <input
                type="text"
                value={xMax}
                onChange={(e) => setXMax(e.target.value)}
                style={{ width: "100px", marginLeft: "0.5rem" }}
              />
            </label>
          </div>
          <div>
            <label>
              Lower limit of y: 
              <input
                type="text"
                value={yMin}
                onChange={(e) => setYMin(e.target.value)}
                style={{ width: "100px", marginLeft: "0.5rem" }}
              />
            </label>
          </div>
          <div>
            <label>
              Upper limit of y: 
              <input
                type="text"
                value={yMax}
                onChange={(e) => setYMax(e.target.value)}
                style={{ width: "100px", marginLeft: "0.5rem" }}
              />
            </label>
          </div>
        </div>

        <div style={{ marginTop: "0.5rem", marginBottom: "0.5rem" }}>
          <label>
            Form:
            <select
              value={selectedFormCategory}
              onChange={(e) => setSelectedFormCategory(e.target.value)}
              style={{ marginLeft: "0.5rem", minWidth: "180px" }}
            >
              <option value="">--- All forms ---</option>
              {formCategoryOptions.map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </select>
          </label>
        </div>

        {/* ボタン Display */}
        <div style={{ marginTop: "0.5rem" }}>
          <button onClick={handleDisplay} disabled={loadingDisplay}>
            {loadingDisplay ? "Displaying..." : "Display"}
          </button>

          {/* ★追加：グラフだけ入れ替え */}
          <button
            type="button"
            onClick={() => setIsSwapped((v) => !v)}
            disabled={points.length === 0}
            style={{ marginLeft: "0.5rem" }}
          >
            Swap graph X/Y
          </button>
        </div>

        {points.length === 0 ? (
          <p>No data to display. Please run Search and Display.</p>
        ) : (
          (() => {
            const grouped = groupPoints(points);

            const plotData = Object.entries(grouped).map(([key, pts]) => ({
              x: isSwapped ? pts.map((p) => p.y) : pts.map((p) => p.x),
              y: isSwapped ? pts.map((p) => p.x) : pts.map((p) => p.y),
              mode: "markers",
              type: "scattergl",
              name: key, // SID | composition
              marker: { size: 8 }
            }));

          return (
            <div style={{ width: "100%", maxWidth: 900 }}>
              <Plot
                data={plotData}
                layout={{
                  autosize: true,
                  height: 600, // グラフ本体の高さを確保（凡例が下でもつぶれにくい）
                  title: "Dataset B",
                  xaxis: { title: (isSwapped ? { text: axisYLabel || "y" } : { text: axisXLabel || "x" }) },
                  yaxis: { title: (isSwapped ? { text: axisXLabel || "x" } : { text: axisYLabel || "y" }) },
                  showlegend: true,

                  // ★凡例を下へ
                  legend: {
                    orientation: "h",
                    x: 0.5,
                    xanchor: "center",
                    y: -0.25,
                    yanchor: "top"
                  },

                  // ★凡例のぶん下余白を増やす（ここが重要）
                  margin: { l: 60, r: 20, t: 50, b: 160 }
                }}
                revision={`${axisXLabel}|${axisYLabel}|${points.length}`}
                useResizeHandler
                style={{ width: "100%" }}
              />
            </div>
          );
          })()
        )}
      </section>

      {/* table と SID クリック */}
      <section
        style={{
          border: "1px solid #ccc",
          borderRadius: "8px",
          padding: "1rem",
          marginBottom: "1rem"
        }}
      >
        <h2>Value List</h2>
        {points.length === 0 ? (
          <p>No data to display.</p>
        ) : (
          <>
            <div style={{ marginBottom: "1rem" }}>
                Number of Records : {points.length}
            </div>
            {/* ボタン Download */}
            <div style={{ marginBottom: "1rem" }}>
              <button onClick={handleDownload}>
                Download
              </button>
            </div>
            <table
              style={{
                borderCollapse: "collapse",
                width: "100%"
              }}
            >
              <thead>
                <tr>
                  <th style={{ border: "1px solid #ccc", padding: "0.25rem" }}>SID</th>
                  <th style={{ border: "1px solid #ccc", padding: "0.25rem" }}>Composition</th>
                  <th style={{ border: "1px solid #ccc", padding: "0.25rem" }}>x</th>
                  <th style={{ border: "1px solid #ccc", padding: "0.25rem" }}>y</th>
                  <th style={{ border: "1px solid #ccc", padding: "0.25rem" }}>Form</th>
                  <th style={{ border: "1px solid #ccc", padding: "0.25rem" }}>Form Comment</th>
                  <th style={{ border: "1px solid #ccc", padding: "0.25rem" }}>Purity</th>
                  <th style={{ border: "1px solid #ccc", padding: "0.25rem" }}>Purity Comment</th>
                </tr>
              </thead>
              <tbody>
                {points.map((p, idx) => (
                  <tr key={`${p.SID}-${idx}`}>
                    <td
                      style={{
                        border: "1px solid #ccc",
                        padding: "0.25rem",
                        color: "blue",
                        cursor: "pointer",
                        textDecoration: "underline"
                      }}
                      onClick={() => handleSidClick(p.SID)}
                      title="Click to display paper details"
                    >
                      {p.SID}
                    </td>
                    <td style={{ border: "1px solid #ccc", padding: "0.25rem" }}>{p.composition}</td>
                    <td style={{ border: "1px solid #ccc", padding: "0.25rem" }}>{p.x}</td>
                    <td style={{ border: "1px solid #ccc", padding: "0.25rem" }}>{p.y}</td>
                    <td style={{ border: "1px solid #ccc", padding: "0.25rem" }}>{p.form_category}</td>
                    <td style={{ border: "1px solid #ccc", padding: "0.25rem" }}>{p.form_comment}</td>
                    <td style={{ border: "1px solid #ccc", padding: "0.25rem" }}>{p.purity_category}</td>
                    <td style={{ border: "1px solid #ccc", padding: "0.25rem" }}>{p.purity_comment}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </section>
      {/* ★ SIDをクリックしたら表示されるポップアップカード ★ */}
      <PaperModal
        paper={selectedPaper}
        onClose={() => setSelectedPaper(null)}
      />
    </div>
  );
};

export default App;
