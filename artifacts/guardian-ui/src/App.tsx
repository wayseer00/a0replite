import { useState, useRef, useEffect, useCallback } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const API_BASE = import.meta.env.BASE_URL.replace(/\/$/, "");

function apiUrl(path: string) {
  return `${API_BASE}${path}`;
}

// ─── types ───────────────────────────────────────────────────────────────────

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface AuditEvent {
  event: string;
  data: Record<string, unknown>;
  ts?: number;
}

interface HealthStatus {
  status: string;
  components?: Record<string, string>;
  heartbeat?: {
    tick?: number;
    uptime_secs?: number;
  };
}

// ─── Chat tab ────────────────────────────────────────────────────────────────

function ChatTab() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const ensureSession = useCallback(async (): Promise<string> => {
    if (sessionId) return sessionId;
    const res = await fetch(apiUrl("/api/session"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: "guardian-ui", tier: "seeker" }),
    });
    if (!res.ok) throw new Error(`Session create failed: ${res.status}`);
    const data = await res.json();
    const id = data.session_id as string;
    setSessionId(id);
    return id;
  }, [sessionId]);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || streaming) return;
    setInput("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setStreaming(true);

    let sid: string;
    try {
      sid = await ensureSession();
    } catch (e: unknown) {
      setError(String(e));
      setStreaming(false);
      return;
    }

    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      const res = await fetch(apiUrl("/api/chat"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sid,
          message: text,
          hmmm: "",
        }),
      });

      if (!res.ok) {
        const err = await res.text();
        setError(`Chat error ${res.status}: ${err}`);
        setMessages((prev) => prev.slice(0, -1));
        setStreaming(false);
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response body");
      const decoder = new TextDecoder();
      let buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6).trim();
          if (payload === "[DONE]") break;
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last?.role !== "assistant") return prev;
            return [
              ...prev.slice(0, -1),
              { role: "assistant", content: last.content + payload },
            ];
          });
        }
      }
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setStreaming(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {sessionId && (
        <div className="px-4 py-1 text-xs text-muted-foreground border-b border-border font-mono">
          session: {sessionId}
        </div>
      )}
      <ScrollArea className="flex-1 px-4 py-4">
        {messages.length === 0 && (
          <div className="text-center text-muted-foreground mt-12 text-sm">
            <p className="mb-1 text-cyan font-mono tracking-widest uppercase text-xs">a0replite</p>
            <p>The Interdependent Way — grounded AI instance</p>
            <p className="mt-2 text-xs opacity-60">Send a message to begin.</p>
          </div>
        )}
        <div className="space-y-4 max-w-2xl mx-auto">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`rounded-lg px-4 py-2 max-w-[80%] text-sm whitespace-pre-wrap ${
                  m.role === "user"
                    ? "bg-secondary text-secondary-foreground"
                    : "bg-card border border-border text-foreground"
                }`}
              >
                {m.content}
                {m.role === "assistant" && streaming && i === messages.length - 1 && (
                  <span className="inline-block w-1.5 h-4 ml-0.5 bg-primary animate-pulse align-middle" />
                )}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      {error && (
        <div className="px-4 py-2 text-xs text-destructive border-t border-destructive/20 font-mono">
          {error}
        </div>
      )}

      <div className="border-t border-border p-4">
        <div className="flex gap-2 max-w-2xl mx-auto">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message a0replite… (Enter to send, Shift+Enter for newline)"
            className="resize-none min-h-[60px] bg-input border-input text-foreground placeholder:text-muted-foreground"
            disabled={streaming}
          />
          <Button
            onClick={sendMessage}
            disabled={streaming || !input.trim()}
            className="self-end bg-primary text-primary-foreground hover:opacity-90"
          >
            {streaming ? "…" : "Send"}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ─── Guardian tab ─────────────────────────────────────────────────────────────

function GuardianTab() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [opKey, setOpKey] = useState("");
  const [actionTarget, setActionTarget] = useState("");
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const fetchAudit = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(apiUrl("/guardian/audit"), {
        headers: opKey ? { "X-Operator-Key": opKey } : {},
      });
      if (!res.ok) {
        const txt = await res.text();
        setError(`Audit fetch error ${res.status}: ${txt}`);
        return;
      }
      const data = await res.json();
      setEvents(Array.isArray(data.events) ? data.events : []);
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const sendApprove = async (target: string) => {
    setActionMsg(null);
    try {
      const res = await fetch(apiUrl("/guardian/approve"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(opKey ? { "X-Operator-Key": opKey } : {}),
        },
        body: JSON.stringify({ target, hmmm: "" }),
      });
      const data = await res.json();
      setActionMsg(res.ok ? `Approved: ${target}` : `Error: ${JSON.stringify(data)}`);
    } catch (e: unknown) {
      setActionMsg(String(e));
    }
  };

  const sendRevoke = async (target: string) => {
    setActionMsg(null);
    try {
      const res = await fetch(apiUrl("/guardian/revoke"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(opKey ? { "X-Operator-Key": opKey } : {}),
        },
        body: JSON.stringify({ target, hmmm: "" }),
      });
      const data = await res.json();
      setActionMsg(res.ok ? `Revoked: ${target}` : `Error: ${JSON.stringify(data)}`);
    } catch (e: unknown) {
      setActionMsg(String(e));
    }
  };

  return (
    <div className="p-4 space-y-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
        <div className="flex-1">
          <label className="text-xs text-muted-foreground mb-1 block">Operator Key (optional)</label>
          <input
            type="password"
            value={opKey}
            onChange={(e) => setOpKey(e.target.value)}
            placeholder="GUARDIAN_OPERATOR_KEY"
            className="w-full rounded-md border border-input bg-input px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
          />
        </div>
        <Button onClick={fetchAudit} disabled={loading} size="sm" variant="outline">
          {loading ? "Loading…" : "Refresh Audit Log"}
        </Button>
      </div>

      {error && (
        <div className="text-xs text-destructive font-mono bg-destructive/10 rounded px-3 py-2">
          {error}
        </div>
      )}

      <Separator />

      <div>
        <p className="text-xs text-muted-foreground mb-2 uppercase tracking-widest">Approve / Revoke</p>
        <div className="flex gap-2">
          <input
            value={actionTarget}
            onChange={(e) => setActionTarget(e.target.value)}
            placeholder="gate target (e.g. PUSH)"
            className="flex-1 rounded-md border border-input bg-input px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
          />
          <Button
            size="sm"
            onClick={() => sendApprove(actionTarget)}
            disabled={!actionTarget}
            className="bg-primary text-primary-foreground"
          >
            Approve
          </Button>
          <Button
            size="sm"
            variant="destructive"
            onClick={() => sendRevoke(actionTarget)}
            disabled={!actionTarget}
          >
            Revoke
          </Button>
        </div>
        {actionMsg && (
          <p className="mt-2 text-xs font-mono text-foreground/70">{actionMsg}</p>
        )}
      </div>

      <Separator />

      <div>
        <p className="text-xs text-muted-foreground mb-2 uppercase tracking-widest">
          Audit Events ({events.length})
        </p>
        <ScrollArea className="h-[40vh] rounded-md border border-border">
          {events.length === 0 ? (
            <p className="p-4 text-sm text-muted-foreground">No events — click Refresh Audit Log.</p>
          ) : (
            <div className="p-2 space-y-2">
              {events.map((ev, i) => (
                <div key={i} className="rounded bg-muted/40 px-3 py-2 text-xs font-mono">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant="outline" className="text-cyan border-cyan/40 text-[10px]">
                      {ev.event}
                    </Badge>
                    {ev.ts && (
                      <span className="text-muted-foreground">
                        {new Date(ev.ts * 1000).toISOString()}
                      </span>
                    )}
                  </div>
                  <pre className="whitespace-pre-wrap break-all text-foreground/70">
                    {JSON.stringify(ev.data, null, 2)}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </div>
    </div>
  );
}

// ─── Status tab ───────────────────────────────────────────────────────────────

function StatusTab() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<string | null>(null);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(apiUrl("/api/health"));
      if (!res.ok) {
        setError(`Health check failed: ${res.status}`);
        return;
      }
      const data = await res.json();
      setHealth(data);
      setLastRefresh(new Date().toISOString());
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const id = setInterval(fetchHealth, 30_000);
    return () => clearInterval(id);
  }, []);

  const statusColor = (s: string) => {
    if (s === "ok") return "text-green-400";
    if (s === "unavailable") return "text-yellow-400";
    return "text-destructive";
  };

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-muted-foreground uppercase tracking-widest">System Status</p>
          {lastRefresh && (
            <p className="text-[10px] text-muted-foreground font-mono">
              last refresh: {lastRefresh}
            </p>
          )}
        </div>
        <Button size="sm" variant="outline" onClick={fetchHealth} disabled={loading}>
          {loading ? "Checking…" : "Refresh"}
        </Button>
      </div>

      {error && (
        <div className="text-xs text-destructive font-mono bg-destructive/10 rounded px-3 py-2">
          {error}
        </div>
      )}

      {health && (
        <div className="space-y-3">
          <Card className="bg-card border-border">
            <CardHeader className="pb-2 pt-4 px-4">
              <CardTitle className="text-sm flex items-center gap-2">
                Overall
                <span className={`text-xs font-mono ${statusColor(health.status)}`}>
                  {health.status}
                </span>
              </CardTitle>
            </CardHeader>
          </Card>

          {health.components && (
            <Card className="bg-card border-border">
              <CardHeader className="pb-2 pt-4 px-4">
                <CardTitle className="text-sm">Components</CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-4">
                <div className="grid grid-cols-2 gap-x-6 gap-y-1">
                  {Object.entries(health.components).map(([name, status]) => (
                    <div key={name} className="flex items-center justify-between text-xs py-0.5">
                      <span className="font-mono text-muted-foreground">{name}</span>
                      <span className={`font-mono ${statusColor(status)}`}>{status}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {health.heartbeat && (
            <Card className="bg-card border-border">
              <CardHeader className="pb-2 pt-4 px-4">
                <CardTitle className="text-sm">Heartbeat</CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-4 text-xs font-mono space-y-1">
                {health.heartbeat.tick !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">tick</span>
                    <span>{health.heartbeat.tick}</span>
                  </div>
                )}
                {health.heartbeat.uptime_secs !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">uptime</span>
                    <span>{Math.floor(health.heartbeat.uptime_secs)}s</span>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          <Card className="bg-card border-border">
            <CardHeader className="pb-2 pt-4 px-4">
              <CardTitle className="text-sm">Raw Response</CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <ScrollArea className="h-40">
                <pre className="text-[11px] font-mono text-foreground/70 whitespace-pre-wrap">
                  {JSON.stringify(health, null, 2)}
                </pre>
              </ScrollArea>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

// ─── Policy tab ───────────────────────────────────────────────────────────────

function PolicyTab() {
  const [policy, setPolicy] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPolicy = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(apiUrl("/api/policy"));
      if (!res.ok) {
        setError(`Policy fetch failed: ${res.status}`);
        return;
      }
      const data = await res.json();
      setPolicy(data);
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPolicy();
  }, []);

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground uppercase tracking-widest">OpenAI Policy</p>
        <Button size="sm" variant="outline" onClick={fetchPolicy} disabled={loading}>
          {loading ? "Loading…" : "Refresh"}
        </Button>
      </div>

      {error && (
        <div className="text-xs text-destructive font-mono bg-destructive/10 rounded px-3 py-2">
          {error}
        </div>
      )}

      {policy && (
        <div className="space-y-4">
          {typeof policy === "object" && policy !== null && "roles" in policy && (
            <Card className="bg-card border-border">
              <CardHeader className="pb-2 pt-4 px-4">
                <CardTitle className="text-sm">Model Roles</CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-4">
                <div className="space-y-2">
                  {Object.entries((policy as Record<string, Record<string, Record<string, string>>>).roles).map(
                    ([role, cfg]) => (
                      <div key={role} className="text-xs rounded bg-muted/30 px-3 py-2">
                        <div className="flex items-center gap-2 mb-0.5">
                          <Badge variant="outline" className="text-[10px] border-secondary/40 text-violet-400">
                            {role}
                          </Badge>
                          <span className="font-mono text-cyan">{cfg.default}</span>
                        </div>
                        <p className="text-muted-foreground">{cfg.purpose}</p>
                      </div>
                    )
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          <Card className="bg-card border-border">
            <CardHeader className="pb-2 pt-4 px-4">
              <CardTitle className="text-sm">Full Policy JSON</CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <ScrollArea className="h-64">
                <pre className="text-[11px] font-mono text-foreground/70 whitespace-pre-wrap">
                  {JSON.stringify(policy, null, 2)}
                </pre>
              </ScrollArea>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

// ─── Root app ─────────────────────────────────────────────────────────────────

export default function App() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <header className="border-b border-border px-6 py-3 flex items-center gap-3">
        <div>
          <h1 className="text-sm font-mono font-semibold tracking-widest uppercase text-cyan">
            a0replite
          </h1>
          <p className="text-[10px] text-muted-foreground tracking-wider">
            The Interdependent Way — Guardian Interface
          </p>
        </div>
        <div className="ml-auto">
          <Badge variant="outline" className="text-[10px] border-secondary/40 text-violet-400 font-mono">
            grounded
          </Badge>
        </div>
      </header>

      <Tabs defaultValue="chat" className="flex-1 flex flex-col">
        <div className="border-b border-border px-4">
          <TabsList className="bg-transparent h-10 gap-0">
            {(["chat", "guardian", "status", "policy"] as const).map((tab) => (
              <TabsTrigger
                key={tab}
                value={tab}
                className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:text-primary text-muted-foreground text-xs uppercase tracking-wider px-4 h-10 bg-transparent"
              >
                {tab}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>

        <TabsContent value="chat" className="flex-1 flex flex-col m-0 data-[state=active]:flex">
          <ChatTab />
        </TabsContent>
        <TabsContent value="guardian" className="m-0 overflow-auto">
          <GuardianTab />
        </TabsContent>
        <TabsContent value="status" className="m-0 overflow-auto">
          <StatusTab />
        </TabsContent>
        <TabsContent value="policy" className="m-0 overflow-auto">
          <PolicyTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
