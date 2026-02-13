/**
 * SSE proxy for run events. Next.js rewrites break text/event-stream streaming,
 * so we proxy manually to preserve the connection and stream.
 * @see https://github.com/vercel/next.js/issues/45048
 */
import { NextRequest } from "next/server";

const API_BASE = process.env.API_BASE_URL || "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ runId: string }> }
) {
  const { runId } = await params;
  const backendUrl = `${API_BASE}/runs/${runId}/events`;

  const res = await fetch(backendUrl, {
    headers: { Accept: "text/event-stream" },
    cache: "no-store",
  });

  if (!res.ok || !res.body) {
    return new Response(res.statusText, { status: res.status });
  }

  return new Response(res.body, {
    status: res.status,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
