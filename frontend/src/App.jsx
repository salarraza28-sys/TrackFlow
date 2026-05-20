import React, { useState, useEffect } from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts';
import { 
  Play, Pause, Activity, Clock, Layout, Monitor, Shield, 
  RefreshCw, CheckCircle2, FileText
} from 'lucide-react';
import moment from 'moment';

const API_BASE = 'http://localhost:5001/api';

const COLORS = ['#3b82f6', '#8b5cf6', '#ec4899', '#f43f5e', '#f59e0b', '#10b981', '#06b6d4'];

const App = () => {
  const [logs, setLogs] = useState([]);
  const [isPaused, setIsPaused] = useState(false);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('dashboard');

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const timestamp = new Date().getTime();
      const [logsRes, statusRes] = await Promise.all([
        fetch(`${API_BASE}/logs?t=${timestamp}`, { cache: 'no-store' }),
        fetch(`${API_BASE}/status?t=${timestamp}`, { cache: 'no-store' })
      ]);
      
      const logsData = await logsRes.json();
      const statusData = await statusRes.json();
      
      setLogs(logsData);
      setIsPaused(statusData.paused);
      setLoading(false);
    } catch (err) {
      console.error("Failed to fetch data:", err);
      // Fallback dummy data if backend is not running yet
      if (logs.length === 0) {
        setLogs([
            { application: "Visual Studio Code", window: "App.jsx - frontend", start_time: new Date(Date.now() - 3600000).toISOString(), end_time: new Date().toISOString(), duration_minutes: 60 },
            { application: "Google Chrome", window: "React Documentation", start_time: new Date(Date.now() - 7200000).toISOString(), end_time: new Date(Date.now() - 3600000).toISOString(), duration_minutes: 45 },
            { application: "Slack", window: "Engineering Team", start_time: new Date(Date.now() - 8000000).toISOString(), end_time: new Date(Date.now() - 7200000).toISOString(), duration_minutes: 15 }
        ]);
        setLoading(false);
      }
    }
  };

  const togglePause = async () => {
    try {
      const newState = !isPaused;
      await fetch(`${API_BASE}/pause`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paused: newState })
      });
      setIsPaused(newState);
    } catch (err) {
      console.error("Failed to toggle pause:", err);
    }
  };

  const generateMock = async () => {
    try {
      const res = await fetch(`${API_BASE}/generate_mock`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        setLogs(data.logs);
      }
    } catch (err) {
      console.error("Failed to generate mock:", err);
    }
  };

  const clearLogs = async () => {
    try {
      const res = await fetch(`${API_BASE}/clear`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        setLogs([]);
      }
    } catch (err) {
      console.error("Failed to clear logs:", err);
    }
  };

  // Compute statistics
  const today = moment().startOf('day');
  const todayLogs = logs.filter(log => moment(log.start_time).isSameOrAfter(today));
  
  const totalMinutesToday = todayLogs.reduce((acc, log) => acc + log.duration_minutes, 0);
  
  // App usage stats for Pie chart
  const appStats = {};
  todayLogs.forEach(log => {
    if (!appStats[log.application]) appStats[log.application] = 0;
    appStats[log.application] += log.duration_minutes;
  });
  const pieData = Object.keys(appStats).map(app => ({
    name: app,
    value: Number(appStats[app].toFixed(2))
  })).sort((a, b) => b.value - a.value).slice(0, 6);

  // Timeline for Bar chart
  const timelineStats = {};
  todayLogs.forEach(log => {
    const hour = moment(log.start_time).format('HA');
    if (!timelineStats[hour]) timelineStats[hour] = 0;
    timelineStats[hour] += log.duration_minutes;
  });
  const barData = Object.keys(timelineStats).map(hour => ({
    time: hour,
    minutes: Number(timelineStats[hour].toFixed(2))
  }));

  const formatDuration = (mins) => {
    if (mins < 1) {
      const secs = Math.round(mins * 60);
      return `${secs}s`;
    }
    if (mins < 60) {
      return `${mins.toFixed(1)}m`;
    }
    const h = Math.floor(mins / 60);
    const m = Math.round(mins % 60);
    return `${h}h ${m}m`;
  };

  if (loading) return <div className="min-h-screen bg-slate-950 flex items-center justify-center text-white"><RefreshCw className="w-8 h-8 animate-spin text-blue-500" /></div>;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-blue-500/30">
      {/* Header */}
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
              <RefreshCw className="w-4 h-4 animate-spin-slow" />
              <span>Live Synced</span>
            </div>
            
            <button
              onClick={togglePause}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-full font-medium transition-all duration-300 shadow-lg cursor-pointer ${
                isPaused 
                  ? 'bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 border border-amber-500/20 shadow-amber-500/10' 
                  : 'bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 border border-emerald-500/20 shadow-emerald-500/10'
              }`}
            >
              {isPaused ? <Play className="w-4 h-4 fill-current" /> : <Pause className="w-4 h-4 fill-current" />}
              {isPaused ? 'Resume Tracking' : 'Pause Tracking'}
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        
        {/* Top Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/5 rounded-full blur-2xl -mr-10 -mt-10 transition-transform group-hover:scale-150 duration-700"></div>
            <div className="flex justify-between items-start mb-4">
              <div>
                <p className="text-slate-400 text-sm font-medium mb-1">Today's Focus Time</p>
                <h2 className="text-4xl font-bold text-white">{formatDuration(totalMinutesToday)}</h2>
              </div>
              <div className="p-3 bg-blue-500/10 rounded-xl">
                <Clock className="w-6 h-6 text-blue-500" />
              </div>
            </div>
            <div className="flex items-center gap-2 text-sm text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
              <span>Auto-tracked seamlessly</span>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/5 rounded-full blur-2xl -mr-10 -mt-10 transition-transform group-hover:scale-150 duration-700"></div>
            <div className="flex justify-between items-start mb-4">
              <div>
                <p className="text-slate-400 text-sm font-medium mb-1">Active Applications</p>
                <h2 className="text-4xl font-bold text-white">{Object.keys(appStats).length}</h2>
              </div>
              <div className="p-3 bg-purple-500/10 rounded-xl">
                <Layout className="w-6 h-6 text-purple-500" />
              </div>
            </div>
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <Monitor className="w-4 h-4" />
              <span>Across all desktops</span>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-32 h-32 bg-amber-500/5 rounded-full blur-2xl -mr-10 -mt-10 transition-transform group-hover:scale-150 duration-700"></div>
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
            <div className="flex items-center gap-2 text-sm text-slate-400">
              {isPaused ? 'Recording stopped for privacy' : 'Capturing background activity'}
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-6 border-b border-slate-800 mb-8">
          <button 
            onClick={() => setActiveTab('dashboard')}
            className={`pb-4 px-2 text-sm font-medium transition-colors relative cursor-pointer ${activeTab === 'dashboard' ? 'text-white' : 'text-slate-400 hover:text-slate-200'}`}
          >
            Analytics Dashboard
            {activeTab === 'dashboard' && <div className="absolute bottom-0 left-0 w-full h-0.5 bg-blue-500 rounded-t-full"></div>}
          </button>
          <button 
            onClick={() => setActiveTab('logs')}
            className={`pb-4 px-2 text-sm font-medium transition-colors relative cursor-pointer ${activeTab === 'logs' ? 'text-white' : 'text-slate-400 hover:text-slate-200'}`}
          >
            Review Logs
            {activeTab === 'logs' && <div className="absolute bottom-0 left-0 w-full h-0.5 bg-blue-500 rounded-t-full"></div>}
          </button>
        </div>

        {/* Tab Content */}
        {logs.length === 0 ? (
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-12 text-center max-w-2xl mx-auto my-8 backdrop-blur-xl">
            <Activity className="w-16 h-16 text-blue-500 mx-auto mb-6 animate-pulse" />
            <h3 className="text-2xl font-bold text-white mb-3">No Active Window Logs Yet</h3>
            <p className="text-slate-400 text-sm mb-8 leading-relaxed max-w-md mx-auto">
              TrackFlow's API is active, but it hasn't recorded any local windows yet. This is common in remote sessions, WSL without active displays, or headless VMs.
            </p>
            <button
              onClick={generateMock}
              className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-semibold px-8 py-3.5 rounded-xl transition-all duration-300 shadow-xl shadow-blue-500/10 cursor-pointer"
            >
              Generate Realistic Demo Logs
            </button>
          </div>
        ) : activeTab === 'dashboard' ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Chart 1 */}
            <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
                <Activity className="w-5 h-5 text-blue-500" /> Activity Timeline
              </h3>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={barData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                    <XAxis dataKey="time" stroke="#64748b" tick={{fill: '#64748b', fontSize: 12}} axisLine={false} tickLine={false} />
                    <YAxis stroke="#64748b" tick={{fill: '#64748b', fontSize: 12}} axisLine={false} tickLine={false} />
                    <Tooltip 
                      cursor={{fill: '#1e293b'}} 
                      contentStyle={{backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '8px', color: '#f8fafc'}}
                      itemStyle={{color: '#e2e8f0'}}
                    />
                    <Bar dataKey="minutes" fill="#3b82f6" radius={[4, 4, 0, 0]}>
                      {barData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Chart 2 */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
                <PieChart className="w-5 h-5 text-purple-500" /> App Distribution
              </h3>
              <div className="h-60 flex items-center justify-center">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="value"
                      stroke="none"
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip 
                      contentStyle={{backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '8px', color: '#f8fafc'}}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-4 space-y-2">
                {pieData.map((entry, index) => (
                  <div key={index} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full" style={{backgroundColor: COLORS[index % COLORS.length]}}></div>
                      <span className="text-slate-300 truncate max-w-[120px]">{entry.name}</span>
                    </div>
                    <span className="font-medium">{formatDuration(entry.value)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
            <div className="p-6 border-b border-slate-800 flex justify-between items-center">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <FileText className="w-5 h-5 text-blue-500" /> Review Generated Logs
              </h3>
              <div className="flex gap-3">
                <button 
                  onClick={clearLogs}
                  className="border border-slate-700 hover:bg-slate-800 text-slate-300 px-4 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer"
                >
                  Clear All Logs
                </button>
                <button className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer">
                  Approve Today's Logs
                </button>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-950/50 text-slate-400 text-sm">
                    <th className="p-4 font-medium">Time</th>
                    <th className="p-4 font-medium">Application</th>
                    <th className="p-4 font-medium">Window Details</th>
                    <th className="p-4 font-medium">Duration</th>
                    <th className="p-4 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody className="text-sm divide-y divide-slate-800">
                  {todayLogs.slice().reverse().map((log, i) => (
                    <tr key={i} className="hover:bg-slate-800/30 transition-colors">
                      <td className="p-4 whitespace-nowrap text-slate-300">
                        {moment(log.start_time).format('hh:mm A')} - {moment(log.end_time).format('hh:mm A')}
                      </td>
                      <td className="p-4 font-medium text-white">
                        {log.application}
                      </td>
                      <td className="p-4 text-slate-400 max-w-xs truncate">
                        {log.window}
                      </td>
                      <td className="p-4 font-mono text-slate-300">
                        {formatDuration(log.duration_minutes)}
                      </td>
                      <td className="p-4">
                        <span className="bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2 py-1 rounded text-xs font-medium">
                          Auto-logged
                        </span>
                      </td>
                    </tr>
                  ))}
                  {todayLogs.length === 0 && (
                    <tr>
                      <td colSpan="5" className="p-8 text-center text-slate-500">
                        No activity recorded yet today. Keep this tracker running in the background.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </main>
    </div>
  );
};

export default App;
