import { useEffect, useState } from "react";
import AlertDetailBox from "./AlertDetailBox";
import api from "../utils/api";

export default function PriceAlerts({ selectedAsset }) {
  const [alerts, setAlerts] = useState([]);
  const [severityFilter, setSeverityFilter] = useState("");
  const [limit, setLimit] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchAlerts = async (controller) => {
    try {
      setError("");
      setLoading(true);
      const alertParams = `?asset_symbol=${selectedAsset}&limit=${limit}&severity=${severityFilter}`;
      const res = await api.get(`/alerts${alertParams}`, {
        signal: controller.signal,
      });
      setAlerts(filterAlerts(res.data.data || [], severityFilter));
    } catch (err) {
      console.log(err);
      if (err.name !== "CanceledError" && err.code !== "ERR_CANCELED") {
        setError("Failed to load alerts");
      }
    } finally {
      setLoading(false);
    }
    return () => controller.abort();
  };

  useEffect(() => {
    const controller = new AbortController();
    fetchAlerts(controller);
  }, [selectedAsset, severityFilter, limit]);

  return (
    <div>
      <div className="container">
        <div className="header">
          <div>
            <h2>Price Warning Alerts</h2>
          </div>

          <div className="select-controls">
            <select
              className="select"
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
            >
              <option value="">All Severities</option>
              <option value="warning">Warning</option>
              <option value="info">Info</option>
              <option value="critical">Critical</option>
            </select>
            
            <select
              className="select"
              value={limit}
              onChange={(e) => setLimit(e.target.value)}
            >
              <option value="">Limit</option>
              <option value={100}>100</option>
              <option value={10}>10</option>
              <option value={5}>5</option>
            </select>

            <button className="btn-primary" onClick={fetchAlerts}>
              Refresh
            </button>
          </div>
        </div>

        {loading && alerts.length === 0 ? (
          <div className="empty-container">Loading alerts...</div>
        ) : error ? (
          <div className="empty-container">{error}</div>
        ) : alerts.length === 0 ? (
          <div className="empty-container">
            No alerts found for the selected filters.
          </div>
        ) : (
          <div className="card-list">
            {alerts.map((alert) => {
              const severity = (alert.severity || "info").toLowerCase();

              return (
                <div key={alert.id} className={`card alert ${severity}`}>
                  <div className="header">
                    <div className="alert-header">
                      <div className="alert-symbol">
                        {alert.asset_symbol || "Unknown Asset"}
                      </div>
                      <div className="alert-type">
                        {alert.alert_type || "alert"}
                      </div>
                    </div>

                    <div className={`alert-pill ${severity}`}>{severity}</div>
                  </div>

                  {alert.details && (
                    <div className="alert-details-grid">
                      <AlertDetailBox
                        title="Divergence"
                        content={alert.details.divergence?.toFixed(4) ?? "-"}
                      />
                      <AlertDetailBox
                        title="Price Close"
                        content={
                          alert.details.price_close?.toLocaleString() ?? "-"
                        }
                      />
                      <AlertDetailBox
                        title="Price Change %"
                        content={alert.details.divergence?.toFixed(4) ?? "-"}
                        styling={
                          (alert.details.price_change_pct ?? 0) < 0
                            ? "negative"
                            : "positive"
                        }
                      />
                      <AlertDetailBox
                        title="Weighted Sentiment"
                        content={
                          alert.details.weighted_sentiment?.toFixed(4) ?? "-"
                        }
                      />
                      <AlertDetailBox
                        title="Message Volume"
                        content={alert.details.message_volume ?? "-"}
                      />
                    </div>
                  )}

                  <div className="alert-message">
                    {alert.message || "No message provided"}
                  </div>

                  <div className="alert-footer">
                    <p>Event time: {formatDateTime(alert.event_timestamp)}</p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function sortAlerts(alerts) {
  const severityRank = { critical: 3, warning: 2, info: 1 };

  return [...alerts].sort((a, b) => {
    const sevA = severityRank[(a.severity || "info").toLowerCase()] || 0;
    const sevB = severityRank[(b.severity || "info").toLowerCase()] || 0;

    if (sevA !== sevB) {
      return sevB - sevA;
    }

    return new Date(b.event_timestamp) - new Date(a.event_timestamp);
  });
}

function filterAlerts(alerts, severity) {
  if (alerts.length == 0) return [];
  if (severity == "") return sortAlerts(alerts);
  const filtered = alerts.filter((alert) => {
    return alert.severity == severity;
  });

  return sortAlerts(filtered);
}

function formatDateTime(dateString) {
  if (!dateString) return "Unknown time";
  const date = new Date(dateString);
  return date.toLocaleString();
}
