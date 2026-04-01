import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../hooks/useAuth";
import { useNavigate } from "react-router-dom";
import { RefreshCw, Save, Clock, Zap, Database, Activity, ChevronDown, ChevronUp } from "lucide-react";
import api from "../api";

// Telemetry
function TelemetrySection() {
  const qc = useQueryClient();
  const [showMore, setShowMore] = useState(false);

  const { data: telemetry, isLoading } = useQuery({
    queryKey: ["telemetry-status"],
    queryFn: () => api.get("/admin/telemetry").then((r) => r.data),
  });

  const enable = useMutation({
    mutationFn: () => api.post("/admin/telemetry/enable"),
                             onSuccess: () => qc.invalidateQueries(["telemetry-status"]),
  });

  const disable = useMutation({
    mutationFn: () => api.post("/admin/telemetry/disable"),
                              onSuccess: () => qc.invalidateQueries(["telemetry-status"]),
  });

  const isPending = enable.isPending || disable.isPending;
  if (!isLoading && telemetry?.suppressed) return null;

  return (
    <div className="settings-card">
    <div className="section-label">
    Anonymous Usage Telemetry
    </div>

    {isLoading ? (
      <div className="loading">Loading…</div>
    ) : telemetry?.suppressed ? null : (
      <>
      <div style={{ display: "flex", alignItems: "flex-start", gap: "0.9rem", marginBottom: "0.85rem" }}>

      <div style={{ paddingTop: "0.1rem", flexShrink: 0 }}>
      <label style={{
        position: "relative",
        display: "inline-block",
        width: "36px",
        height: "20px",
        cursor: isPending ? "not-allowed" : "pointer",
        opacity: isPending ? 0.6 : 1,
      }}>
      <input
      type="checkbox"
      checked={!!telemetry?.enabled}
      onChange={() => telemetry?.enabled ? disable.mutate() : enable.mutate()}
      disabled={isPending}
      style={{ opacity: 0, width: 0, height: 0, position: "absolute" }}
      />
      <span style={{
        position: "absolute",
        inset: 0,
        borderRadius: "20px",
        background: telemetry?.enabled ? "var(--accent)" : "var(--surface2)",
         border: "1px solid var(--border)",
         transition: "background 0.18s",
      }} />
      <span style={{
        position: "absolute",
         top: "3px",
         left: telemetry?.enabled ? "17px" : "3px",
         width: "12px",
         height: "12px",
         borderRadius: "50%",
         background: "white",
         boxShadow: "0 1px 3px rgba(0,0,0,0.25)",
         transition: "left 0.18s",
      }} />
      </label>
      </div>

      <div style={{ flex: 1 }}>
      <div style={{ fontWeight: 600, fontSize: "0.9rem", lineHeight: 1.4 }}>
      {telemetry?.enabled
        ? "Sharing anonymous usage data"
        : "Help improve OpenMTG by sharing anonymous usage data"}
        </div>

        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.25rem", lineHeight: 1.55 }}>
        {telemetry?.enabled ? (
          <>
          A daily heartbeat is being sent to the OpenMTG development team.
          Your anonymous ID is{" "}
          <code style={{
            fontSize: "0.72rem",
            background: "var(--surface2)",
                               border: "1px solid var(--border)",
                               padding: "0.1em 0.4em",
                               borderRadius: "3px",
                               letterSpacing: "0.01em",
          }}>
          {telemetry.id}
          </code>
          . Opting out will permanently delete this ID.
          </>
        ) : (
          "If enabled, a random ID is generated and a small daily heartbeat is sent. No personal data is collected. Disabled by default."
        )}
        </div>
        </div>
        </div>

        <button
        className="btn btn-ghost"
        style={{ fontSize: "0.8rem", padding: "0.3rem 0.6rem", gap: "0.3rem" }}
        onClick={() => setShowMore((v) => !v)}
        >
        {showMore ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        {showMore ? "Show less" : "Read more"}
        </button>

        {showMore && (
          <div style={{
            marginTop: "0.75rem",
            background: "var(--surface2)",
                      border: "1px solid var(--border)",
                      borderRadius: "var(--radius)",
                      padding: "1rem 1.1rem",
                      fontSize: "0.82rem",
                      lineHeight: 1.7,
                      color: "var(--text-muted)",
          }}>
          <p style={{ margin: "0 0 0.7rem" }}>
          OpenMTG does not have access to reliable usage metrics through GitHub or
          the Scryfall API. To better understand how many people actively use the
          tool, this optional feature sends a minimal daily usage signal to the
          OpenMTG development team.
          </p>
          <p style={{ margin: "0 0 0.7rem" }}>
          If enabled, a random ID is generated and stored locally in your database.
          Once per day, a small heartbeat request is sent. This allows the
          development team to estimate active user counts over time.
          </p>
          <p style={{ margin: "0 0 0.7rem" }}>
          <strong style={{ color: "var(--text)" }}>Data collected:</strong> an
          anonymous unique ID and a UTC timestamp. This ID is only created after
          opting in and is permanently deleted if you opt out.
          </p>
          <p style={{ margin: "0 0 0.7rem" }}>
          To suppress all telemetry prompts and options permanently, add the
          following to your{" "}
          <code style={{
            background: "var(--surface2)",
                      border: "1px solid var(--border)",
                      padding: "0.1em 0.35em",
                      borderRadius: "3px",
                      fontSize: "0.78rem",
          }}>
          .env
          </code>{" "}
          file:
          </p>
          <pre style={{
            margin: "0 0 0.7rem",
            background: "var(--surface2)",
                      border: "1px solid var(--border)",
                      borderRadius: "var(--radius)",
                      padding: "0.5rem 0.75rem",
                      fontSize: "0.8rem",
                      fontFamily: "monospace",
          }}>
          NOTEL=true
          </pre>
          <p style={{ margin: 0 }}>
          OpenMTG respects your privacy. Participation is completely optional and
          no personally identifiable information is ever collected. Anonymous data
          is used purely for development and is never shared, sold, traded, or
          transferred to any third party.
          </p>
          </div>
        )}
        </>
    )}
    </div>
  );
}

// Main Settings
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
     Card Price Cache
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
        Auto-refresh Interval
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
        Scryfall API Rate Limit
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

      {/* Anonymous Usage Telemetry */}
      <TelemetrySection />
      </div>
    );
}
