import { useEffect, useState } from "react";
import Plot, { baseLayout, plotConfig } from "./components/Plot";
import {
  getBooks,
  getHistory,
  getLatency,
  getOpportunities,
  getTriangular,
} from "./api/client";

const chartStyle = { width: "100%", height: "300px" };
const bps = (x: number) => (x * 1e4).toFixed(1);

export default function App() {
  const [books, setBooks] = useState<any>(null);
  const [opps, setOpps] = useState<any>(null);
  const [tri, setTri] = useState<any>(null);
  const [latency, setLatency] = useState<any>(null);
  const [history, setHistory] = useState<any>(null);

  function refresh() {
    getBooks().then(setBooks);
    getOpportunities().then(setOpps);
  }
  useEffect(() => {
    refresh();
    getTriangular(true).then(setTri);
    getLatency().then(setLatency);
    getHistory().then(setHistory);
  }, []);

  return (
    <>
      <header className="app-header">
        <h1>Crypto Arbitrage Monitor</h1>
        <div className="sub">
          Fee- &amp; slippage-adjusted cross-venue spreads, liquidity filters, edge decay.
        </div>
      </header>
      <div className="warn">
        <b>Monitoring / analytics only.</b> Theoretical spreads net of fees and book slippage.
        Not trading advice; no orders are placed.
      </div>

      <div className="grid">
        <div className="card full">
          <h2>
            Venue tops <button style={{ float: "right" }} onClick={refresh}>Refresh</button>
          </h2>
          {books && (
            <table>
              <thead>
                <tr>
                  <th>Venue</th>
                  <th>Best bid</th>
                  <th>Best ask</th>
                  <th>Mid</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries<any>(books.books).map(([v, b]) => (
                  <tr key={v}>
                    <td>{v}</td>
                    <td className="pos">{b.best_bid.toLocaleString()}</td>
                    <td className="neg">{b.best_ask.toLocaleString()}</td>
                    <td>{b.mid.toLocaleString(undefined, { maximumFractionDigits: 2 })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="card full">
          <h2>Detected opportunities (fee + slippage adjusted)</h2>
          {opps && opps.opportunities.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>Buy</th>
                  <th>Sell</th>
                  <th>Gross bps</th>
                  <th>Net bps</th>
                  <th>Max size</th>
                  <th>Est. profit</th>
                </tr>
              </thead>
              <tbody>
                {opps.opportunities.map((o: any, i: number) => (
                  <tr key={i}>
                    <td>{o.buy_venue}</td>
                    <td>{o.sell_venue}</td>
                    <td>{bps(o.gross_spread)}</td>
                    <td className="pos">{bps(o.net_spread)}</td>
                    <td>{o.max_size.toFixed(3)}</td>
                    <td className="pos">${o.est_profit.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="stat"><span>No opportunities above threshold.</span></div>
          )}
        </div>

        <div className="card">
          <h2>Triangular cycle</h2>
          <div className="row" style={{ marginBottom: 8 }}>
            <button onClick={() => getTriangular(true).then(setTri)}>Profitable</button>
            <button onClick={() => getTriangular(false).then(setTri)}>Balanced</button>
          </div>
          {tri && (
            <div>
              <div className="stat">
                <span>cycle:</span> <b>{tri.legs.join("  →  ")}</b>
              </div>
              <br />
              <span className="stat">
                <span>net return:</span>{" "}
                <b className={tri.net_return > 0 ? "pos" : "neg"}>
                  {(tri.net_return * 100).toFixed(3)}%
                </b>
              </span>
              <span className="stat">
                <span>opportunity:</span>{" "}
                <b className={tri.is_opportunity ? "pos" : "neg"}>
                  {tri.is_opportunity ? "YES" : "no"}
                </b>
              </span>
            </div>
          )}
        </div>

        <div className="card">
          <h2>Latency by venue</h2>
          {latency && (
            <Plot
              data={[
                {
                  x: Object.keys(latency),
                  y: Object.values<any>(latency).map((s) => s.p50 * 1000),
                  name: "p50 ms",
                  type: "bar",
                  marker: { color: "#4da3ff" },
                },
                {
                  x: Object.keys(latency),
                  y: Object.values<any>(latency).map((s) => s.p95 * 1000),
                  name: "p95 ms",
                  type: "bar",
                  marker: { color: "#f7a600" },
                },
              ]}
              layout={{ ...baseLayout, yaxis: { ...baseLayout.yaxis, title: "ms" } }}
              config={plotConfig}
              style={chartStyle}
            />
          )}
        </div>

        <div className="card full">
          <h2>Opportunity net spread &amp; decay</h2>
          {history && (
            <>
              <div className="stat">
                <span>half-life:</span>{" "}
                <b>{isFinite(history.half_life) ? `${history.half_life.toFixed(2)}s` : "∞"}</b>
              </div>
              <div className="stat">
                <span>edge lifetime:</span> <b>{history.lifetime.toFixed(1)}s</b>
              </div>
              <Plot
                data={[
                  {
                    x: history.t,
                    y: history.net_spread.map((v: number) => v * 1e4),
                    name: "net spread (bps)",
                    mode: "markers",
                    type: "scatter",
                    marker: { color: "#4da3ff", size: 6 },
                  },
                  {
                    x: history.t,
                    y: history.t.map((t: number) => history.s0 * Math.exp(-history.decay_rate * t) * 1e4),
                    name: "decay fit",
                    type: "scatter",
                    line: { color: "#f7a600" },
                  },
                  {
                    x: history.t,
                    y: history.t.map(() => history.threshold * 1e4),
                    name: "threshold",
                    type: "scatter",
                    line: { color: "#f85149", dash: "dash" },
                  },
                ]}
                layout={{
                  ...baseLayout,
                  xaxis: { ...baseLayout.xaxis, title: "seconds" },
                  yaxis: { ...baseLayout.yaxis, title: "bps" },
                }}
                config={plotConfig}
                style={chartStyle}
              />
            </>
          )}
        </div>
      </div>
    </>
  );
}
