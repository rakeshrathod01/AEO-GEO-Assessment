import { useEffect, useRef, useState } from "react";
import { apiStreamUrl, type ProgressEvent } from "@/lib/api";

interface JobStreamState {
  events: ProgressEvent[];
  latest: ProgressEvent | null;
  done: boolean;
}

/**
 * Subscribe to the Celery ingestion progress stream (SSE) for a job.
 * Pass null to disconnect.
 */
export function useJobStream(jobId: number | null): JobStreamState {
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [done, setDone] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    setEvents([]);
    setDone(false);
    esRef.current?.close();
    if (jobId == null) return;

    const es = new EventSource(apiStreamUrl(`/crawl/jobs/${jobId}/stream`));
    esRef.current = es;

    es.onmessage = (e) => {
      try {
        const ev = JSON.parse(e.data) as ProgressEvent;
        setEvents((prev) => [...prev, ev]);
      } catch {
        /* ignore malformed frame */
      }
    };
    es.addEventListener("done", () => {
      setDone(true);
      es.close();
    });
    es.onerror = () => {
      // Connection closed by server (job finished) or network blip.
      es.close();
    };

    return () => es.close();
  }, [jobId]);

  return { events, latest: events[events.length - 1] ?? null, done };
}
