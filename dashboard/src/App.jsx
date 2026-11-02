import React, { useState, useEffect } from "react";
import {
  Activity,
  Mail,
  Send,
  Users,
  Calendar,
  Terminal,
  Search,
  CheckCircle,
  Clock,
  Play,
  Pause,
  RefreshCw,
  Zap,
  Globe,
  Radio,
  Sparkles,
  MessageSquare,
  AlertTriangle,
  XCircle,
  Key,
  ShieldCheck,
  Plus,
  Trash2,
  ExternalLink,
  Sliders,
  Check,
  EyeOff,
  Eye
} from "lucide-react";

const API_BASE = "/api";
const PORTFOLIO_URL = "https://portfolio-public-theta-three.vercel.app/";

function renderPortfolioLinks(text) {
  if (typeof text !== "string") return text;
  const marker = "[[PORTFOLIO_LINK]]";
  const chunks = text.split(marker);
  return chunks.flatMap((chunk, index) => index === chunks.length - 1
    ? [chunk]
    : [chunk, <a key={`portfolio-${index}`} href={PORTFOLIO_URL} target="_blank" rel="noopener noreferrer" style={{ color: "#7dd3fc", textDecoration: "underline", textUnderlineOffset: "2px" }}>View portfolio</a>]);
}

export default function App() {
  const [activeTab, setActiveTab] = useState("messages");
  const [stats, setStats] = useState(null);
  const [leads, setLeads] = useState([]);
  const [outreach, setOutreach] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [logs, setLogs] = useState([]);
  const [search, setSearch] = useState("");
  const [outreachSearch, setOutreachSearch] = useState("");
  const [outreachFilter, setOutreachFilter] = useState("ALL");
  const [senderFilter, setSenderFilter] = useState("ALL");
  const [selectedMessageEmail, setSelectedMessageEmail] = useState(null);
  const selectedMessage = outreach.find((item) => item.email === selectedMessageEmail) || null;
  const [harvesting, setHarvesting] = useState(false);
  const [manualReply, setManualReply] = useState("");
  const [sendingReply, setSendingReply] = useState(false);
  const [suggestingReply, setSuggestingReply] = useState(false);

  // New Account Form State
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newName, setNewName] = useState("");
  const [newLimit, setNewLimit] = useState(200);
  const [addingAccount, setAddingAccount] = useState(false);
  const [accountActionMessage, setAccountActionMessage] = useState(null);
  const [testingEmail, setTestingEmail] = useState(null);

  const fetchData = async () => {
    try {
      const [resStats, resLeads, resOutreach, resLogs, resAccounts] = await Promise.all([
        fetch(`${API_BASE}/stats`).then((r) => r.json()),
        fetch(`${API_BASE}/leads`).then((r) => r.json()),
        fetch(`${API_BASE}/outreach`).then((r) => r.json()),
        fetch(`${API_BASE}/logs`).then((r) => r.json()),
        fetch(`${API_BASE}/accounts`).then((r) => r.json()).catch(() => ({ accounts: [] })),
      ]);
      setStats(resStats);
      setLeads(resLeads);
      setOutreach(resOutreach);
      setLogs(resLogs);
      setAccounts(resAccounts?.accounts || []);

    } catch (err) {
      console.error("API error:", err);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 2500);
    return () => clearInterval(interval);
  }, []);

  const toggleWorker = async () => {
    try {
      await fetch(`${API_BASE}/worker/toggle`, { method: "POST" });
      fetchData();
    } catch (e) {
      console.error(e);
    }
  };

  const toggleAutoSend = async () => {
    try {
      await fetch(`${API_BASE}/autosend/toggle`, { method: "POST" });
      fetchData();
    } catch (e) {
      console.error(e);
    }
  };

  const triggerHarvest = async () => {
    setHarvesting(true);
    try {
      await fetch(`${API_BASE}/harvest-now`, { method: "POST" });
      setTimeout(() => {
        setHarvesting(false);
        fetchData();
      }, 2000);
    } catch (e) {
      alert("Error: " + e);
      setHarvesting(false);
    }
  };

  const handleSendManualReply = async () => {
    if (!manualReply.trim() || !selectedMessage) return;
    setSendingReply(true);
    try {
      const res = await fetch(`${API_BASE}/reply/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: selectedMessage.email,
          message: manualReply.trim(),
        }),
      });
      const data = await res.json();
      if (data.success) {
        setManualReply("");
        fetchData();
      } else {
        alert("Failed to send reply: " + (data.error || "Unknown error"));
      }
    } catch (e) {
      alert("Network error: " + e);
    }
    setSendingReply(false);
  };

  const handleSuggestReply = async () => {
    if (!selectedMessage) return;
    setSuggestingReply(true);
    try {
      const res = await fetch(`${API_BASE}/suggest-reply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: selectedMessage.email }),
      });
      const data = await res.json();
      if (data.success && data.suggestion) {
        setManualReply(data.suggestion);
      }
    } catch (e) {
      console.error(e);
    }
    setSuggestingReply(false);
  };

  // Account Management Handlers
  const handleAddAccount = async (e) => {
    e.preventDefault();
    if (!newEmail.trim() || !newPassword.trim()) {
      setAccountActionMessage({ type: "error", text: "Please enter Gmail address and 16-character App Password." });
      return;
    }
    setAddingAccount(true);
    setAccountActionMessage({ type: "info", text: "Authenticating SMTP & IMAP with Google servers..." });

    try {
      const res = await fetch(`${API_BASE}/accounts/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: newEmail.trim().toLowerCase(),
          app_password: newPassword.trim(),
          sender_name: newName.trim() || "Shubham Dixit",
          daily_limit: parseInt(newLimit, 10) || 200,
        }),
      });
      const data = await res.json();
      if (data.success) {
        setAccountActionMessage({ type: "success", text: data.message });
        setNewEmail("");
        setNewPassword("");
        setNewName("");
        setNewLimit(200);
        fetchData();
      } else {
        setAccountActionMessage({ type: "error", text: data.error || data.message });
      }
    } catch (err) {
      setAccountActionMessage({ type: "error", text: "Network error: " + err.message });
    }
    setAddingAccount(false);
  };

  const handleToggleAccount = async (email) => {
    try {
      const res = await fetch(`${API_BASE}/accounts/toggle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();
      if (data.success) {
        fetchData();
      } else {
        alert(data.error || "Toggle failed");
      }
    } catch (e) {
      alert("Error: " + e);
    }
  };

  const handleDeleteAccount = async (email) => {
    if (!window.confirm(`Are you sure you want to delete Gmail account ${email}?`)) return;
    try {
      const res = await fetch(`${API_BASE}/accounts/delete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();
      if (data.success) {
        fetchData();
      } else {
        alert(data.error || "Delete failed");
      }
    } catch (e) {
      alert("Error: " + e);
    }
  };

  const handleTestAccount = async (email) => {
    setTestingEmail(email);
    try {
      const res = await fetch(`${API_BASE}/accounts/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();
      alert(data.success ? `✅ ${email}: ${data.message}` : `❌ ${email}: ${data.error}`);
    } catch (e) {
      alert("Test failed: " + e);
    }
    setTestingEmail(null);
  };

  // Filtered Leads Table
  const filteredLeads = leads.filter((l) => {
    const q = search.toLowerCase();
    return (
      l.business_name?.toLowerCase().includes(q) ||
      l.email?.toLowerCase().includes(q) ||
      l.contact_person?.toLowerCase().includes(q) ||
      l.category?.toLowerCase().includes(q) ||
      l.address?.toLowerCase().includes(q)
    );
  });

  // Filtered Outreach List
  const filteredOutreach = outreach.filter((item) => {
    const q = outreachSearch.toLowerCase();
    const matchesSearch =
      !q ||
      item.business_name?.toLowerCase().includes(q) ||
      item.email?.toLowerCase().includes(q) ||
      item.subject?.toLowerCase().includes(q) ||
      item.body?.toLowerCase().includes(q);

    if (!matchesSearch) return false;

    if (senderFilter !== "ALL" && item.assigned_sender !== senderFilter) {
      return false;
    }

    if (outreachFilter === "ALL") return true;
    if (outreachFilter === "CHATS") return item.status === "NEGOTIATING" || item.status === "MEETING_BOOKED";
    if (outreachFilter === "SEEN_NO_REPLY") {
      const hasClientReply = Array.isArray(item.history) && item.history.some(h => typeof h === 'object' && h && String(h.sender || '').toLowerCase() === 'client');
      return item.status === "SENT" && !hasClientReply;
    }
    if (outreachFilter === "SENT") return item.status === "SENT";
    if (outreachFilter === "DRAFTED") return item.status === "DRAFTED" || item.status === "SENDING";
    if (outreachFilter === "NEW") return item.status === "NEW";
    if (outreachFilter === "FAILED") return item.status === "FAILED";
    return true;
  });

  const senderPauseUntil = stats?.sender_pause_until ? new Date(stats.sender_pause_until) : null;
  const senderCoolingDown = Boolean(
    stats?.auto_send && senderPauseUntil && senderPauseUntil.getTime() > Date.now()
  );
  const senderResumeLabel = senderPauseUntil
    ? senderPauseUntil.toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })
    : "";

  return (
    <div style={{ backgroundColor: "#000000", minHeight: "100vh", color: "#ededed" }}>
      {/* Ultra-Modern Compact Navbar (Sleek Linear/Vercel Style) */}
      <header
        style={{
          borderBottom: "1px solid rgba(255, 255, 255, 0.07)",
          padding: "7px 20px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          backgroundColor: "rgba(9, 9, 11, 0.92)",
          backdropFilter: "blur(16px)",
          position: "sticky",
          top: 0,
          zIndex: 50,
          minHeight: "44px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "14px", flexWrap: "wrap" }}>
          {/* Logo & Status Indicator */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span
              style={{
                width: "7px",
                height: "7px",
                borderRadius: "50%",
                backgroundColor: stats?.worker_running ? "#10b981" : "#ef4444",
                boxShadow: stats?.worker_running ? "0 0 8px rgba(16,185,129,0.9)" : "none",
                display: "inline-block",
              }}
              className={stats?.worker_running ? "radar-pulse" : ""}
            />
            <span style={{ fontSize: "13px", fontWeight: 800, letterSpacing: "-0.3px", color: "#ffffff" }}>
              NEXUS UK
            </span>
            <span
              style={{
                fontSize: "9px",
                letterSpacing: "0.5px",
                textTransform: "uppercase",
                padding: "2px 6px",
                borderRadius: "4px",
                backgroundColor: "rgba(239, 68, 68, 0.12)",
                color: "#f87171",
                border: "1px solid rgba(239, 68, 68, 0.28)",
                fontWeight: 600,
                fontFamily: "JetBrains Mono, monospace",
              }}
            >
              🇬🇧 UK & BRITISH ISLES
            </span>
          </div>

          <div style={{ width: "1px", height: "14px", backgroundColor: "#27272a" }} />

          {/* Minimal Telemetry Capsule */}
          <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "11px", fontFamily: "JetBrains Mono, monospace" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
              <span style={{ color: "#71717a" }}>Sender:</span>
              <span style={{ color: "#e4e4e7", fontWeight: 500 }}>
                {stats?.active_sender ? (stats.active_sender.length > 18 ? stats.active_sender.slice(0, 15) + "…" : stats.active_sender) : "None"}
              </span>
              <span style={{ fontSize: "9px", color: "#10b981", backgroundColor: "rgba(16,185,129,0.12)", border: "1px solid rgba(16,185,129,0.25)", padding: "1px 5px", borderRadius: "3px" }}>
                {accounts.filter(a => a.status === 'ACTIVE').length} live
              </span>
            </div>

            <span style={{ color: "#27272a" }}>•</span>

            <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
              <span style={{ color: "#71717a" }}>Today:</span>
              <span style={{ color: "#00f2fe", fontWeight: 600 }}>{stats?.sent_today || 0}</span>
              <span style={{ color: "#52525b" }}>/ {stats?.daily_limit || 200}</span>
            </div>

            <span style={{ color: "#27272a" }}>•</span>

            <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
              <span style={{ color: "#71717a" }}>AI:</span>
              <span style={{ color: "#a1a1aa" }}>
                fast (Kimi + Groq fallback)
              </span>
            </div>
          </div>
        </div>

        {/* Action Controls - Ultra-Sleek Pill Buttons */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          {/* Fast Harvest Button */}
          <button
            onClick={triggerHarvest}
            disabled={harvesting}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "4px",
              backgroundColor: "rgba(0, 242, 254, 0.06)",
              color: "#38bdf8",
              border: "1px solid rgba(0, 242, 254, 0.22)",
              padding: "4px 10px",
              borderRadius: "5px",
              fontSize: "11px",
              fontWeight: 600,
              cursor: harvesting ? "not-allowed" : "pointer",
              transition: "all 0.15s ease",
            }}
          >
            <Zap size={11} color="#00f2fe" />
            {harvesting ? "SEARCHING..." : "SEARCH NOW"}
          </button>

          {/* Auto-Send Toggle Button */}
          <button
            onClick={toggleAutoSend}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "5px",
              backgroundColor: stats?.auto_send ? (senderCoolingDown ? "rgba(245, 158, 11, 0.12)" : "rgba(16, 185, 129, 0.12)") : "rgba(239, 68, 68, 0.12)",
              color: stats?.auto_send ? (senderCoolingDown ? "#fbbf24" : "#34d399") : "#f87171",
              border: `1px solid ${stats?.auto_send ? (senderCoolingDown ? "rgba(245, 158, 11, 0.28)" : "rgba(16, 185, 129, 0.28)") : "rgba(239, 68, 68, 0.28)"}`,
              padding: "4px 10px",
              borderRadius: "5px",
              fontSize: "11px",
              fontWeight: 600,
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            <span style={{ width: "5px", height: "5px", borderRadius: "50%", backgroundColor: stats?.auto_send ? (senderCoolingDown ? "#fbbf24" : "#34d399") : "#f87171" }} />
            {senderCoolingDown ? "COOLDOWN" : stats?.auto_send ? "AUTO-SEND: ON" : "AUTO-SEND: OFF"}
          </button>

          {/* 24/7 Master Engine Toggle */}
          <button
            onClick={toggleWorker}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "4px",
              backgroundColor: stats?.worker_running ? "rgba(16, 185, 129, 0.08)" : "rgba(239, 68, 68, 0.08)",
              color: stats?.worker_running ? "#10b981" : "#ef4444",
              border: `1px solid ${stats?.worker_running ? "rgba(16, 185, 129, 0.22)" : "rgba(239, 68, 68, 0.22)"}`,
              padding: "4px 10px",
              borderRadius: "5px",
              fontSize: "11px",
              fontWeight: 600,
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            {stats?.worker_running ? <Pause size={11} /> : <Play size={11} />}
            {stats?.worker_running ? "ENGINE ON" : "PAUSED"}
          </button>
        </div>
      </header>

      {/* Compact Modern KPI Stats Bar */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(145px, 1fr))",
          gap: "8px",
          padding: "10px 20px",
          borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
          backgroundColor: "rgba(5, 5, 8, 0.6)",
        }}
      >
        <KpiCard title="TOTAL LEADS" value={stats?.total_leads || 0} sub="Continuous UK Harvester" icon={<Globe color="#00f2fe" size={13} />} />
        <KpiCard title="CONNECTED SENDERS" value={`${accounts.filter(a => a.status === 'ACTIVE').length} / ${accounts.length}`} sub={`Daily Cap: ${stats?.daily_limit || 200}`} icon={<Key color="#38bdf8" size={13} />} />
        <KpiCard title="SENT TODAY" value={`${stats?.sent_today || 0} / ${stats?.daily_limit || 200}`} sub="Multi-account balanced" icon={<Send color="#3b82f6" size={13} />} />
        <KpiCard title="ACTIVE CONVERSATIONS" value={stats?.negotiating || 0} sub="Auto-Chat Responding" icon={<MessageSquare color="#f59e0b" size={13} />} />
        <KpiCard title="DELIVERED (HOLD)" value={outreach.filter(o => o.status === 'SENT' && (!Array.isArray(o.history) || !o.history.some(h => typeof h === 'object' && h && String(h.sender || '').toLowerCase() === 'client'))).length} sub="Awaiting client reply" icon={<EyeOff color="#a855f7" size={13} />} />
        <KpiCard title="PERMANENT BOUNCES" value={stats?.failed || 0} sub="Address not found" icon={<XCircle color="#ef4444" size={13} />} isError={stats?.failed > 0} />
        <KpiCard title="MEETINGS BOOKED" value={stats?.meeting_booked || 0} sub={`Base: ${stats?.starting_price || '£129'}`} icon={<Calendar color="#10b981" size={13} />} />
      </div>

      {senderCoolingDown && (
        <div style={{ margin: "10px 20px 0", padding: "10px 14px", border: "1px solid #6b4e12", borderRadius: "6px", background: "#1b1609", color: "#fbbf24", fontSize: "11px", display: "flex", alignItems: "center", gap: "8px" }}>
          <Clock size={14} /> All connected Gmail limits reached for today. Automatic sending resumes at {senderResumeLabel} IST.
        </div>
      )}

      {/* Tab Navigation */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "10px 20px 0px 20px",
        }}
      >
        <div style={{ display: "flex", gap: "6px" }}>
          <TabButton active={activeTab === "messages"} onClick={() => setActiveTab("messages")} icon={<Mail size={13} />} label={`Outreach & Live Chat (${outreach.length})`} />
          <TabButton active={activeTab === "leads"} onClick={() => setActiveTab("leads")} icon={<Users size={13} />} label={`Discovered Leads (${leads.length})`} />
          <TabButton active={activeTab === "accounts"} onClick={() => setActiveTab("accounts")} icon={<ShieldCheck size={13} />} label={`Gmail Senders & Quota (${accounts.length})`} />
          <TabButton active={activeTab === "terminal"} onClick={() => setActiveTab("terminal")} icon={<Terminal size={13} />} label="24/7 Agent Terminal Logs" />
        </div>

        {activeTab === "leads" && (
          <div style={{ position: "relative", width: "240px" }}>
            <Search size={13} style={{ position: "absolute", left: "9px", top: "8px", color: "#71717a" }} />
            <input
              type="text"
              placeholder="Search leads, gmails..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{
                width: "100%",
                padding: "6px 10px 6px 28px",
                backgroundColor: "#0d0d10",
                border: "1px solid rgba(255, 255, 255, 0.08)",
                borderRadius: "5px",
                color: "#fff",
                fontSize: "11px",
                outline: "none",
              }}
            />
          </div>
        )}
      </div>

      {/* Main Content Area */}
      <main style={{ padding: "14px 20px 50px 20px" }}>
        {/* TAB 1: Outreach & Live Chat */}
        {activeTab === "messages" && (
          <div>
            {/* Sender Account Filter Bar */}
            {accounts.length > 0 && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  flexWrap: "wrap",
                  marginBottom: "10px",
                  padding: "8px 14px",
                  backgroundColor: "#07070a",
                  border: "1px solid #16161f",
                  borderRadius: "6px",
                }}
              >
                <span style={{ fontSize: "11px", fontWeight: 700, color: "#71717a", textTransform: "uppercase", display: "flex", alignItems: "center", gap: "4px" }}>
                  <Mail size={12} color="#00f2fe" /> Sender Account:
                </span>
                <button
                  onClick={() => setSenderFilter("ALL")}
                  style={{
                    padding: "3px 10px",
                    borderRadius: "4px",
                    fontSize: "11px",
                    fontWeight: 700,
                    cursor: "pointer",
                    backgroundColor: senderFilter === "ALL" ? "#1e1e24" : "transparent",
                    color: senderFilter === "ALL" ? "#00f2fe" : "#71717a",
                    border: `1px solid ${senderFilter === "ALL" ? "#383844" : "#1a1a20"}`,
                  }}
                >
                  All Senders ({outreach.length})
                </button>
                {accounts.map((acc) => {
                  const count = outreach.filter((o) => o.assigned_sender === acc.email).length;
                  const isSelected = senderFilter === acc.email;
                  return (
                    <button
                      key={acc.email}
                      onClick={() => setSenderFilter(acc.email)}
                      style={{
                        padding: "3px 10px",
                        borderRadius: "4px",
                        fontSize: "11px",
                        fontWeight: 700,
                        cursor: "pointer",
                        backgroundColor: isSelected ? "#0e1a24" : "transparent",
                        color: isSelected ? "#38bdf8" : "#888899",
                        border: `1px solid ${isSelected ? "#1e3c54" : "#1a1a20"}`,
                        fontFamily: "JetBrains Mono",
                      }}
                    >
                      {acc.email} ({count})
                    </button>
                  );
                })}
              </div>
            )}

            {/* Filter Pills and Quick Search Bar */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px", flexWrap: "wrap", gap: "10px" }}>
              <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                {[
                  { id: "ALL", label: `ALL (${outreach.length})` },
                  { id: "CHATS", label: `ACTIVE CHATS (${outreach.filter(o => o.status === 'NEGOTIATING' || o.status === 'MEETING_BOOKED').length})` },
                  { id: "SEEN_NO_REPLY", label: `SEEN / NO REPLY (${outreach.filter(o => o.status === 'SENT' && (!Array.isArray(o.history) || !o.history.some(h => typeof h === 'object' && h && String(h.sender || '').toLowerCase() === 'client'))).length})` },
                  { id: "SENT", label: `ALL DELIVERED (${outreach.filter(o => o.status === 'SENT').length})` },
                  { id: "DRAFTED", label: `DRAFTS READY (${outreach.filter(o => o.status === 'DRAFTED' || o.status === 'SENDING').length})` },
                  { id: "NEW", label: `QUEUED (${outreach.filter(o => o.status === 'NEW').length})` },
                  { id: "FAILED", label: `FAILED (${outreach.filter(o => o.status === 'FAILED').length})` },
                ].map((btn) => (
                  <button
                    key={btn.id}
                    onClick={() => setOutreachFilter(btn.id)}
                    style={{
                      padding: "5px 12px",
                      borderRadius: "6px",
                      fontSize: "11px",
                      fontWeight: 700,
                      cursor: "pointer",
                      backgroundColor: outreachFilter === btn.id ? "#1e1e24" : "#0d0d10",
                      color: outreachFilter === btn.id ? "#00f2fe" : "#71717a",
                      border: `1px solid ${outreachFilter === btn.id ? "#383844" : "#1a1a20"}`,
                    }}
                  >
                    {btn.label}
                  </button>
                ))}
              </div>

              <div style={{ position: "relative", width: "240px" }}>
                <Search size={13} style={{ position: "absolute", left: "10px", top: "9px", color: "#71717a" }} />
                <input
                  type="text"
                  placeholder="Filter name, email, subject..."
                  value={outreachSearch}
                  onChange={(e) => setOutreachSearch(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "7px 10px 7px 30px",
                    backgroundColor: "#0a0a0d",
                    border: "1px solid #1a1a22",
                    borderRadius: "6px",
                    color: "#fff",
                    fontSize: "11px",
                    outline: "none",
                  }}
                />
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: selectedMessage ? "1fr 1fr" : "1fr", gap: "16px" }}>
              <div
                style={{
                  backgroundColor: "#070709",
                  border: "1px solid #17171c",
                  borderRadius: "8px",
                  overflow: "hidden",
                }}
              >
                <div style={{ padding: "12px 16px", borderBottom: "1px solid #18181e", fontSize: "13px", fontWeight: 700, display: "flex", justifyContent: "space-between" }}>
                  <span>OUTREACH THREADS ({filteredOutreach.length})</span>
                  <span style={{ fontSize: "11px", color: "#71717a", fontWeight: 400 }}>Click any thread to inspect or reply</span>
                </div>
                <div style={{ maxHeight: "720px", overflowY: "auto" }}>
                  {filteredOutreach.length === 0 ? (
                    <div style={{ padding: "30px", textAlign: "center", color: "#71717a", fontSize: "12px" }}>
                      No outreach records match the selected filter.
                    </div>
                  ) : (
                    filteredOutreach.map((item, idx) => (
                      <div
                        key={item.email}
                        onClick={() => {
                          setSelectedMessageEmail(item.email);
                          setManualReply("");
                        }}
                        style={{
                          padding: "14px 16px",
                          borderBottom: "1px solid #121216",
                          cursor: "pointer",
                          backgroundColor: selectedMessage?.email === item.email ? "#111116" : "transparent",
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#0f0f13")}
                        onMouseLeave={(e) =>
                          (e.currentTarget.style.backgroundColor = selectedMessage?.email === item.email ? "#111116" : "transparent")
                        }
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                          <span style={{ fontWeight: 600, color: "#fff", fontSize: "13px" }}>{item.business_name}</span>
                          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                            {item.status === "SENT" && (!Array.isArray(item.history) || !item.history.some(h => typeof h === 'object' && h && String(h.sender || '').toLowerCase() === 'client')) && (
                              <span style={{ fontSize: "10px", fontWeight: 700, padding: "2px 6px", borderRadius: "4px", backgroundColor: "#1e102e", color: "#c084fc", border: "1px solid #3b1d61", display: "flex", alignItems: "center", gap: "3px" }}>
                                <EyeOff size={10} /> SEEN / NO REPLY
                              </span>
                            )}
                            <StatusBadge status={item.status} />
                          </div>
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", marginBottom: "4px" }}>
                          <span style={{ color: "#00f2fe", fontFamily: "JetBrains Mono" }}>{item.email}</span>
                          {item.assigned_sender && (
                            <span style={{ color: "#a1a1aa", fontSize: "10px" }}>Via: {item.assigned_sender}</span>
                          )}
                        </div>

                        {item.error_message && (
                          <div style={{ color: "#ef4444", fontSize: "11px", fontWeight: 600, marginBottom: "4px", display: "flex", alignItems: "center", gap: "4px" }}>
                            <AlertTriangle size={12} /> NOTICE: {item.error_message}
                          </div>
                        )}

                        <div style={{ fontSize: "12px", color: "#d4d4d8", fontWeight: 500 }}>
                          Subject: {item.subject}
                        </div>
                        <div
                          style={{
                            fontSize: "11px",
                            color: "#71717a",
                            marginTop: "4px",
                            whiteSpace: "nowrap",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                          }}
                        >
                          {item.body}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Interactive Detail & Reply Panel */}
              {selectedMessage && (
                <div
                  style={{
                    backgroundColor: "#070709",
                    border: "1px solid #1e1e24",
                    borderRadius: "8px",
                    padding: "20px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "14px",
                    maxHeight: "750px",
                    overflowY: "auto",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", borderBottom: "1px solid #18181e", paddingBottom: "12px" }}>
                    <div>
                      <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#fff" }}>{selectedMessage.business_name}</h3>
                      <p style={{ fontSize: "12px", color: "#00f2fe", fontFamily: "JetBrains Mono" }}>{selectedMessage.email}</p>
                      <p style={{ fontSize: "11px", color: "#71717a" }}>
                        Contact: {selectedMessage.contact_person} | Sender: {selectedMessage.assigned_sender || "Assigned on Dispatch"}
                      </p>
                    </div>
                    <button
                      onClick={() => setSelectedMessageEmail(null)}
                      style={{ background: "none", border: "none", color: "#71717a", cursor: "pointer", fontSize: "14px" }}
                    >
                      ✕ Close
                    </button>
                  </div>

                  {selectedMessage.error_message && (
                    <div
                      style={{
                        backgroundColor: "#241010",
                        border: "1px solid #571b1b",
                        borderRadius: "6px",
                        padding: "10px 14px",
                        color: "#f87171",
                        fontSize: "12px",
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                      }}
                    >
                      <AlertTriangle size={16} />
                      <span><strong>Notice:</strong> {selectedMessage.error_message}</span>
                    </div>
                  )}

                  <div>
                    <div style={{ fontSize: "10px", color: "#71717a", textTransform: "uppercase", marginBottom: "4px", fontWeight: 700 }}>
                      Subject Line
                    </div>
                    <div style={{ fontSize: "13px", fontWeight: 600, color: "#fff", backgroundColor: "#0f0f13", padding: "8px 12px", borderRadius: "6px" }}>
                      {selectedMessage.subject}
                    </div>
                  </div>

                  <div>
                    <div style={{ fontSize: "10px", color: "#71717a", textTransform: "uppercase", marginBottom: "4px", fontWeight: 700 }}>
                      Personalized Pitch Body
                    </div>
                    <div
                      style={{
                        fontSize: "12px",
                        lineHeight: "1.5",
                        color: "#d4d4d8",
                        backgroundColor: "#0c0c0f",
                        border: "1px solid #17171c",
                        padding: "12px",
                        borderRadius: "6px",
                        whiteSpace: "pre-line",
                        maxHeight: "130px",
                        overflowY: "auto",
                      }}
                    >
                      {renderPortfolioLinks(selectedMessage.body)}
                    </div>
                  </div>

                  {/* Conversation Thread */}
                  <div>
                    <div style={{ fontSize: "10px", color: "#10b981", textTransform: "uppercase", marginBottom: "6px", fontWeight: 700 }}>
                      Live Conversation Thread ({selectedMessage.history ? selectedMessage.history.length : 0})
                    </div>
                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: "8px",
                        maxHeight: "180px",
                        overflowY: "auto",
                        paddingRight: "4px",
                      }}
                    >
                      {(!selectedMessage.history || selectedMessage.history.length === 0) && (
                        <div style={{ fontSize: "11px", color: "#52525b", fontStyle: "italic", padding: "8px" }}>
                          Awaiting client reply or initial dispatch...
                        </div>
                      )}
                      {selectedMessage.history &&
                        selectedMessage.history.map((msg, i) => (
                          <div
                            key={i}
                            style={{
                              padding: "10px 12px",
                              borderRadius: "6px",
                              fontSize: "12px",
                              lineHeight: "1.4",
                              backgroundColor: msg.sender === "Client" ? "#1a160c" : "#0e1724",
                              border: `1px solid ${msg.sender === "Client" ? "#4a3310" : "#1a2c45"}`,
                              alignSelf: msg.sender === "Client" ? "flex-start" : "flex-end",
                              maxWidth: "92%",
                            }}
                          >
                            <div
                              style={{
                                display: "flex",
                                justifyContent: "space-between",
                                gap: "10px",
                                fontSize: "10px",
                                fontWeight: 700,
                                color: msg.sender === "Client" ? "#f59e0b" : "#38bdf8",
                                marginBottom: "4px",
                              }}
                            >
                              <span>{msg.sender === "Client" ? "CLIENT" : (msg.sender_email ? `YOU (${msg.sender_email})` : "YOU")}</span>
                              <span style={{ color: "#71717a" }}>{msg.timestamp}</span>
                            </div>
                            <div style={{ color: "#e4e4e7", whiteSpace: "pre-wrap" }}>{renderPortfolioLinks(msg.text)}</div>
                          </div>
                        ))}
                    </div>
                  </div>

                  {/* Reply Input Box */}
                  <div style={{ borderTop: "1px solid #18181e", paddingTop: "12px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                      <span style={{ fontSize: "11px", fontWeight: 600, color: "#fff", display: "flex", alignItems: "center", gap: "6px" }}>
                        <Send size={12} /> Send Direct Message / Reply:
                      </span>
                      <button
                        onClick={handleSuggestReply}
                        disabled={suggestingReply}
                        style={{
                          background: "none",
                          border: "none",
                          color: "#a855f7",
                          cursor: "pointer",
                          fontSize: "11px",
                          fontWeight: 600,
                          display: "flex",
                          alignItems: "center",
                          gap: "4px",
                        }}
                      >
                        <Sparkles size={12} />
                        {suggestingReply ? "Generating..." : "AI Auto-Suggest"}
                      </button>
                    </div>

                    <textarea
                      value={manualReply}
                      onChange={(e) => setManualReply(e.target.value)}
                      placeholder={`Type your reply to ${selectedMessage.contact_person || 'Business Owner'} (e.g. quote price ₹2,000, send Google Meet link, or answer question)...`}
                      style={{
                        width: "100%",
                        height: "75px",
                        backgroundColor: "#040405",
                        border: "1px solid #24242d",
                        borderRadius: "6px",
                        color: "#fff",
                        padding: "10px",
                        fontSize: "12px",
                        lineHeight: "1.4",
                        outline: "none",
                        resize: "none",
                      }}
                    />

                    <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "8px" }}>
                      <button
                        onClick={handleSendManualReply}
                        disabled={sendingReply || !manualReply.trim()}
                        style={{
                          backgroundColor: manualReply.trim() ? "#00f2fe" : "#1e1e24",
                          color: manualReply.trim() ? "#000" : "#71717a",
                          border: "none",
                          borderRadius: "6px",
                          padding: "8px 16px",
                          fontSize: "12px",
                          fontWeight: 700,
                          cursor: manualReply.trim() ? "pointer" : "not-allowed",
                          display: "flex",
                          alignItems: "center",
                          gap: "6px",
                        }}
                      >
                        <Send size={12} />
                        {sendingReply ? "SENDING..." : "SEND REPLY DIRECTLY"}
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 2: Discovered Leads Table */}
        {activeTab === "leads" && (
          <div
            style={{
              backgroundColor: "#070709",
              border: "1px solid #17171c",
              borderRadius: "8px",
              overflow: "hidden",
            }}
          >
            <div style={{ padding: "12px 16px", borderBottom: "1px solid #18181e", fontSize: "12px", color: "#a1a1aa" }}>
              Showing {filteredLeads.length} genuine leads. <em>Tip: Click any row to view in Outreach & Chat.</em>
            </div>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #1a1a20", textAlign: "left", color: "#71717a", backgroundColor: "#0b0b0e" }}>
                  <th style={{ padding: "12px 16px" }}>BUSINESS NAME</th>
                  <th style={{ padding: "12px 16px" }}>VERIFIED GMAIL</th>
                  <th style={{ padding: "12px 16px" }}>CONTACT PERSON</th>
                  <th style={{ padding: "12px 16px" }}>CATEGORY</th>
                  <th style={{ padding: "12px 16px" }}>LOCATION</th>
                  <th style={{ padding: "12px 16px" }}>WEBSITE</th>
                  <th style={{ padding: "12px 16px" }}>STATUS</th>
                </tr>
              </thead>
              <tbody>
                {filteredLeads.map((lead, idx) => (
                  <tr
                    key={idx}
                    onClick={() => {
                      const match = outreach.find(o => o.email === lead.email);
                      if (match) setSelectedMessageEmail(match.email);
                      setActiveTab("messages");
                    }}
                    style={{
                      borderBottom: "1px solid #121215",
                      cursor: "pointer",
                      transition: "background 0.2s",
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#0d0d11")}
                    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
                  >
                    <td style={{ padding: "12px 16px", fontWeight: 600, color: "#ffffff" }}>
                      {lead.business_name}
                      {lead.error_message && (
                        <div style={{ color: "#ef4444", fontSize: "10px", fontWeight: 500, marginTop: "2px" }}>
                          ⚠ {lead.error_message}
                        </div>
                      )}
                    </td>
                    <td style={{ padding: "12px 16px", fontFamily: "JetBrains Mono", color: "#00f2fe" }}>
                      {lead.email}
                    </td>
                    <td style={{ padding: "12px 16px", color: "#a1a1aa" }}>{lead.contact_person}</td>
                    <td style={{ padding: "12px 16px", color: "#a1a1aa" }}>{lead.category}</td>
                    <td style={{ padding: "12px 16px", color: "#71717a", maxWidth: "180px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {lead.address}
                    </td>
                    <td style={{ padding: "12px 16px" }}>
                      {lead.website ? (
                        <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                          <span style={{ color: "#38bdf8", fontSize: "11px", fontFamily: "JetBrains Mono" }}>{lead.website.replace(/^https?:\/\//, '')}</span>
                          {lead.website_issues && lead.website_issues.length > 0 && (
                            <span
                              title={lead.website_issues.join(", ")}
                              style={{ color: "#fbbf24", fontSize: "9px", fontWeight: 700, backgroundColor: "rgba(245, 158, 11, 0.15)", border: "1px solid rgba(245, 158, 11, 0.3)", padding: "1px 5px", borderRadius: "3px", width: "fit-content" }}
                            >
                              ⚠ {lead.website_issues.length} ISSUES FOUND
                            </span>
                          )}
                        </div>
                      ) : (
                        <span style={{ color: "#f87171", fontSize: "10px", fontWeight: 700, backgroundColor: "#2b1414", padding: "2px 6px", borderRadius: "4px" }}>NO WEBSITE</span>
                      )}
                    </td>
                    <td style={{ padding: "12px 16px" }}>
                      <StatusBadge status={lead.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* TAB 3: Gmail Senders & Quota Management (Admin Panel) */}
        {activeTab === "accounts" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            {/* Top Setup & Direct Link Card */}
            <div
              style={{
                backgroundColor: "#070709",
                border: "1px solid #1c1c24",
                borderRadius: "8px",
                padding: "20px 24px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexWrap: "wrap",
                gap: "16px",
              }}
            >
              <div>
                <h2 style={{ fontSize: "16px", fontWeight: 700, color: "#fff", display: "flex", alignItems: "center", gap: "8px" }}>
                  <ShieldCheck size={18} color="#00f2fe" /> Multi-Gmail Auto-Rotation & Failover Admin Panel
                </h2>
                <p style={{ fontSize: "12px", color: "#a1a1aa", marginTop: "4px", maxWidth: "680px", lineHeight: "1.5" }}>
                  Add multiple Gmail accounts here. The dispatcher rotates them fairly according to daily quotas.
                  If one Gmail hits its daily sending limit (or 5.4.5 error), it <strong>automatically switches to the next account without stopping</strong>, and conversation replies always continue with the original sender!
                </p>
              </div>

              <a
                href="https://myaccount.google.com/apppasswords"
                target="_blank"
                rel="noreferrer"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  backgroundColor: "#00f2fe",
                  color: "#000",
                  padding: "9px 16px",
                  borderRadius: "6px",
                  fontSize: "12px",
                  fontWeight: 700,
                  textDecoration: "none",
                }}
              >
                <ExternalLink size={14} /> Open Google App Passwords Setup ↗
              </a>
            </div>

            {/* Quick 3-Step Guide */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
                gap: "12px",
              }}
            >
              <div style={{ backgroundColor: "#09090d", border: "1px solid #17171f", padding: "14px", borderRadius: "6px" }}>
                <div style={{ color: "#00f2fe", fontWeight: 700, fontSize: "12px", marginBottom: "4px" }}>STEP 1: 2-Step Verification</div>
                <div style={{ color: "#71717a", fontSize: "11px", lineHeight: "1.4" }}>
                  Ensure 2-Step Verification is enabled in your Google Account Security settings.
                </div>
              </div>
              <div style={{ backgroundColor: "#09090d", border: "1px solid #17171f", padding: "14px", borderRadius: "6px" }}>
                <div style={{ color: "#a855f7", fontWeight: 700, fontSize: "12px", marginBottom: "4px" }}>STEP 2: Generate App Password</div>
                <div style={{ color: "#71717a", fontSize: "11px", lineHeight: "1.4" }}>
                  Go to <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noreferrer" style={{ color: "#a855f7" }}>App Passwords</a>, name it "Outreach", and copy the 16-character code.
                </div>
              </div>
              <div style={{ backgroundColor: "#09090d", border: "1px solid #17171f", padding: "14px", borderRadius: "6px" }}>
                <div style={{ color: "#10b981", fontWeight: 700, fontSize: "12px", marginBottom: "4px" }}>STEP 3: Connect & Authenticate</div>
                <div style={{ color: "#71717a", fontSize: "11px", lineHeight: "1.4" }}>
                  Paste below and click Authenticate. Both SMTP & IMAP will be tested and activated live.
                </div>
              </div>
            </div>

            {/* Google App Password Troubleshooting Alert */}
            <div
              style={{
                backgroundColor: "#080c14",
                border: "1px solid #17253b",
                borderRadius: "6px",
                padding: "12px 16px",
                display: "flex",
                alignItems: "flex-start",
                gap: "12px",
              }}
            >
              <AlertTriangle size={16} color="#38bdf8" style={{ marginTop: "2px", flexShrink: 0 }} />
              <div style={{ fontSize: "11px", color: "#94a3b8", lineHeight: "1.5" }}>
                <strong style={{ color: "#38bdf8" }}>Google App Passwords Troubleshooting:</strong> If you see <em>"The setting that you are looking for is not available for your account"</em>, make sure <strong>2-Step Verification (2FA)</strong> is turned ON in Google Account &gt; Security settings. Google hides App Passwords if 2FA is off. Once enabled, search <strong>"App passwords"</strong> directly in the search bar of <a href="https://myaccount.google.com" target="_blank" rel="noreferrer" style={{ color: "#00f2fe" }}>myaccount.google.com</a>. Both <code>dixitshubham68359@gmail.com</code> &amp; <code>sd5630074@gmail.com</code> are already 100% authenticated and active in this system!
              </div>
            </div>

            {/* Add Account Form & Live Verification */}
            <div
              style={{
                backgroundColor: "#070709",
                border: "1px solid #1c1c24",
                borderRadius: "8px",
                padding: "20px 24px",
              }}
            >
              <h3 style={{ fontSize: "14px", fontWeight: 700, color: "#fff", marginBottom: "14px", display: "flex", alignItems: "center", gap: "8px" }}>
                <Plus size={16} color="#00f2fe" /> Connect New Gmail Account
              </h3>

              {accountActionMessage && (
                <div
                  style={{
                    padding: "10px 14px",
                    borderRadius: "6px",
                    fontSize: "12px",
                    marginBottom: "14px",
                    backgroundColor: accountActionMessage.type === "success" ? "#062419" : accountActionMessage.type === "error" ? "#290c0c" : "#161622",
                    border: `1px solid ${accountActionMessage.type === "success" ? "#0d543b" : accountActionMessage.type === "error" ? "#541919" : "#2d2d3d"}`,
                    color: accountActionMessage.type === "success" ? "#34d399" : accountActionMessage.type === "error" ? "#f87171" : "#38bdf8",
                  }}
                >
                  {accountActionMessage.text}
                </div>
              )}

              <form onSubmit={handleAddAccount} style={{ display: "grid", gridTemplateColumns: "2fr 2fr 1.5fr 1fr auto", gap: "12px", alignItems: "flex-end" }}>
                <div>
                  <label style={{ display: "block", fontSize: "10px", fontWeight: 700, color: "#71717a", textTransform: "uppercase", marginBottom: "6px" }}>
                    Gmail Address
                  </label>
                  <input
                    type="email"
                    placeholder="e.g. shubham.agency@gmail.com"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    required
                    style={{
                      width: "100%",
                      padding: "9px 12px",
                      backgroundColor: "#0d0d12",
                      border: "1px solid #22222a",
                      borderRadius: "6px",
                      color: "#fff",
                      fontSize: "12px",
                      outline: "none",
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "10px", fontWeight: 700, color: "#71717a", textTransform: "uppercase", marginBottom: "6px" }}>
                    16-Character App Password
                  </label>
                  <input
                    type="password"
                    placeholder="xxxx xxxx xxxx xxxx"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    required
                    style={{
                      width: "100%",
                      padding: "9px 12px",
                      backgroundColor: "#0d0d12",
                      border: "1px solid #22222a",
                      borderRadius: "6px",
                      color: "#fff",
                      fontSize: "12px",
                      outline: "none",
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "10px", fontWeight: 700, color: "#71717a", textTransform: "uppercase", marginBottom: "6px" }}>
                    Sender Name
                  </label>
                  <input
                    type="text"
                    placeholder="Shubham Dixit"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "9px 12px",
                      backgroundColor: "#0d0d12",
                      border: "1px solid #22222a",
                      borderRadius: "6px",
                      color: "#fff",
                      fontSize: "12px",
                      outline: "none",
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "10px", fontWeight: 700, color: "#71717a", textTransform: "uppercase", marginBottom: "6px" }}>
                    Daily Quota
                  </label>
                  <input
                    type="number"
                    min="10"
                    max="500"
                    value={newLimit}
                    onChange={(e) => setNewLimit(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "9px 12px",
                      backgroundColor: "#0d0d12",
                      border: "1px solid #22222a",
                      borderRadius: "6px",
                      color: "#fff",
                      fontSize: "12px",
                      outline: "none",
                    }}
                  />
                </div>

                <button
                  type="submit"
                  disabled={addingAccount}
                  style={{
                    backgroundColor: "#00f2fe",
                    color: "#000",
                    border: "none",
                    borderRadius: "6px",
                    padding: "9px 18px",
                    fontSize: "12px",
                    fontWeight: 700,
                    cursor: addingAccount ? "not-allowed" : "pointer",
                    height: "36px",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    whiteSpace: "nowrap",
                  }}
                >
                  <Plus size={14} />
                  {addingAccount ? "Testing & Adding..." : "Connect Gmail"}
                </button>
              </form>
            </div>

            {/* Connected Accounts - Dedicated Section for Each Gmail */}
            <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
                <div>
                  <h3 style={{ fontSize: "15px", fontWeight: 700, color: "#fff", display: "flex", alignItems: "center", gap: "8px" }}>
                    <ShieldCheck size={18} color="#00f2fe" /> CONNECTED GMAIL SENDERS &amp; ACTIVITY SECTIONS ({accounts.length})
                  </h3>
                  <p style={{ fontSize: "12px", color: "#71717a", marginTop: "2px" }}>
                    Total Daily Quota: {accounts.reduce((sum, a) => sum + (a.daily_limit || 0), 0)} emails/day · Dispatched Today: {accounts.reduce((sum, a) => sum + (a.sent_today || 0), 0)}
                  </p>
                </div>
              </div>

              {accounts.length === 0 ? (
                <div style={{ padding: "40px", textAlign: "center", color: "#71717a", fontSize: "13px", backgroundColor: "#070709", border: "1px solid #1c1c24", borderRadius: "8px" }}>
                  No Gmail accounts connected yet. Add your Gmail above to begin auto-rotation!
                </div>
              ) : (
                accounts.map((acc, idx) => {
                  const pct = Math.min(100, Math.round(((acc.sent_today || 0) / (acc.daily_limit || 200)) * 100));
                  const remainingQuota = Math.max(0, (acc.daily_limit || 200) - (acc.sent_today || 0));

                  return (
                    <div
                      key={acc.email || idx}
                      style={{
                        backgroundColor: "#070709",
                        border: `1px solid ${acc.status === "ACTIVE" ? "#1e293b" : "#331a1a"}`,
                        borderRadius: "10px",
                        padding: "20px 24px",
                        display: "flex",
                        flexDirection: "column",
                        gap: "18px",
                      }}
                    >
                      {/* Section Header */}
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px", borderBottom: "1px solid #14141c", paddingBottom: "14px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                          <div
                            style={{
                              width: "40px",
                              height: "40px",
                              borderRadius: "8px",
                              backgroundColor: "#0f172a",
                              border: "1px solid #1e3a5f",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              color: "#00f2fe",
                            }}
                          >
                            <Mail size={20} />
                          </div>
                          <div>
                            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                              <span style={{ fontSize: "15px", fontWeight: 700, color: "#fff", fontFamily: "JetBrains Mono" }}>
                                {acc.email}
                              </span>
                              <span
                                style={{
                                  fontSize: "10px",
                                  fontWeight: 800,
                                  padding: "3px 8px",
                                  borderRadius: "4px",
                                  backgroundColor: acc.status === "ACTIVE" ? "#062419" : acc.status === "QUOTA_EXCEEDED" ? "#291b07" : "#241818",
                                  color: acc.status === "ACTIVE" ? "#34d399" : acc.status === "QUOTA_EXCEEDED" ? "#fbbf24" : "#f87171",
                                  border: `1px solid ${acc.status === "ACTIVE" ? "#0d543b" : acc.status === "QUOTA_EXCEEDED" ? "#59390c" : "#4a2424"}`,
                                }}
                              >
                                {acc.status}
                              </span>
                            </div>
                            <div style={{ fontSize: "11px", color: "#71717a", marginTop: "3px" }}>
                              Sender Name: <strong style={{ color: "#e4e4e7" }}>{acc.sender_name}</strong> · App Password: <span style={{ fontFamily: "JetBrains Mono" }}>{acc.app_password_masked}</span>
                            </div>
                            {acc.error_message && (
                              <div style={{ color: "#ef4444", fontSize: "11px", marginTop: "4px", fontWeight: 600 }}>
                                ⚠ {acc.error_message}
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Action Buttons */}
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <button
                            onClick={() => handleTestAccount(acc.email)}
                            disabled={testingEmail === acc.email}
                            style={{
                              backgroundColor: "#0e1a24",
                              color: "#38bdf8",
                              border: "1px solid #1c3c54",
                              borderRadius: "6px",
                              padding: "7px 14px",
                              fontSize: "11px",
                              fontWeight: 700,
                              cursor: "pointer",
                              display: "flex",
                              alignItems: "center",
                              gap: "6px",
                            }}
                          >
                            <Zap size={13} />
                            {testingEmail === acc.email ? "Testing..." : "Test Connection"}
                          </button>

                          <button
                            onClick={() => handleToggleAccount(acc.email)}
                            style={{
                              backgroundColor: acc.status === "ACTIVE" ? "#1e1717" : "#13241b",
                              color: acc.status === "ACTIVE" ? "#f87171" : "#34d399",
                              border: `1px solid ${acc.status === "ACTIVE" ? "#3b1d1d" : "#1a3b2b"}`,
                              borderRadius: "6px",
                              padding: "7px 14px",
                              fontSize: "11px",
                              fontWeight: 700,
                              cursor: "pointer",
                            }}
                          >
                            {acc.status === "ACTIVE" ? "Pause Sending" : "Resume Sending"}
                          </button>

                          <button
                            onClick={() => handleDeleteAccount(acc.email)}
                            style={{
                              backgroundColor: "#1f1111",
                              color: "#ef4444",
                              border: "1px solid #3b1919",
                              borderRadius: "6px",
                              padding: "7px 12px",
                              fontSize: "11px",
                              cursor: "pointer",
                              display: "flex",
                              alignItems: "center",
                            }}
                            title="Delete Account"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>

                      {/* 4 Metric Tiles Grid */}
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                          gap: "12px",
                        }}
                      >
                        {/* Sent Today */}
                        <div style={{ backgroundColor: "#0b0b10", border: "1px solid #181822", padding: "14px 16px", borderRadius: "8px" }}>
                          <div style={{ fontSize: "10px", color: "#71717a", fontWeight: 700, textTransform: "uppercase" }}>Sent Today / Limit</div>
                          <div style={{ fontSize: "20px", fontWeight: 800, color: "#fff", fontFamily: "JetBrains Mono", marginTop: "4px" }}>
                            {acc.sent_today || 0} <span style={{ fontSize: "13px", color: "#71717a" }}>/ {acc.daily_limit || 200}</span>
                          </div>
                          <div style={{ width: "100%", height: "5px", backgroundColor: "#171720", borderRadius: "3px", overflow: "hidden", marginTop: "8px" }}>
                            <div
                              style={{
                                width: `${pct}%`,
                                height: "100%",
                                backgroundColor: pct >= 100 ? "#ef4444" : pct >= 80 ? "#f59e0b" : "#10b981",
                              }}
                            />
                          </div>
                        </div>

                        {/* Lifetime Outreach */}
                        <div style={{ backgroundColor: "#0b0b10", border: "1px solid #181822", padding: "14px 16px", borderRadius: "8px" }}>
                          <div style={{ fontSize: "10px", color: "#71717a", fontWeight: 700, textTransform: "uppercase" }}>Lifetime Outreached</div>
                          <div style={{ fontSize: "20px", fontWeight: 800, color: "#00f2fe", fontFamily: "JetBrains Mono", marginTop: "4px" }}>
                            {acc.sent_lifetime || 0}
                          </div>
                          <div style={{ fontSize: "11px", color: "#52525b", marginTop: "4px" }}>Total businesses contacted</div>
                        </div>

                        {/* Active Client Conversations */}
                        <div style={{ backgroundColor: "#0b0b10", border: "1px solid #181822", padding: "14px 16px", borderRadius: "8px" }}>
                          <div style={{ fontSize: "10px", color: "#71717a", fontWeight: 700, textTransform: "uppercase" }}>Active Client Chats</div>
                          <div style={{ fontSize: "20px", fontWeight: 800, color: "#a855f7", fontFamily: "JetBrains Mono", marginTop: "4px" }}>
                            {acc.active_conversations_count || 0}
                          </div>
                          <div style={{ fontSize: "11px", color: "#52525b", marginTop: "4px" }}>Client replies on this Gmail</div>
                        </div>

                        {/* Quota Remaining */}
                        <div style={{ backgroundColor: "#0b0b10", border: "1px solid #181822", padding: "14px 16px", borderRadius: "8px" }}>
                          <div style={{ fontSize: "10px", color: "#71717a", fontWeight: 700, textTransform: "uppercase" }}>Remaining Today</div>
                          <div style={{ fontSize: "20px", fontWeight: 800, color: "#34d399", fontFamily: "JetBrains Mono", marginTop: "4px" }}>
                            {remainingQuota}
                          </div>
                          <div style={{ fontSize: "11px", color: "#52525b", marginTop: "4px" }}>Resets automatically at midnight</div>
                        </div>
                      </div>

                      {/* Recent Dispatches from THIS Gmail */}
                      <div style={{ backgroundColor: "#050508", border: "1px solid #14141c", borderRadius: "8px", padding: "14px 18px" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                          <span style={{ fontSize: "12px", fontWeight: 700, color: "#d4d4d8", display: "flex", alignItems: "center", gap: "6px" }}>
                            <Send size={13} color="#00f2fe" /> Recent Leads Contacted via {acc.email}
                          </span>
                          <span style={{ fontSize: "11px", color: "#71717a" }}>
                            {acc.recent_sends?.length || 0} recent record{acc.recent_sends?.length === 1 ? "" : "s"}
                          </span>
                        </div>

                        {(!acc.recent_sends || acc.recent_sends.length === 0) ? (
                          <div style={{ padding: "16px", textAlign: "center", color: "#71717a", fontSize: "12px", border: "1px dashed #1a1a24", borderRadius: "6px" }}>
                            ⚡ Ready to dispatch — queued drafts will automatically route to this account!
                          </div>
                        ) : (
                          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                            {acc.recent_sends.map((s, sIdx) => (
                              <div
                                key={sIdx}
                                style={{
                                  display: "flex",
                                  justifyContent: "space-between",
                                  alignItems: "center",
                                  padding: "8px 12px",
                                  backgroundColor: "#09090f",
                                  border: "1px solid #121218",
                                  borderRadius: "6px",
                                  fontSize: "11px",
                                }}
                              >
                                <div style={{ display: "flex", alignItems: "center", gap: "8px", minWidth: "200px" }}>
                                  <span style={{ fontWeight: 600, color: "#fff" }}>{s.business_name}</span>
                                  <span style={{ color: "#71717a", fontFamily: "JetBrains Mono" }}>&lt;{s.lead_email}&gt;</span>
                                </div>
                                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                                  <span
                                    style={{
                                      fontSize: "9px",
                                      fontWeight: 700,
                                      padding: "2px 6px",
                                      borderRadius: "4px",
                                      backgroundColor: s.status === "SENT" ? "#062419" : s.status === "FAILED" ? "#2b1111" : "#241829",
                                      color: s.status === "SENT" ? "#34d399" : s.status === "FAILED" ? "#f87171" : "#c084fc",
                                    }}
                                  >
                                    {s.status}
                                  </span>
                                  <span style={{ color: "#52525b", fontSize: "10px" }}>{s.timestamp}</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}

        {/* TAB 4: Terminal Logs */}
        {activeTab === "terminal" && (
          <div
            style={{
              backgroundColor: "#030303",
              border: "1px solid #1a1a20",
              borderRadius: "8px",
              padding: "16px",
              fontFamily: "JetBrains Mono",
              fontSize: "12px",
              minHeight: "450px",
              maxHeight: "650px",
              overflowY: "auto",
            }}
          >
            <div style={{ color: "#71717a", marginBottom: "12px", borderBottom: "1px solid #18181e", paddingBottom: "8px" }}>
              // LIVE AGENT REAL-TIME CONSOLE STREAM (POLLING EVERY 2.5 SECONDS)
            </div>
            {logs.map((log, i) => (
              <div key={i} style={{ color: log.includes("ERROR") || log.includes("Error") || log.includes("FAILED") ? "#ef4444" : log.includes("SENT SUCCESS") || log.includes("Harvested") || log.includes("MANUAL REPLY") || log.includes("AUTO-REPLY") ? "#10b981" : "#a1a1aa", lineHeight: "1.8" }}>
                {log}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

function KpiCard({ title, value, sub, icon, isError }) {
  return (
    <div
      style={{
        backgroundColor: isError ? "rgba(239, 68, 68, 0.05)" : "rgba(14, 14, 18, 0.65)",
        border: `1px solid ${isError ? "rgba(239, 68, 68, 0.22)" : "rgba(255, 255, 255, 0.05)"}`,
        borderRadius: "6px",
        padding: "8px 12px",
        display: "flex",
        flexDirection: "column",
        gap: "2px",
        transition: "all 0.15s ease",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: "9px", letterSpacing: "0.4px", color: isError ? "#f87171" : "#71717a", fontWeight: 700, fontFamily: "JetBrains Mono, monospace" }}>{title}</span>
        {icon}
      </div>
      <div style={{ fontSize: "18px", fontWeight: 700, color: isError ? "#ef4444" : "#ffffff", letterSpacing: "-0.4px", lineHeight: "1.2" }}>{value}</div>
      <div style={{ fontSize: "10px", color: isError ? "#fca5a5" : "#52525b", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{sub}</div>
    </div>
  );
}

function TabButton({ active, onClick, icon, label }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "6px",
        backgroundColor: active ? "rgba(255, 255, 255, 0.08)" : "transparent",
        color: active ? "#ffffff" : "#71717a",
        border: `1px solid ${active ? "rgba(255, 255, 255, 0.12)" : "transparent"}`,
        padding: "5px 12px",
        borderRadius: "5px",
        fontSize: "11px",
        fontWeight: 600,
        cursor: "pointer",
        transition: "all 0.15s ease",
      }}
    >
      {icon}
      {label}
    </button>
  );
}

function StatusBadge({ status }) {
  const map = {
    NEW: { label: "NEW IN QUEUE", bg: "#141416", border: "#222228", color: "#a1a1aa" },
    DRAFTED: { label: "DRAFT READY", bg: "#1e142e", border: "#3c2161", color: "#c084fc" },
    SENDING: { label: "SENDING NOW", bg: "#1e142e", border: "#3c2161", color: "#c084fc" },
    SENT: { label: "OUTREACH DELIVERED", bg: "#0c1f30", border: "#15416b", color: "#60a5fa" },
    NEGOTIATING: { label: "IN NEGOTIATION", bg: "#291b07", border: "#59390c", color: "#fbbf24" },
    MEETING_BOOKED: { label: "MEETING BOOKED", bg: "#062419", border: "#0d543b", color: "#34d399" },
    FAILED: { label: "DELIVERY FAILED", bg: "#290c0c", border: "#541919", color: "#ef4444" },
  };
  const b = map[status] || map.NEW;
  return (
    <span
      style={{
        backgroundColor: b.bg,
        border: `1px solid ${b.border}`,
        color: b.color,
        fontSize: "10px",
        fontWeight: 700,
        padding: "3px 8px",
        borderRadius: "4px",
        fontFamily: "JetBrains Mono",
        letterSpacing: "0.4px",
      }}
    >
      {b.label}
    </span>
  );
}
