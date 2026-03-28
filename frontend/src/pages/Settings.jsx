import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../AuthContext";
import { useNavigate } from "react-router-dom";
import { RefreshCw, Save, Clock, Zap, Database } from "lucide-react";
import api from "../api";

export default function Settings() {
  useEffect(() => {
    document.title = "Settings - OpenMTG";
  }, []);

  const { user } = useAuth();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const { data: currentSettings, isLoading: loadingSettings } = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.get("/admin/settings").then((r) => r.data),
    enabled: !!user?.is_admin,
  });

  const [pollFast, setPollFast] = useState(false);

  const { data: status, isLoading: loadingStatus } = useQuery({
    queryKey: ["refresh-status"],
    queryFn: () =>
      api.get("/admin/settings/refresh-status").then((r) => r.data),
    enabled: !!user?.is_admin,
    refetchInterval: pollFast ? 500 : 30000,
  });

  useEffect(() => {
    if (pollFast && status?.stale_cards === 0) setPollFast(false);
  }, [status?.stale_cards, pollFast]);

  const [form, setForm] = useState({
    price_refresh_hours: 72,
    scryfall_rps: 1,
  });
  const [refreshing, setRefreshing] = useState(false);
  const [refreshMsg, setRefreshMsg] = useState("");

  useEffect(() => {
    if (currentSettings) {
      setForm({
        price_refresh_hours: parseInt(currentSettings.price_refresh_hours),
        scryfall_rps: parseInt(currentSettings.scryfall_rps),
      });
    }
  }, [currentSettings]);

  const save = useMutation({
    mutationFn: () => api.patch("/admin/settings", form),
    onSuccess: () => qc.invalidateQueries(["settings"]),
  });

  const triggerRefresh = async () => {
    setRefreshing(true);
    setRefreshMsg("");
    try {
      const res = await api.post("/admin/settings/refresh-now");
      setRefreshMsg(res.data.message);
      setPollFast(true);
    } catch (err) {
      setRefreshMsg(err.response?.data?.detail || "Failed to start refresh");
    } finally {
      setRefreshing(false);
    }
  };

  const hoursToHuman = (h) => {
    if (h < 24) return `${h} hour${h !== 1 ? "s" : ""}`;
    const days = Math.floor(h / 24);
    const rem = h % 24;
    return rem > 0 ? `${days}d ${rem}h` : `${days} day${days !== 1 ? "s" : ""}`;
  };

  const formatDate = (iso) => (iso ? new Date(iso).toLocaleString() : "—");

  const stalePct = status
    ? Math.round((status.stale_cards / (status.total_cards || 1)) * 100)
    : 0;

  const freshnessColor =
    stalePct > 50
      ? "var(--danger)"
      : stalePct > 20
        ? "var(--gold)"
        : "var(--success)";

  if (user && !user.is_admin) {
    navigate("/");
    return null;
  }

  return (
    <div className="settings-page">
      <div className="page-header">
        <h1>Settings</h1>
      </div>

      {/* Card Price Cache */}
      <div className="settings-card">
        <div className="section-label">
          <Database size={15} /> Card Price Cache
          {pollFast && (
            <span className="updating-badge">
              <RefreshCw size={11} className="spin" /> Updating…
            </span>
          )}
        </div>

        {loadingStatus ? (
          <div className="loading">Loading…</div>
        ) : (
          status && (
            <>
              <div className="stat-grid">
                <div className="stat-item">
                  <div className="stat-value">{status.total_cards}</div>
                  <div className="stat-label">Cached Cards</div>
                </div>
                <div className="stat-item">
                  <div
                    className="stat-value"
                    style={{
                      color:
                        status.fresh_cards > 0
                          ? "var(--success)"
                          : "var(--text-muted)",
                    }}
                  >
                    {status.fresh_cards}
                  </div>
                  <div className="stat-label">Fresh</div>
                </div>
                <div className="stat-item">
                  <div
                    className="stat-value"
                    style={{
                      color:
                        status.stale_cards > 0
                          ? "var(--gold)"
                          : "var(--text-muted)",
                    }}
                  >
                    {status.stale_cards}
                  </div>
                  <div className="stat-label">Stale</div>
                </div>
              </div>

              {status.total_cards > 0 && (
                <div className="freshness-wrap">
                  <div className="freshness-info">
                    <span>Cache freshness</span>
                    <span>{100 - stalePct}% fresh</span>
                  </div>
                  <div className="freshness-track">
                    <div
                      className="freshness-bar"
                      style={{
                        width: `${100 - stalePct}%`,
                        background: freshnessColor,
                      }}
                    />
                  </div>
                </div>
              )}

              <div className="meta-grid">
                <div>
                  Oldest: <span>{formatDate(status.oldest_fetch)}</span>
                </div>
                <div>
                  Newest: <span>{formatDate(status.newest_fetch)}</span>
                </div>
              </div>

              {refreshMsg && <div className="info-banner">{refreshMsg}</div>}

              <button
                className="btn btn-ghost"
                onClick={triggerRefresh}
                disabled={refreshing || status.total_cards === 0}
              >
                <RefreshCw size={16} className={refreshing ? "spin" : ""} />
                {refreshing ? "Starting Refresh…" : "Refresh Prices Now"}
              </button>
            </>
          )
        )}
      </div>

      {/* Price Refresh Settings */}
      <div className="settings-card">
        <div className="section-label">Price Refresh Settings</div>

        {loadingSettings ? (
          <div className="loading">Loading…</div>
        ) : (
          <>
            <div className="form-group">
              <label className="label-icon">
                <Clock size={14} /> Auto-refresh Interval
              </label>
              <div className="range-row">
                <input
                  type="range"
                  min={1}
                  max={168}
                  step={1}
                  value={form.price_refresh_hours}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      price_refresh_hours: parseInt(e.target.value),
                    }))
                  }
                />
                <div className="range-value">
                  {hoursToHuman(form.price_refresh_hours)}
                </div>
              </div>
              <div className="range-labels">
                <span>1 hour</span>
                <span>Default: 3 days</span>
                <span>7 days</span>
              </div>
              <div className="field-hint">
                Prices older than {hoursToHuman(form.price_refresh_hours)} will
                be automatically refreshed. The scheduler checks every 30
                minutes.
              </div>
            </div>

            <div className="form-group">
              <label className="label-icon">
                <Zap size={14} /> Scryfall API Rate Limit
              </label>
              <div className="range-row">
                <input
                  type="range"
                  min={1}
                  max={10}
                  step={1}
                  value={form.scryfall_rps}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      scryfall_rps: parseInt(e.target.value),
                    }))
                  }
                />
                <div className="range-value">{form.scryfall_rps} req/s</div>
              </div>
              <div className="range-labels">
                <span>1/s (safe)</span>
                <span>10/s (max)</span>
              </div>
              <div className="field-hint">
                Scryfall's guidelines recommend no more than 10 requests per
                second. Staying at 1/s is safest and avoids any risk of being
                rate limited.
              </div>
            </div>

            <div className="save-row">
              <button
                className="btn btn-primary"
                onClick={() => save.mutate()}
                disabled={save.isPending}
              >
                <Save size={16} />
                {save.isPending ? "Saving…" : "Save Settings"}
              </button>
              {save.isSuccess && <span className="save-success">✓ Saved</span>}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
