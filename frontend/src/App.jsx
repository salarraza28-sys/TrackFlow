import React, { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart as RechartsPieChart, Pie, Cell
} from 'recharts';
import {
  Play, Pause, Activity, Clock, Layout, Monitor, Shield,
  RefreshCw, CheckCircle2, FileText, PieChart, Sparkles,
  AlertCircle, Loader2, History, Calendar, Keyboard, MousePointer
} from 'lucide-react';
import moment from 'moment';

const API_BASE = 'http://localhost:5173/api';

const COLORS = ['#3b82f6', '#8b5cf6', '#ec4899', '#f43f5e', '#f59e0b', '#10b981', '#06b6d4'];

// ── Programmatic heuristic narration using Peripheral Metrics ─────────────────
function generateHeuristicNarratives(entries) {
  return entries.map(entry => {
    let app = entry.application || "Unknown App";
    let windowTitle = entry.window || "";
    let duration = entry.duration_minutes || 0;

    // Fallback safely to 0 if metrics are missing
    let keystrokes = entry.metrics?.keystrokes ?? 0;
    let clicks = entry.metrics?.mouse_clicks ?? 0;
    let distance = entry.metrics?.mouse_distance_px ?? 0;

    let durationText = "";
    if (duration < 1) {
      durationText = `${Math.round(duration * 60)} sec`;
    } else if (duration < 60) {
      durationText = `${Math.round(duration)} min`;
    } else {
      let h = Math.floor(duration / 60);
      let m = Math.round(duration % 60);
      durationText = m > 0 ? `${h} hr ${m} min` : `${h} hr`;
    }

    let summary = "Desktop Activity";
    let desc = "";
    let commentary = "";

    const appLower = app.toLowerCase();
    const winLower = windowTitle.toLowerCase();

    // ── Metric Heuristics Logic (Item 1 Optimization) ──
    let intensityContext = `Inputs captured: ${keystrokes} keystrokes, ${clicks} clicks, ${distance}px distance.`;

    if (keystrokes === 0 && clicks === 0) {
      summary = "System Idle";
      desc = `The system was idle on "${windowTitle}" via ${app} for ${durationText}. No active user input recorded.`;
      commentary = "Away from keyboard or reading passive content.";
    } else if (appLower.includes("code") || winLower.includes("vscode") || winLower.includes("studio")) {
      summary = "Software Development";
      let project = windowTitle.replace(/( - )?(visual studio code|antigravity)/gi, '').trim();
      if (!project || project === "unknown window") project = "project files";

      desc = `Worked on ${project} in ${app} for ${durationText}. ${intensityContext}`;
      commentary = keystrokes > clicks * 3 ? "Highly active programming session." : "Reviewing structures and navigation.";
    } else if (appLower.includes("chrome") || appLower.includes("browser") || appLower.includes("firefox")) {
      if (winLower.includes("youtube") || winLower.includes("video")) {
        summary = "Video Content";
        desc = `Watched media content or instructions for ${durationText}. (${intensityContext})`;
        commentary = "Passive stream review.";
      } else if (winLower.includes("docs") || winLower.includes("sheet") || winLower.includes("notion")) {
        summary = "Documentation & Writing";
        desc = `Read and edited documentation for ${durationText}. Managed text updates containing ${keystrokes} active key variations.`;
        commentary = "Content writing / data collation.";
      } else {
        summary = "Web Research";
        desc = `Researched material online for ${durationText} across pages related to "${windowTitle}".`;
        commentary = "Active cross-referencing.";
      }
    } else if (appLower.includes("terminal") || appLower.includes("alacritty") || appLower.includes("konsole")) {
      summary = "System Configurations";
      desc = `Executed backend processes and workspace scripts using terminal keys. (${intensityContext})`;
      commentary = "Automating tasks via CLI.";
    } else {
      desc = `Maintained focus on "${windowTitle}" inside ${app} for ${durationText}. ${intensityContext}`;
      commentary = "General computer workflow management.";
    }

    return {
      index: entry.index,
      summary: summary,
      description: desc,
      commentary: commentary
    };
  });
}

async function trySaveToServer(logs, dateStr) {
  try {
    await fetch(`${API_BASE}/update_logs?date=${dateStr}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ logs }),
    });
  } catch (_) { }
}

const App = () => {
  const [logs, setLogs] = useState([]);
  const [isPaused, setIsPaused] = useState(false);
  const [pauseCount, setPauseCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('dashboard');

  const [availableDates, setAvailableDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState(() => moment().format('DD-MM-YYYY'));

  const [narrativeLoading, setNarrativeLoading] = useState(false);
  const [narrativeError, setNarrativeError] = useState(null);

  const [historyLogs, setHistoryLogs] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  const isGeneratingRef = React.useRef(isGenerating);
  isGeneratingRef.current = isGenerating;

  useEffect(() => {
    fetchDates();
  }, []);

  useEffect(() => {
    if (activeTab !== 'history') {
      if (!isGenerating) fetchData();
      const interval = setInterval(fetchData, 5000);
      return () => clearInterval(interval);
    } else {
      fetchHistoryData();
    }
  }, [selectedDate, activeTab, isGenerating]);

  const fetchDates = async () => {
    try {
      const res = await fetch(`${API_BASE}/dates`);
      const data = await res.json();
      if (data && data.length > 0) {
        setAvailableDates(data);
      } else {
        setAvailableDates([moment().format('DD-MM-YYYY')]);
      }
    } catch (err) {
      setAvailableDates([moment().format('DD-MM-YYYY')]);
    }
  };

  const fetchData = async () => {
    if (isGeneratingRef.current) return;
    try {
      const t = Date.now();
      const [logsRes, statusRes] = await Promise.all([
        fetch(`${API_BASE}/logs?date=${selectedDate}&t=${t}`, { cache: 'no-store' }),
        fetch(`${API_BASE}/status?date=${selectedDate}&t=${t}`, { cache: 'no-store' })
      ]);
      if (isGeneratingRef.current) return;
      setLogs(await logsRes.json());
      const statusData = await statusRes.json();
      setIsPaused(statusData.paused);
      setPauseCount(statusData.pause_count || 0);
      setLoading(false);
    } catch (err) {
      setLoading(false);
    }
  };

  const fetchHistoryData = async () => {
    setHistoryLoading(true);
    try {
      const res = await fetch(`${API_BASE}/logs?t=${Date.now()}`, { cache: 'no-store' });
      const data = await res.json();
      setHistoryLogs(data);
    } catch (err) {
      console.error(err);
    } finally {
      setHistoryLoading(false);
    }
  };

  const togglePause = async () => {
    try {
      const newState = !isPaused;
      const res = await fetch(`${API_BASE}/pause`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paused: newState })
      });
      const data = await res.json();
      setIsPaused(newState);
      if (selectedDate === moment().format('DD-MM-YYYY')) {
        setPauseCount(data.pause_count || 0);
      }
    } catch (err) { }
  };

  const clearLogs = async () => {
    try {
      const res = await fetch(`${API_BASE}/clear`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await res.json();
      if (data.success) setLogs([]);
    } catch (err) { }
  };

  const generateNarratives = async () => {
    setNarrativeError(null);
    setNarrativeLoading(true);
    setIsGenerating(true); // 1. Freeze background polling immediately

    try {
      const pending = logs
        .map((log, i) => ({ ...log, _idx: i }))
        .filter(log => !log.smart_narration);

      if (pending.length === 0) {
        setNarrativeLoading(false);
        setIsGenerating(false);
        return;
      }

      const entries = pending.map(log => ({
        index: log._idx,
        application: log.application,
        window: log.window,
        start_time: log.start_time,
        end_time: log.end_time,
        duration_minutes: log.duration_minutes,
        metrics: log.metrics
      }));

      await new Promise(r => setTimeout(r, 600));
      const narratives = generateHeuristicNarratives(entries);

      const updated = [...logs];
      for (const item of narratives) {
        updated[item.index] = {
          ...updated[item.index],
          smart_narration: true,
          summary: item.summary || '',
          description: item.description || '',
          commentary: item.commentary || '',
          ai_generated_text: item.summary || '',
        };
      }

      // 2. Save explicitly to server database disk first
      await trySaveToServer(updated, selectedDate);

      // 3. Update local state afterward
      setLogs(updated);

    } catch (err) {
      setNarrativeError(err.message || 'Generation failed.');
    } finally {
      setNarrativeLoading(false);
      // 4. Safely unfreeze polling now that disk I/O and state matches up
      setTimeout(() => setIsGenerating(false), 1000);
    }
  };

  const formatDuration = (mins) => {
    if (mins < 1) return `${Math.round(mins * 60)}s`;
    if (mins < 60) return `${mins.toFixed(1)}m`;
    return `${Math.floor(mins / 60)}h ${Math.round(mins % 60)}m`;
  };

  const groupedHistory = historyLogs.reduce((acc, log) => {
    let dateKey = log.date || (log.start_time ? moment(log.start_time).format('DD-MM-YYYY') : "Unknown Date");
    if (!acc[dateKey]) acc[dateKey] = [];
    acc[dateKey].push(log);
    return acc;
  }, {});

  const sortedHistoryDates = Object.keys(groupedHistory).sort((a, b) => {
    const timeA = new Date(groupedHistory[a][0]?.start_time).getTime() || 0;
    const timeB = new Date(groupedHistory[b][0]?.start_time).getTime() || 0;
    return timeB - timeA;
  });

  const todayLogs = logs;
  const totalMinutesToday = todayLogs.reduce((acc, l) => acc + l.duration_minutes, 0);
  const narratedCount = todayLogs.filter(l => l.smart_narration).length;
  const allNarrated = todayLogs.length > 0 && narratedCount === todayLogs.length;

  const appStats = {};
  todayLogs.forEach(log => {
    if (log.application !== "System") {
      appStats[log.application] = (appStats[log.application] || 0) + log.duration_minutes;
    }
  });
  const pieData = Object.keys(appStats)
    .map(app => ({ name: app, value: Number(appStats[app].toFixed(2)) }))
    .sort((a, b) => b.value - a.value).slice(0, 6);

  const timelineStats = {};
  todayLogs.forEach(log => {
    if (log.application !== "System") {
      const hour = moment(log.start_time).format('HA');
      timelineStats[hour] = (timelineStats[hour] || 0) + log.duration_minutes;
    }
  });
  const barData = Object.keys(timelineStats).map(hour => ({
    time: hour,
    minutes: Number(timelineStats[hour].toFixed(2))
  }));

  if (loading && activeTab !== 'history') return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-blue-500/30">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400">
                TrackFlow
              </h1>
              <p className="text-xs text-slate-500 font-medium tracking-wide">AUTOMATED DESKTOP LOGGER</p>
            </div>
          </div>
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2 text-sm text-slate-400 bg-slate-800/50 py-1.5 px-3 rounded-full">
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span>Live Synced</span>
            </div>
            <button
              onClick={togglePause}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-full font-medium transition-all duration-300 shadow-lg cursor-pointer ${isPaused
                ? 'bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 border border-amber-500/20'
                : 'bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 border border-emerald-500/20'
                }`}
            >
              {isPaused ? <Play className="w-4 h-4 fill-current" /> : <Pause className="w-4 h-4 fill-current" />}
              {isPaused ? 'Resume Tracking' : 'Pause Tracking'}
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* ── Stat Cards ─────────────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 relative overflow-hidden group">
            <div className="flex justify-between items-start mb-4">
              <div>
                <p className="text-slate-400 text-sm font-medium mb-1">Focus Time</p>
                <h2 className="text-4xl font-bold text-white">{formatDuration(totalMinutesToday)}</h2>
              </div>
              <div className="p-3 bg-blue-500/10 rounded-xl"><Clock className="w-6 h-6 text-blue-500" /></div>
            </div>
            <div className="flex items-center gap-2 text-sm text-emerald-400">
              <CheckCircle2 className="w-4 h-4" /><span>Auto-tracked seamlessly</span>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 relative overflow-hidden group">
            <div className="flex justify-between items-start mb-4">
              <div>
                <p className="text-slate-400 text-sm font-medium mb-1">Active Applications</p>
                <h2 className="text-4xl font-bold text-white">{Object.keys(appStats).length}</h2>
              </div>
              <div className="p-3 bg-purple-500/10 rounded-xl"><Layout className="w-6 h-6 text-purple-500" /></div>
            </div>
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <Monitor className="w-4 h-4" /><span>Across all desktops</span>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 relative overflow-hidden group">
            <div className="flex justify-between items-start mb-4">
              <div>
                <p className="text-slate-400 text-sm font-medium mb-1">Narrated Entries</p>
                <h2 className="text-4xl font-bold text-white">
                  {narratedCount}<span className="text-slate-500 text-2xl">/{todayLogs.length}</span>
                </h2>
              </div>
              <div className="p-3 bg-violet-500/10 rounded-xl"><Sparkles className="w-6 h-6 text-violet-400" /></div>
            </div>
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <Sparkles className="w-4 h-4 text-violet-400" /><span>Dynamic rule classification</span>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 relative overflow-hidden group">
            <div className="flex justify-between items-start mb-4">
              <div>
                <p className="text-slate-400 text-sm font-medium mb-1">Privacy Status</p>
                <h2 className={`text-3xl font-bold mt-1 ${isPaused ? 'text-amber-500' : 'text-emerald-500'}`}>
                  {isPaused ? 'PAUSED' : 'WATCHING'}
                </h2>
              </div>
              <div className={`p-3 rounded-xl ${isPaused ? 'bg-amber-500/10' : 'bg-emerald-500/10'}`}>
                <Shield className={`w-6 h-6 ${isPaused ? 'text-amber-500' : 'text-emerald-500'}`} />
              </div>
            </div>
            <div className="text-sm text-slate-400">
              {pauseCount > 0 ? `Paused ${pauseCount} times` : 'Monitoring foreground changes'}
            </div>
          </div>
        </div>

        {/* ── Tabs ───────────────────────────────────────────────────────────── */}
        <div className="flex items-center gap-6 border-b border-slate-800 mb-8">
          {[
            { id: 'dashboard', label: 'Analytics Dashboard' },
            { id: 'logs', label: 'Review Logs' },
            { id: 'history', label: 'History Archive' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`pb-4 px-2 text-sm font-medium transition-colors relative cursor-pointer ${activeTab === tab.id ? 'text-white' : 'text-slate-400 hover:text-slate-200'}`}
            >
              {tab.label}
              {activeTab === tab.id && <div className="absolute bottom-0 left-0 w-full h-0.5 bg-blue-500 rounded-t-full" />}
            </button>
          ))}
        </div>

        {/* ── Dashboard Tab ──────────────────────────────────────────────────── */}
        {activeTab === 'dashboard' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
                <Activity className="w-5 h-5 text-blue-500" /> Activity Timeline
              </h3>
              <div className="h-72">
                {barData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={barData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                      <XAxis dataKey="time" stroke="#64748b" tick={{ fill: '#64748b', fontSize: 12 }} axisLine={false} tickLine={false} />
                      <YAxis stroke="#64748b" tick={{ fill: '#64748b', fontSize: 12 }} axisLine={false} tickLine={false} />
                      <Tooltip
                        cursor={{ fill: '#1e293b' }}
                        contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '8px', color: '#f8fafc' }}
                      />
                      <Bar dataKey="minutes" radius={[4, 4, 0, 0]}>
                        {barData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-slate-500 text-sm">
                    No application activity to display yet.
                  </div>
                )}
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
                <PieChart className="w-5 h-5 text-purple-500" /> App Distribution
              </h3>
              <div className="h-60">
                {pieData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <RechartsPieChart>
                      <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value" stroke="none">
                        {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                      </Pie>
                      <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '8px', color: '#f8fafc' }} />
                    </RechartsPieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-slate-500 text-sm">
                    No application distribution data.
                  </div>
                )}
              </div>
              <div className="mt-4 space-y-2">
                {pieData.map((entry, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                      <span className="text-slate-300 truncate max-w-[120px]">{entry.name}</span>
                    </div>
                    <span className="font-medium">{formatDuration(entry.value)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── Review Logs Tab ────────────────────────────────────────────────── */}
        {activeTab === 'logs' && (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
            <div className="p-6 border-b border-slate-800 space-y-3">
              <div className="flex flex-wrap gap-3 justify-between items-center">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <FileText className="w-5 h-5 text-blue-500" /> Review Generated Logs
                </h3>
                <div className="flex flex-wrap gap-3 items-center">
                  <button onClick={clearLogs} className="border border-slate-700 hover:bg-slate-800 text-slate-300 px-4 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer">
                    Clear All Logs
                  </button>
                  <button className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer">
                    Approve Logs
                  </button>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-3 pt-1">
                <button
                  onClick={generateNarratives}
                  disabled={narrativeLoading || allNarrated}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${narrativeLoading || allNarrated
                    ? 'bg-violet-500/5 text-violet-400/40 border border-violet-500/10 cursor-not-allowed'
                    : 'bg-violet-500/10 text-violet-400 border border-violet-500/20 hover:bg-violet-500/20 cursor-pointer'
                    }`}
                >
                  {narrativeLoading ? <><Loader2 className="w-4 h-4 animate-spin" /> Narration Binding…</> : <><Sparkles className="w-4 h-4" /> {allNarrated ? 'All Narrated' : 'Generate Narratives'}</>}
                </button>
                {narrativeError && (
                  <div className="flex items-center gap-1.5 text-sm text-red-400 bg-red-500/10 border border-red-500/20 px-3 py-1.5 rounded-lg">
                    <AlertCircle className="w-4 h-4 shrink-0" /> {narrativeError}
                  </div>
                )}
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-950/50 text-slate-400 text-sm">
                    <th className="p-4 font-medium whitespace-nowrap">Time</th>
                    <th className="p-4 font-medium">Application</th>
                    <th className="p-4 font-medium">Window</th>
                    <th className="p-4 font-medium">
                      <span className="flex items-center gap-1.5"><Sparkles className="w-3.5 h-3.5 text-violet-400" /> Narrative Activity</span>
                    </th>
                    <th className="p-4 font-medium">Activity Telemetry</th>
                    <th className="p-4 font-medium">Duration</th>
                  </tr>
                </thead>
                <tbody className="text-sm divide-y divide-slate-800">
                  {todayLogs.slice().reverse().map((log, i) => (
                    <tr key={i} className="hover:bg-slate-800/30 transition-colors align-top">
                      <td className="p-4 whitespace-nowrap text-slate-300">
                        {moment(log.start_time).format('hh:mm A')}<br />
                        <span className="text-slate-500 text-xs">→ {moment(log.end_time).format('hh:mm A')}</span>
                      </td>
                      <td className="p-4 font-medium text-white">{log.application}</td>
                      <td className="p-4 text-slate-400 max-w-[180px]"><span className="block truncate" title={log.window}>{log.window}</span></td>
                      <td className="p-4 max-w-xs">
                        {log.smart_narration ? (
                          <div className="space-y-1">
                            <p className="text-slate-200 text-sm leading-snug">{log.description}</p>
                            {log.commentary && <p className="text-slate-500 text-xs italic">{log.commentary}</p>}
                          </div>
                        ) : narrativeLoading ? (
                          <span className="flex items-center gap-1.5 text-slate-500 text-xs"><Loader2 className="w-3 h-3 animate-spin" /> generating…</span>
                        ) : <span className="text-slate-600 text-xs">—</span>}
                      </td>
                      <td className="p-4 min-w-[150px]">
                        <div className="flex flex-col gap-1 text-xs font-mono text-slate-400">
                          <span className="flex items-center gap-1"><Keyboard className="w-3 h-3 text-blue-400" /> Keys: {log.metrics?.keystrokes ?? 0}</span>
                          <span className="flex items-center gap-1"><MousePointer className="w-3 h-3 text-purple-400" /> Clicks: {log.metrics?.mouse_clicks ?? 0}</span>
                          <span className="flex items-center gap-1"><MousePointer className="w-3 h-3 text-emerald-400" /> Dist: {log.metrics?.mouse_distance_px ?? 0}px</span>
                        </div>
                      </td>
                      <td className="p-4 font-mono text-slate-300 whitespace-nowrap">{formatDuration(log.duration_minutes)}</td>
                    </tr>
                  ))}
                  {todayLogs.length === 0 && (
                    <tr><td colSpan={6} className="p-8 text-center text-slate-500">No activity recorded for {selectedDate}.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── History Archive Tab ────────────────────────────────────────────── */}
        {activeTab === 'history' && (
          <div className="space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex justify-between items-center">
              <div>
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <History className="w-5 h-5 text-blue-500" /> Daily History Archive
                </h3>
                <p className="text-slate-400 text-sm mt-1">Viewing all immutable daily logs from your data storage.</p>
              </div>
            </div>

            {historyLoading ? (
              <div className="flex justify-center p-12">
                <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
              </div>
            ) : sortedHistoryDates.length === 0 ? (
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center">
                <History className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                <h3 className="text-xl font-medium text-white mb-2">No History Found</h3>
                <p className="text-slate-400 text-sm">There are no log files saved in the archive yet.</p>
              </div>
            ) : (
              sortedHistoryDates.map(date => (
                <div key={date} className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
                  <div className="p-4 border-b border-slate-800 bg-slate-950/30 flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-slate-400" />
                    <h4 className="font-semibold text-slate-200">{date}</h4>
                    <span className="text-slate-500 text-xs ml-2">({groupedHistory[date].length} entries)</span>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="bg-slate-950/20 text-slate-400 text-xs uppercase tracking-wider">
                          <th className="p-3 font-medium whitespace-nowrap">Time</th>
                          <th className="p-3 font-medium">Application</th>
                          <th className="p-3 font-medium">Window</th>
                          <th className="p-3 font-medium">
                            <span className="flex items-center gap-1.5"><Sparkles className="w-3.5 h-3.5 text-violet-400" /> Description</span>
                          </th>
                          <th className="p-3 font-medium">Telemetry</th>
                          <th className="p-3 font-medium">Duration</th>
                        </tr>
                      </thead>
                      <tbody className="text-sm divide-y divide-slate-800/50">
                        {groupedHistory[date].slice().reverse().map((log, i) => (
                          <tr key={i} className="hover:bg-slate-800/20 transition-colors align-top">
                            <td className="p-3 whitespace-nowrap text-slate-400">
                              {moment(log.start_time).format('hh:mm A')} - {moment(log.end_time).format('hh:mm A')}
                            </td>
                            <td className="p-3 font-medium text-slate-300">{log.application}</td>
                            <td className="p-3 text-slate-500 max-w-[150px] truncate" title={log.window}>{log.window}</td>
                            <td className="p-3 max-w-xs">
                              {log.smart_narration ? (
                                <div className="space-y-1">
                                  <p className="text-slate-300 text-sm leading-snug">{log.description}</p>
                                  {log.commentary && <p className="text-slate-500 text-xs italic">{log.commentary}</p>}
                                </div>
                              ) : <span className="text-slate-600 text-xs">—</span>}
                            </td>
                            <td className="p-3 font-mono text-xs text-slate-500">
                              K: {log.metrics?.keystrokes ?? 0} | C: {log.metrics?.mouse_clicks ?? 0} | D: {log.metrics?.mouse_distance_px ?? 0}px
                            </td>
                            <td className="p-3 font-mono text-slate-300 whitespace-nowrap">{formatDuration(log.duration_minutes)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </main>
    </div>
  );
};

export default App;